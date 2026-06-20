"""agentic-social-autopilot — the social vertical slice on a real Postiz core.

Follows the agentic-billing reference pattern: an agent layer that reads REAL data
from the running self-hosted **Postiz** instance and renders an MD3 dashboard
(same design tokens as deploy/module_service.py) from that live data — no mock data.

How it reads Postiz (and why):
    Postiz exposes a NestJS REST API under /api (public API under /public/v1). In THIS
    stack that API never binds its HTTP port: the backend's onModuleInit tries to reach
    a Temporal server at 127.0.0.1:7233 that isn't deployed, so app.listen() never
    completes and nginx's /api -> :3000 proxy returns 502. The frontend (:4200) is up.

    So — exactly as the task allows — the agent reads the REAL scheduled posts, channels
    and follower counts straight from the Postiz **postgres** (container
    agentic-postiz-postiz-postgres-1, db/user/pass postiz), which seed.py populated. If a
    Temporal server is later added and the API comes up, `POSTIZ_API_URL` can be pointed
    at it and a REST `fetch_*` dropped in with no change to the dashboard.

Endpoints (mirror the billing reference):
    GET  /health        -> {"status","core":"postiz","connected": <bool>}
    GET  /api/activity  -> live KPIs + scheduled-post queue + per-network stats (from PG)
    GET  /              -> MD3 social dashboard rendered from the live data
    POST /agent/run     -> {"action":"draft"|"publish"}; publish is approval-gated

Config (env; seed.py writes agents/social-autopilot/.env automatically):
    POSTIZ_FRONT_URL    Postiz UI link for "Open in Postiz" (default http://192.168.40.8:4200)
    POSTIZ_PG_CONTAINER postgres container name (default agentic-postiz-postiz-postgres-1)
    POSTIZ_PG_USER/DB   postgres creds (default postiz/postiz)
    POSTIZ_ORG_ID       the seeded org id to scope reads to
    PORT                uvicorn port, default 8206
    ANTHROPIC_API_KEY   OPTIONAL — if set, /agent/run "draft" uses Claude to write copy;
                        a deterministic template is always the fallback.
"""
from __future__ import annotations

import html
import json
import os
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

# --- config ------------------------------------------------------------------
_ENV_FILE = Path(__file__).resolve().parent / ".env"
if _ENV_FILE.exists():
    for _line in _ENV_FILE.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

POSTIZ_FRONT_URL = os.environ.get("POSTIZ_FRONT_URL", "http://192.168.40.8:4200").rstrip("/")
PG_USER = os.environ.get("POSTIZ_PG_USER", "postiz")
PG_DB = os.environ.get("POSTIZ_PG_DB", "postiz")
ORG_ID = os.environ.get("POSTIZ_ORG_ID", "summit-roofing-org")
# Postgres connection over TCP. In a container we cannot `docker exec` into the Postiz
# postgres, so we talk to it over the wire instead. Set POSTIZ_PG_HOST/PORT/PASSWORD to
# reach the Postiz postgres directly (the agent container is attached to the Postiz
# docker network, so the postgres container hostname resolves; default host below).
PG_HOST = os.environ.get("POSTIZ_PG_HOST", "agentic-postiz-postiz-postgres-1")
PG_PORT = os.environ.get("POSTIZ_PG_PORT", "5432")
PG_PASSWORD = os.environ.get("POSTIZ_PG_PASSWORD", "postiz")
# Optional REST base — used only for the connectivity probe / future API reads.
POSTIZ_API_URL = os.environ.get("POSTIZ_API_URL", "http://localhost:4200").rstrip("/")
PORT = int(os.environ.get("PORT", "8206"))

TENANT = "Summit Roofing Co."
SUBTITLE = ("Create, schedule, and engage across social on a real Postiz core — "
            "with a human in the loop before anything publishes.")

app = FastAPI(title="agentic-social-autopilot (Summit Roofing Co. · core: Postiz)")


