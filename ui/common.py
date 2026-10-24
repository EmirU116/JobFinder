"""Shared building blocks for the Streamlit pages."""

import pandas as pd
import streamlit as st

from jobfinder import store

# Display metadata per status, in pipeline order.
STATUS_META = {
    "ready_for_review": {"label": "To review", "color": "orange", "icon": ":material/pending:"},
    "approved": {"label": "Approved", "color": "blue", "icon": ":material/thumb_up:"},
    "applied": {"label": "Applied", "color": "violet", "icon": ":material/send:"},
    "interview": {"label": "Interview", "color": "green", "icon": ":material/groups:"},
    "offer": {"label": "Offer", "color": "green", "icon": ":material/celebration:"},
    "rejected": {"label": "Rejected", "color": "red", "icon": ":material/close:"},
    "skipped": {"label": "Skipped", "color": "gray", "icon": ":material/skip_next:"},
}

WORK_MODE_ICONS = {
    "hybrid": ":material/sync_alt:",
    "remote": ":material/home:",
    "on-site": ":material/apartment:",
    "unknown": ":material/help:",
}

PAGES = {
    "dashboard": "ui/pages/dashboard.py",
    "review": "ui/pages/review.py",
    "applications": "ui/pages/applications.py",
    "profile": "ui/pages/profile.py",
    "run": "ui/pages/run.py",
}


def status_label(status: str) -> str:
    return STATUS_META.get(status, {"label": status})["label"]


def load_df(parse_dates: bool = False) -> pd.DataFrame:
    """The applications CSV as a DataFrame, read fresh on every call.

    With parse_dates, date_found/deadline become dates (missing -> None) for
    sorting and date columns; otherwise every value is the raw CSV string.
    """
    df = pd.DataFrame(store.read_rows(), columns=store.FIELDS).fillna("")
    if parse_dates:
        for col in ("date_found", "deadline"):
            parsed = pd.to_datetime(df[col], errors="coerce")
            df[col] = [d.date() if pd.notna(d) else None for d in parsed]
    return df


def status_badge(status: str) -> None:
    meta = STATUS_META.get(status, {"label": status, "color": "gray", "icon": None})
    st.badge(meta["label"], icon=meta["icon"], color=meta["color"])


def job_card(row: dict) -> None:
    """Header block describing one job: title, company, badges, links."""
    st.subheader(row["role"], anchor=False)
    st.markdown(f"**{row['company']}** · {row['location']}")
    with st.container(horizontal=True):
        status_badge(row["status"])
        st.badge(row["work_mode"], icon=WORK_MODE_ICONS.get(row["work_mode"]), color="gray")
        if row["language"]:
            st.badge(row["language"].upper(), icon=":material/translate:", color="gray")
        if row["deadline"]:
            st.badge(f"Deadline {row['deadline']}", icon=":material/event:", color="red")

    st.link_button("Open job ad", row["url"], icon=":material/open_in_new:")
    st.markdown(f"**How to apply:** {row['apply_method'] or '—'}")
    if row["notes"]:
        st.markdown(f"**Agent notes:** {row['notes']}")
    st.caption(f"Found {row['date_found']} by {row['agent_id']} via {row['source']} · id `{row['job_id']}`")


def letter_editor(row: dict, key: str, height: int = 460) -> str:
    """Editable cover letter with save + copy. Returns the current text."""
    original = store.read_letter(row)
    text = st.text_area("Cover letter", value=original, height=height, key=f"{key}-letter-{row['job_id']}")
    with st.container(horizontal=True):
        if st.button("Save letter", icon=":material/save:", key=f"{key}-save-{row['job_id']}", disabled=text == original):
            store.write_letter(row, text)
            st.toast("Letter saved", icon=":material/check:")
        with st.popover("Copy", icon=":material/content_copy:"):
            st.caption("Use the copy icon in the top-right corner.")
            st.code(text, language=None, wrap_lines=True)
    return text


def set_status(job_id: str, status: str) -> None:
    store.update_row(job_id, status=status)
    st.toast(f"Marked as {status_label(status)}", icon=STATUS_META[status]["icon"])


def empty_state(message: str) -> None:
    with st.container(border=True):
        st.markdown(f":material/inbox: {message}")
        st.page_link(PAGES["run"], label="Go to Run search", icon=":material/rocket_launch:")
