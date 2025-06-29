#!/usr/bin/env python3
"""
Streamlit‑app voor urenregistratie in Moneybird met twee‑staps‑flow:
1. Automatische preview (altijd dry‑run).
2. Knop “Inboeken” onder de preview om definitief te registreren.

Preview toont nu ook Klant en Project.
"""

from __future__ import annotations
import datetime as dt
import os
from functools import lru_cache
from typing import Any, Dict, List

import holidays
import requests
import streamlit as st
from zoneinfo import ZoneInfo

# ─────────────────────────────  pagina  ─────────────────────────────
st.set_page_config(page_title="Urenregistratie", page_icon=None)
st.title("Urenregistratie Moneybird")

# ─────────────────────────────  API‑config  ─────────────────────────
TOKEN = ADMIN = USER = None
if "moneybird" in st.secrets:
    TOKEN = st.secrets["moneybird"].get("token")
    ADMIN = st.secrets["moneybird"].get("admin_id")
    USER = st.secrets["moneybird"].get("user_id")

with st.sidebar.expander("API-token instellen", expanded=False):
    with st.form("save_secrets"):
        s_token = st.text_input("Access token", type="password")
        s_admin = st.text_input("Administration ID")
        s_user = st.text_input("User ID")
        submit = st.form_submit_button("Opslaan")
    if submit:
        os.makedirs(".streamlit", exist_ok=True)
        with open(".streamlit/secrets.toml", "w") as f:
            f.write("[moneybird]\n")
            f.write(f'token    = "{s_token}"\n')
            f.write(f'admin_id = "{s_admin}"\n')
            f.write(f'user_id  = "{s_user}"\n')
        st.success("Token opgeslagen – herstart de app.")

if not TOKEN or not ADMIN or not USER:
    st.warning("Vul je Moneybird‑gegevens in via de zijbalk.")
    st.stop()

# ─────────────────────────────  helpers  ────────────────────────────
@lru_cache(maxsize=None)
def _base_url(admin_id: str) -> str:
    return f"https://moneybird.com/api/v2/{admin_id}"