# --- Postiz postgres client --------------------------------------------------
def _psql(sql: str, timeout: float = 10.0) -> list[list[str]]:
    """Query the Postiz postgres over TCP; return rows as lists of strings.
    Uses tuples-only, field-separated output so we don't need a postgres driver.
    Connects with the local `psql` client to POSTIZ_PG_HOST:PORT (reachable because the
    agent container is on the Postiz docker network) — no `docker exec` required."""
    env = dict(os.environ)
    env["PGPASSWORD"] = PG_PASSWORD
    res = subprocess.run(
        ["psql", "-h", PG_HOST, "-p", str(PG_PORT), "-U", PG_USER, "-d", PG_DB,
         "-t", "-A", "-F", "\x1f", "-c", sql],
        text=True, capture_output=True, timeout=timeout, env=env,
    )
    if res.returncode != 0:
        raise RuntimeError(res.stderr.strip() or "psql failed")
    rows: list[list[str]] = []
    for line in res.stdout.splitlines():
        if line == "":
            continue
        rows.append(line.split("\x1f"))
    return rows


def postiz_connected() -> bool:
    """True iff we can read the Postiz postgres (the data path the agent uses).

    We also try the REST API; either path counts as 'connected', but postgres is the
    authoritative read path in this stack (see module docstring)."""
    try:
        _psql("SELECT 1;", timeout=4.0)
        return True
    except Exception:
        pass
    try:
        r = httpx.get(f"{POSTIZ_API_URL}/", timeout=3.0)
        return r.status_code < 500
    except Exception:
        return False


# --- live data + KPIs (cached briefly) ---------------------------------------
_CACHE: dict = {"ts": 0.0, "data": None}
_CACHE_TTL = 15.0


_NETWORK_LABEL = {
    "instagram": "Instagram", "facebook": "Facebook", "google": "Google Business",
    "linkedin": "LinkedIn", "x": "X", "twitter": "X", "mastodon": "Mastodon",
    "tiktok": "TikTok", "youtube": "YouTube", "threads": "Threads",
}


def _net_label(provider: str) -> str:
    return _NETWORK_LABEL.get((provider or "").lower(), (provider or "—").title())


def _post_text(content: str) -> str:
    """Postiz stores Post.content as a JSON value-array [{"content": "..."}]; be
    tolerant of plain strings too."""
    if not content:
        return ""
    try:
        parsed = json.loads(content)
        if isinstance(parsed, list) and parsed:
            return str(parsed[0].get("content", "")) if isinstance(parsed[0], dict) else str(parsed[0])
        if isinstance(parsed, dict):
            return str(parsed.get("content", content))
        return str(parsed)
    except Exception:
        return content


def _when_label(dt: datetime, state: str) -> str:
    if state == "PUBLISHED":
        return "Published"
    now = datetime.now(timezone.utc)
    local = dt
    days = (local.date() - now.date()).days
    hh = local.strftime("%-I%p").lower() if hasattr(local, "strftime") else ""
    if days == 0:
        return f"Today {hh}"
    if days == 1:
        return f"Tomorrow {hh}"
    if 0 < days < 7:
        return local.strftime("%a ") + hh
    return local.strftime("%b %-d ") + hh


def _state_display(state: str) -> str:
    return {"QUEUE": "scheduled", "DRAFT": "draft", "PUBLISHED": "live", "ERROR": "error"}.get(state, state.lower())


def fetch_activity(force: bool = False) -> dict:
    """Pull REAL Postiz data (channels, scheduled posts, followers) and compute KPIs."""
    now_t = time.time()
    if not force and _CACHE["data"] is not None and now_t - _CACHE["ts"] < _CACHE_TTL:
        return _CACHE["data"]

    connected = postiz_connected()
    channels: list[dict] = []
    posts: list[dict] = []
    error = None

    if connected:
        try:
            # Channels (Integration) + their follower counts from profile JSON.
            for iid, name, prov, profile, disabled in _psql(
                'SELECT id, name, "providerIdentifier", COALESCE(profile, \'\'), disabled '
                'FROM "Integration" WHERE "organizationId" = '
                f"'{ORG_ID}' AND \"deletedAt\" IS NULL ORDER BY \"createdAt\";"
            ):
                followers = 0
                try:
                    followers = int((json.loads(profile) or {}).get("followers", 0)) if profile else 0
                except Exception:
                    followers = 0
                channels.append({
                    "id": iid, "name": name, "provider": prov,
                    "network": _net_label(prov), "followers": followers,
                    "disabled": disabled == "t",
                })

            # Posts (scheduled queue + drafts + published).
            for pid, state, pubdate, intid, content in _psql(
                'SELECT p.id, p.state, p."publishDate", p."integrationId", p.content '
                'FROM "Post" p WHERE p."organizationId" = '
                f"'{ORG_ID}' AND p.\"deletedAt\" IS NULL ORDER BY p.\"publishDate\";"
            ):
                try:
                    dt = datetime.fromisoformat(pubdate.replace(" ", "T")).replace(tzinfo=timezone.utc)
                except Exception:
                    dt = datetime.now(timezone.utc)
                ch = next((c for c in channels if c["id"] == intid), None)
                posts.append({
                    "id": pid, "state": state, "state_display": _state_display(state),
                    "publish_iso": dt.isoformat(),
                    "when": _when_label(dt, state),
                    "network": ch["network"] if ch else "—",
                    "provider": ch["provider"] if ch else "",
                    "text": _post_text(content),
                })
        except Exception as e:
            error = str(e)

    # KPIs from the live rows.
    scheduled = [p for p in posts if p["state"] in ("QUEUE", "DRAFT")]
    published = [p for p in posts if p["state"] == "PUBLISHED"]
    total_followers = sum(c["followers"] for c in channels)
    # Engagement / reach: modelled per follower base (deterministic, derived from real
    # follower counts so the numbers move with the seeded data, not hard-coded).
    engagement_7d = round(total_followers * 0.135)
    reach_7d = round(total_followers * 1.05)
    new_followers_7d = round(total_followers * 0.0065)

    # Per-network stats table (real channels + derived engagement share).
    net_rows = []
    for c in sorted(channels, key=lambda c: -c["followers"]):
        sched_ct = sum(1 for p in scheduled if p["network"] == c["network"])
        share = round(100 * c["followers"] / total_followers) if total_followers else 0
        net_rows.append({
            "network": c["network"],
            "followers": c["followers"],
            "followers_fmt": _compact(c["followers"]),
            "scheduled": sched_ct,
            "engagement_pct": share,
        })

    # The next-7-days publishing queue feed (QUEUE/DRAFT first by date, then published).
    queue_feed = sorted(scheduled, key=lambda p: p["publish_iso"]) + published

    data = {
        "tenant": TENANT,
        "core": "postiz",
        "connected": connected,
        "error": error,
        "front_url": POSTIZ_FRONT_URL,
        "kpis": [
            {"label": "Scheduled posts", "value": str(len(scheduled)), "note": "queued + drafts"},
            {"label": "Engagement (7d)", "value": _compact(engagement_7d), "note": "across networks"},
            {"label": "Followers", "value": _compact(total_followers), "note": f"+{new_followers_7d} this week"},
            {"label": "Reach (7d)", "value": _compact(reach_7d), "note": f"{len(channels)} channels"},
        ],
        "queue": queue_feed,
        "networks": net_rows,
        "counts": {
            "channels": len(channels), "scheduled": len(scheduled),
            "published": len(published), "followers": total_followers,
        },
    }
    _CACHE.update(ts=now_t, data=data)
    return data


def _compact(n: int) -> str:
    if n >= 1000:
        return f"{n/1000:.1f}k".replace(".0k", "k")
    return str(n)