def _get_json(path: str, token: str, admin_id: str,
              params: Dict[str, Any] | None = None):
    r = requests.get(
        _base_url(admin_id) + path,
        headers={"Authorization": f"Bearer {token}"},
        params=params or {},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()

_id_cache: Dict[tuple[str, str], str] = {}

def find_id(kind: str, name: str, token: str, admin_id: str) -> str:
    key = (kind, name.lower())
    if key in _id_cache:
        return _id_cache[key]
    hits = _get_json(f"/{kind}", token, admin_id, {"query": name})
    if not hits:
        raise ValueError(f"Geen {kind[:-1]} gevonden voor ‘{name}’")
    for h in hits:
        nm = h.get("company_name") or h.get("name", "")
        if nm.lower() == name.lower():
            _id_cache[key] = h["id"]
            return h["id"]
    _id_cache[key] = hits[0]["id"]
    st.warning(f"Eerste resultaat '{hits[0].get('name')}' gebruikt voor ‘{name}’")
    return hits[0]["id"]

def log_hours(*, start_local: dt.datetime, end_local: dt.datetime,
              description: str, contact_name: str, project_name: str,
              pause_min: int, token: str, admin_id: str, user_id: str,
              dry_run: bool):
    payload = {
        "time_entry": {
            "user_id": user_id,
            "contact_id": find_id("contacts", contact_name, token, admin_id),
            "project_id": find_id("projects", project_name, token, admin_id),
            "started_at": start_local.astimezone(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "ended_at": end_local.astimezone(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "description": description,
            "billable": True,
            "paused_duration": max(pause_min, 0) * 60,
        }
    }
    if dry_run:
        return payload["time_entry"]
    r = requests.post(
        _base_url(admin_id) + "/time_entries.json",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    if r.status_code != 201:
        raise RuntimeError(f"{r.status_code} – {r.text}")

@st.cache_data(ttl=1800)
def contact_names(token: str, admin_id: str) -> List[str]:
    rows = _get_json("/contacts", token, admin_id, {"query": ""})
    def nm(c): return c.get("company_name") or f"{c.get('firstname','')} {c.get('lastname','')}".strip()
    return sorted(nm(c) for c in rows)

@st.cache_data(ttl=1800)
def project_names(token: str, admin_id: str) -> List[str]:
    rows = _get_json("/projects", token, admin_id, {"query": ""})
    return sorted(p["name"] for p in rows)

# ─────────────────────────────  UI  ────────────────────────────────
day_labels = ["Maandag", "Dinsdag", "Woensdag", "Donderdag",
              "Vrijdag", "Zaterdag", "Zondag"]
dow_short = ["ma", "di", "wo", "do", "vr", "za", "zo"]

with st.form("frm"):
    contact = st.selectbox("Contact", contact_names(TOKEN, ADMIN))
    project = st.selectbox("Project", project_names(TOKEN, ADMIN))
    desc_base = st.text_input("Omschrijving", "Gewerkt")

    c1, c2 = st.columns(2)
    with c1:
        d_from = st.date_input("Van", dt.date.today())
    with c2:
        d_to = st.date_input("Tot", dt.date.today())

    c3, c4 = st.columns(2)
    with c3:
        t_start = st.time_input("Start", dt.time(9, 0))
    with c4:
        t_end = st.time_input("Einde", dt.time(17, 30))

    pause = st.number_input("Pauze (min)", 0, 120, 30)

    sel_days = st.multiselect("Weekdagen",
                              options=day_labels,
                              default=day_labels[:5])
    sel_wd = [day_labels.index(d) for d in sel_days]

    skip_holidays = st.checkbox("NL‑feestdagen overslaan", value=True)

    preview_btn = st.form_submit_button("Voorvertonen")

# ─────────────────────────────  preview stap  ──────────────────────
if preview_btn or st.session_state.get("preview_ready"):
    st.session_state["preview_ready"] = True

    nl_holidays = holidays.country_holidays("NL") if skip_holidays else {}
    tz = ZoneInfo("Europe/Amsterdam")
    desc_full = desc_base + (f" (incl. {pause}m pauze)" if pause else "")
    hrs_day = (
        (dt.datetime.combine(dt.date.today(), t_end) -
         dt.datetime.combine(dt.date.today(), t_start)).seconds / 3600
        - pause / 60
    )

    cur = d_from
    rows: List[Dict[str, Any]] = []
    total = 0.0
    while cur <= d_to:
        sel = cur.weekday() in sel_wd
        hol = cur in nl_holidays
        tag = f"{cur} ({dow_short[cur.weekday()]})"

        # vaste info voor iedere rij
        base_row = {
            "Datum": tag,
            "Klant": contact,
            "Project": project,
        }

        if sel and not hol:
            rows.append({
                **base_row,
                "Start": t_start.strftime("%H:%M"),
                "Einde": t_end.strftime("%H:%M"),
                "Pauze": f"{pause}m",
                "Uren": f"{hrs_day:.2f}",
                "Skip": "",
            })
            total += hrs_day
        else:
            reason = "Niet geselect." if not sel else f"Feestdag: {nl_holidays.get(cur, '')}"
            rows.append({
                **base_row,
                "Start": "-",
                "Einde": "-",
                "Pauze": "-",
                "Uren": "-",
                "Skip": reason,
            })
        cur += dt.timedelta(days=1)

    st.subheader("Preview")
    st.dataframe(rows, use_container_width=True, hide_index=True)
    st.info(f"Totale declarabele uren: **{total:.2f}**")

    if st.button("Inboeken", type="primary"):
        # ─────────────  boeking  ─────────────
        ok = fail = 0
        cur = d_from
        while cur <= d_to:
            sel = cur.weekday() in sel_wd
            hol = cur in nl_holidays
            if sel and not hol:
                s = dt.datetime.combine(cur, t_start, tzinfo=tz)
                e = dt.datetime.combine(cur, t_end, tzinfo=tz)
                try:
                    log_hours(
                        start_local=s, end_local=e,
                        description=desc_full,
                        contact_name=contact, project_name=project,
                        pause_min=pause,
                        token=TOKEN, admin_id=ADMIN, user_id=USER,
                        dry_run=False,
                    )
                    ok += 1
                except Exception as exc:
                    st.error(f"{cur}: {exc}")
                    fail += 1
            cur += dt.timedelta(days=1)
        st.success(f"{ok} dagen geboekt, {fail} mislukt")
        st.session_state["preview_ready"] = False