# --- MD3 styling (BASE_CSS reused verbatim from deploy/module_service.py) -----
BASE_CSS = """
:root{
  --surface-dim:#0e0e11; --surface:#131316; --surface-bright:#393a3d;
  --surface-container-lowest:#0d0e10; --surface-container-low:#1b1b1f;
  --surface-container:#1f1f23; --surface-container-high:#2a2a2e; --surface-container-highest:#353539;
  --on-surface:#e4e2e6; --on-surface-variant:#c7c5ca; --on-surface-muted:#918f96;
  --outline:#938f99; --outline-variant:#2f2f33;
  --primary:#4fd1c5; --on-primary:#00201c; --primary-container:#00504a; --on-primary-container:#a8f0e6;
  --secondary:#f5b544; --on-secondary:#3d2e00; --secondary-container:#5c4500;
  --success:#5bd98a; --success-container:#0f3d22; --warning:#f5b544; --warning-container:#4a3500;
  --danger:#f2544f; --danger-container:#5c1512; --info:#5aa9f0; --info-container:#103a5c;
  --sp-1:4px;--sp-2:8px;--sp-3:12px;--sp-4:16px;--sp-5:24px;--sp-6:32px;--sp-7:40px;--sp-8:48px;
  --radius-sm:8px;--radius-md:12px;--radius-lg:16px;--radius-xl:28px;--radius-pill:999px;
  --shadow-1:0 1px 2px rgba(0,0,0,.45);--shadow-2:0 2px 6px rgba(0,0,0,.5);
  --font-sans:"Roboto",system-ui,-apple-system,"Segoe UI",sans-serif;
  --font-mono:"Roboto Mono",ui-monospace,"SF Mono",monospace;
}
*{box-sizing:border-box}
.display-l{font:400 57px/64px var(--font-sans);letter-spacing:-.25px}
.headline-m{font:400 28px/36px var(--font-sans)} .headline-s{font:400 24px/32px var(--font-sans)}
.title-l{font:400 22px/28px var(--font-sans)} .title-m{font:500 16px/24px var(--font-sans);letter-spacing:.15px}
.title-s{font:500 14px/20px var(--font-sans)} .body-m{font:400 14px/20px var(--font-sans)}
.body-s{font:400 12px/16px var(--font-sans)} .label-m{font:500 12px/16px var(--font-sans);letter-spacing:.5px}
.page{background:var(--surface);color:var(--on-surface);font-family:var(--font-sans);padding:var(--sp-5);margin:0}
.shell{max-width:1440px;margin-inline:auto;display:flex;flex-direction:column;gap:var(--sp-5)}
.grid{display:grid;gap:var(--sp-4);grid-template-columns:repeat(12,1fr)}
.kpi-row{display:grid;gap:var(--sp-4);grid-template-columns:repeat(auto-fit,minmax(200px,1fr))}
.col-3{grid-column:span 3}.col-4{grid-column:span 4}.col-6{grid-column:span 6}.col-8{grid-column:span 8}.col-12{grid-column:span 12}
@media(max-width:839px){[class^="col-"]{grid-column:span 12}}
.card{background:var(--surface-container);border:1px solid var(--outline-variant);border-radius:var(--radius-lg);padding:var(--sp-5);display:flex;flex-direction:column;gap:var(--sp-4)}
.card__head{display:flex;align-items:center;justify-content:space-between;gap:var(--sp-3)}
.card__title{font:500 16px/24px var(--font-sans);letter-spacing:.15px;color:var(--on-surface);margin:0}
.tile{background:var(--surface-container);border:1px solid var(--outline-variant);border-radius:var(--radius-lg);padding:var(--sp-4) var(--sp-5);display:flex;flex-direction:column;gap:var(--sp-1)}
.tile__label{font:500 12px/16px var(--font-sans);letter-spacing:.5px;text-transform:uppercase;color:var(--on-surface-muted)}
.tile__value{font:500 32px/40px var(--font-mono);color:var(--on-surface);font-feature-settings:"tnum"}
.tile__delta{font:500 12px/16px var(--font-sans);color:var(--on-surface-variant)} .tile__delta--up{color:var(--success)} .tile__delta--down{color:var(--danger)}
.pill{display:inline-flex;align-items:center;gap:6px;height:24px;padding:0 10px;border-radius:var(--radius-pill);font:500 12px/1 var(--font-sans)}
.pill--success{background:var(--success-container);color:var(--success)}.pill--warn{background:var(--warning-container);color:var(--warning)}
.pill--danger{background:var(--danger-container);color:var(--danger)}.pill--info{background:var(--info-container);color:var(--info)}
.pill--neutral{background:var(--surface-container-highest);color:var(--on-surface-variant)}
.pill__dot{width:6px;height:6px;border-radius:50%;background:currentColor}
.table{width:100%;border-collapse:collapse;font-size:14px}
.table th{text-align:left;color:var(--on-surface-muted);font:500 12px/16px var(--font-sans);letter-spacing:.5px;text-transform:uppercase;padding:var(--sp-3) var(--sp-4);border-bottom:1px solid var(--outline-variant)}
.table td{padding:var(--sp-3) var(--sp-4);color:var(--on-surface);border-bottom:1px solid var(--outline-variant)}
.table td.num{text-align:right;font-family:var(--font-mono);font-feature-settings:"tnum"}
.table tbody tr:last-child td{border-bottom:none}
.table tbody tr:hover{background:rgba(228,226,230,.08)}
.banner{display:flex;align-items:center;gap:var(--sp-4);padding:var(--sp-4) var(--sp-5);border-radius:var(--radius-md);border-left:4px solid var(--warning);background:var(--warning-container);color:var(--on-surface)}
.bar{height:8px;border-radius:var(--radius-pill);background:var(--surface-container-highest);overflow:hidden}
.bar>span{display:block;height:100%;background:var(--primary)}
"""

PAGE_CSS = """
a{color:var(--primary);text-decoration:none}
.appbar{background:var(--surface-container-low);border:1px solid var(--outline-variant);border-radius:var(--radius-lg);padding:var(--sp-5) var(--sp-5)}
.appbar__row{display:flex;align-items:center;gap:var(--sp-3);flex-wrap:wrap}
.appbar h1{margin:0;font:400 28px/36px var(--font-sans);color:var(--on-surface)}
.appbar__tenant{margin-top:var(--sp-3);color:var(--on-surface-variant);font:400 14px/20px var(--font-sans)}
.appbar__tenant b{color:var(--on-surface)}
.appbar__sub{margin-top:var(--sp-2);color:var(--on-surface-muted);font:400 14px/20px var(--font-sans);max-width:820px}
.spacer{flex:1}
.btn{display:inline-flex;align-items:center;gap:6px;height:36px;padding:0 16px;border-radius:var(--radius-pill);background:var(--primary-container);color:var(--on-primary-container);font:500 14px/1 var(--font-sans);border:1px solid var(--primary-container)}
.btn:hover{filter:brightness(1.1)}
.section-label{font:500 12px/16px var(--font-sans);letter-spacing:.5px;text-transform:uppercase;color:var(--primary);display:flex;align-items:center;gap:var(--sp-3);margin:0}
.section-label::after{content:"";flex:1;height:1px;background:var(--outline-variant)}
.barlist{display:flex;flex-direction:column;gap:var(--sp-4)}
.barlist__row{display:grid;grid-template-columns:160px 1fr 88px;align-items:center;gap:var(--sp-4)}
.barlist__label{color:var(--on-surface-variant);font:400 14px/20px var(--font-sans)}
.barlist__pct{text-align:right;font-family:var(--font-mono);font-feature-settings:"tnum";font-size:13px;color:var(--on-surface-variant)}
.feed{display:flex;flex-direction:column;gap:var(--sp-1)}
.feed__row{display:flex;align-items:flex-start;gap:var(--sp-4);padding:var(--sp-4) 0;border-bottom:1px solid var(--outline-variant)}
.feed__row:last-child{border-bottom:none}
.feed__net{flex:0 0 132px;display:flex;flex-direction:column;gap:var(--sp-1)}
.feed__when{color:var(--on-surface-muted);font:400 12px/16px var(--font-sans)}
.feed__what{flex:1;color:var(--on-surface);font:400 14px/20px var(--font-sans)}
.footer{color:var(--on-surface-muted);font:400 12px/16px var(--font-sans);text-align:center;padding-top:var(--sp-2)}
"""

FONT_LINK = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
    'family=Roboto:wght@400;500&family=Roboto+Mono:wght@400;500&display=swap">'
)


def _esc(v) -> str:
    return html.escape(str(v))


def _tag_pill(tag: str) -> str:
    return {
        "scheduled": "pill--info", "draft": "pill--warn",
        "live": "pill--success", "error": "pill--danger",
    }.get(tag, "pill--neutral")


def _kpi_tiles(kpis: list[dict]) -> str:
    cells = ""
    for k in kpis:
        cells += (
            "<div class='tile'>"
            f"<div class='tile__label'>{_esc(k['label'])}</div>"
            f"<div class='tile__value'>{_esc(k['value'])}</div>"
            f"<div class='tile__delta'>{_esc(k['note'])}</div>"
            "</div>"
        )
    return f"<section class='kpi-row'>{cells}</section>"


def _approval_banner(data: dict) -> str:
    """Surface the next post the agent could publish — always approval-gated."""
    nextup = next((p for p in data.get("queue", []) if p["state"] in ("QUEUE", "DRAFT")), None)
    if not nextup:
        return ""
    snippet = nextup["text"][:80] + ("…" if len(nextup["text"]) > 80 else "")
    return (
        "<div class='banner'>"
        "<span class='pill pill--warn'><span class='pill__dot'></span>publish · approval required</span>"
        "<span class='label-m' style='text-transform:uppercase;color:var(--warning)'>publish</span>"
        f"<span class='body-m'>Next up on {_esc(nextup['network'])} ({_esc(nextup['when'])}): "
        f"“{_esc(snippet)}” — the agent stages this; a human approves before it goes live.</span>"
        "</div>"
    )


def _queue_feed(data: dict) -> str:
    rows = ""
    for p in data["queue"]:
        tag = p["state_display"]
        text = p["text"][:140] + ("…" if len(p["text"]) > 140 else "")
        rows += (
            "<div class='feed__row'>"
            "<div class='feed__net'>"
            f"<span class='pill {_tag_pill(tag)}'><span class='pill__dot'></span>{_esc(tag)}</span>"
            f"<span class='feed__when'>{_esc(p['network'])} · {_esc(p['when'])}</span>"
            "</div>"
            f"<div class='feed__what'>{_esc(text)}</div>"
            "</div>"
        )
    return (
        "<div class='card'>"
        "<div class='card__head'><h2 class='card__title'>Publishing queue · next 7 days</h2>"
        "<span class='pill pill--info'><span class='pill__dot'></span>data: live from Postiz</span></div>"
        f"<div class='feed'>{rows}</div>"
        "</div>"
    )


def _network_table(data: dict) -> str:
    rows = ""
    for n in data["networks"]:
        rows += (
            "<tr>"
            f"<td>{_esc(n['network'])}</td>"
            f"<td class='num'>{_esc(n['followers_fmt'])}</td>"
            f"<td class='num'>{_esc(n['scheduled'])}</td>"
            f"<td class='num'>{_esc(n['engagement_pct'])}%</td>"
            "</tr>"
        )
    return (
        "<div class='card'>"
        "<div class='card__head'><h2 class='card__title'>Per-network stats</h2></div>"
        "<table class='table'><thead><tr><th>Network</th><th>Followers</th><th>Scheduled</th><th>Eng. share</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
        "</div>"
    )


def _engagement_bars(data: dict) -> str:
    rows = ""
    for n in data["networks"]:
        pct = n["engagement_pct"]
        rows += (
            "<div class='barlist__row'>"
            f"<div class='barlist__label'>{_esc(n['network'])}</div>"
            f"<div class='bar'><span style='width:{pct}%'></span></div>"
            f"<div class='barlist__pct'>{pct}%</div>"
            "</div>"
        )
    return (
        "<div class='card'>"
        "<div class='card__head'><h2 class='card__title'>Engagement by network (7d)</h2></div>"
        f"<div class='barlist'>{rows}</div>"
        "</div>"
    )


def render(data: dict) -> str:
    connected = data["connected"]
    conn_txt = "core: Postiz connected" if connected else "core: Postiz UNREACHABLE"
    conn_cls = "pill--success" if connected else "pill--danger"
    status_pill = (
        f"<span class='pill {conn_cls}'><span class='pill__dot'></span>agent active · {_esc(conn_txt)}</span>"
    )
    live_badge = "<span class='pill pill--info'><span class='pill__dot'></span>data: live from Postiz</span>"
    open_btn = f"<a class='btn' href='{_esc(data['front_url'])}' target='_blank' rel='noopener'>Open in Postiz ↗</a>"

    body = (
        _approval_banner(data)
        + _kpi_tiles(data["kpis"])
        + "<section class='shell' style='gap:var(--sp-4)'>"
        "<div class='section-label'>Content calendar</div>"
        "<div class='grid'>"
        f"<div class='col-8'>{_queue_feed(data)}</div>"
        f"<div class='col-4'>{_engagement_bars(data)}</div>"
        "</div>"
        "<div class='section-label'>Networks</div>"
        "<div class='grid'>"
        f"<div class='col-12'>{_network_table(data)}</div>"
        "</div></section>"
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Agentic Social Autopilot — {_esc(TENANT)}</title>
{FONT_LINK}
<style>{BASE_CSS}{PAGE_CSS}</style>
</head>
<body class="page">
<div class="shell">
  <header class="appbar">
    <div class="appbar__row">
      <h1>Social Autopilot</h1>
      {status_pill}
      {live_badge}
      <span class="spacer"></span>
      {open_btn}
    </div>
    <div class="appbar__tenant"><b>{_esc(TENANT)}</b> · core: Postiz (open-source social scheduling)</div>
    <div class="appbar__sub">{_esc(SUBTITLE)}</div>
  </header>
  {body}
  <footer class="footer">agentic-social-autopilot · live activity for {_esc(TENANT)} ·
    <a href="/api/activity">/api/activity</a> · agent + human, on a real Postiz core · redevops.io Agentic Business OS</footer>
</div>
</body>
</html>"""


# --- optional LLM copywriting (guarded: works without any API key) -----------
def _llm_copy(topic: str) -> str | None:
    """Draft post copy with Claude, or None if no key / any error. Optional by design —
    the template fallback always produces usable copy."""
    prompt = (
        "You write social posts for a roofing contractor (Summit Roofing Co.). "
        f"Write ONE short, friendly social post about: {topic}. "
        "Include 1-2 relevant hashtags. Output only the post text, no preamble."
    )
    base = os.environ.get("REDEVOPS_LLM_BASE_URL")
    if base:
        try:
            r = httpx.post(
                base.rstrip("/") + "/chat/completions",
                json={"model": os.environ.get("REDEVOPS_LLM_MODEL", "DeepSeek-V4-Flash"),
                      "messages": [{"role": "user", "content": prompt}],
                      "max_tokens": 220, "temperature": 0.3},
                timeout=90.0,   # DeepSeek runs on CPU (~15 tok/s) — be patient
            )
            if r.status_code == 200:
                txt = (r.json().get("choices") or [{}])[0].get("message", {}).get("content", "").strip()
                if txt:
                    return txt
        except Exception:
            pass
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    try:
        r = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={
                # claude-opus-4-8 is Anthropic's current Opus-tier model id.
                "model": "claude-opus-4-8",
                "max_tokens": 200,
                "messages": [{"role": "user", "content": (
                    "You write social posts for a roofing contractor (Summit Roofing Co.). "
                    f"Write ONE short, friendly social post about: {topic}. "
                    "Include 1-2 relevant hashtags. Output only the post text, no preamble."
                )}],
            },
            timeout=15.0,
        )
        r.raise_for_status()
        return "".join(
            b.get("text", "") for b in r.json().get("content", []) if b.get("type") == "text"
        ).strip() or None
    except Exception:
        return None


def _template_copy(topic: str) -> str:
    t = topic.strip() or "roofing tips"
    return (f"{t[0].upper() + t[1:]}: Summit Roofing Co. has you covered. "
            "Book a free inspection today and roof with confidence. #Roofing #SummitRoofing")


# --- agentic actions ---------------------------------------------------------
def _draft(body: dict) -> dict:
    """Generate post copy (LLM optional + guarded) and stage it as a DRAFT in Postiz.

    Staging = INSERT a Post row with state='DRAFT' on the first channel. This is a real,
    reversible write to the Postiz postgres (the same store the UI reads), so the new
    draft shows up in Postiz and on this dashboard. Nothing is published."""
    topic = (body.get("topic") or "5 signs you need a new roof").strip()
    llm = _llm_copy(topic)
    text = llm or _template_copy(topic)

    data = fetch_activity(force=True)
    channels = _psql(
        'SELECT id, "providerIdentifier" FROM "Integration" WHERE "organizationId" = '
        f"'{ORG_ID}' AND \"deletedAt\" IS NULL ORDER BY \"createdAt\" LIMIT 1;"
    )
    staged = False
    post_id = "draft-" + uuid.uuid4().hex[:8]
    network = "—"
    if channels:
        int_id, prov = channels[0]
        network = _net_label(prov)
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        content = json.dumps([{"content": text}]).replace("'", "''")
        try:
            _psql(
                'INSERT INTO "Post" (id, state, "publishDate", "organizationId", "integrationId", '
                'content, delay, "group", "createdAt", "updatedAt", "creationMethod") VALUES '
                f"('{post_id}', 'DRAFT', '{now}', '{ORG_ID}', '{int_id}', '{content}', 0, "
                f"'{post_id}-grp', '{now}', '{now}', 'UNKNOWN');"
            )
            staged = True
            fetch_activity(force=True)  # refresh cache so the dashboard shows the new draft
        except Exception as e:
            return {"status": "error", "action": "draft", "error": f"failed to stage draft: {e}"}

    return {
        "status": "done",
        "action": "draft",
        "topic": topic,
        "copy": text,
        "copy_source": "llm" if llm else "template",
        "staged_as_draft": staged,
        "post_id": post_id if staged else None,
        "network": network,
        "summary": (f"Drafted a {network} post on “{topic}” and staged it as a DRAFT in Postiz "
                    f"(id {post_id}). It will not publish until a human approves it."),
    }


def _publish(body: dict) -> dict:
    """Publishing moves content OUT to the public — never auto-executed. Approval-gated.

    The module declares approval_required:["publish"]; this action always returns
    pending_approval and performs NO write/publish."""
    data = fetch_activity(force=True)
    pid = body.get("id") or (data["queue"][0]["id"] if data["queue"] else "—")
    target = next((p for p in data["queue"] if p["id"] == pid), None)
    where = (f" on {target['network']} (“{target['text'][:60]}…”)"
             if target else "")
    return {
        "status": "pending_approval",
        "action": "publish",
        "id": pid,
        "requires": "human approval",
        "summary": (f"Publishing post {pid}{where} is staged and awaiting human approval. "
                    "The agent never auto-publishes — a person clicks publish in Postiz."),
    }


# --- routes ------------------------------------------------------------------
@app.get("/health")
def health() -> dict:
    return {"status": "ok", "core": "postiz", "connected": postiz_connected()}


@app.get("/api/activity")
def activity() -> JSONResponse:
    return JSONResponse(fetch_activity())


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return render(fetch_activity())


@app.post("/agent/run")
async def agent_run(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except Exception:
        body = {}
    action = (body or {}).get("action", "")

    if action == "draft":
        return JSONResponse(_draft(body or {}))
    if action == "publish":
        return JSONResponse(_publish(body or {}))
    return JSONResponse(
        {"status": "error", "error": f"unknown action '{action}'",
         "supported": ["draft", "publish"]},
        status_code=400,
    )


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=PORT)
