from datetime import date

import pandas as pd
import streamlit as st

from jobfinder import store
from ui.common import PAGES, STATUS_META, empty_state, load_df, status_label

st.title("Dashboard")
st.caption("An overview of every job the agents have found.")

df = load_df(parse_dates=True)
if df.empty:
    empty_state("No applications yet. Run a search to let the agents find jobs.")
    st.stop()

counts = df["status"].value_counts()

# ---- Key numbers ----
with st.container(horizontal=True):
    st.metric("Jobs found", len(df), border=True)
    st.metric("To review", int(counts.get("ready_for_review", 0)), border=True)
    st.metric("Approved", int(counts.get("approved", 0)), border=True)
    st.metric("Applied", int(counts.get("applied", 0)), border=True)
    st.metric("Interviews", int(counts.get("interview", 0) + counts.get("offer", 0)), border=True)

if counts.get("ready_for_review", 0):
    st.page_link(
        PAGES["review"],
        label=f"Review {int(counts['ready_for_review'])} waiting application(s)",
        icon=":material/arrow_forward:",
    )

# ---- Charts ----
left, right = st.columns(2)
with left, st.container(border=True):
    st.markdown("**By status**")
    by_status = (
        pd.Series({status_label(s): int(counts.get(s, 0)) for s in store.STATUSES}, name="jobs")
        .rename_axis("status")
        .loc[lambda s: s > 0]
    )
    st.bar_chart(by_status, horizontal=True, height=260, x_label="jobs", y_label="")
with right, st.container(border=True):
    st.markdown("**By work mode**")
    by_mode = df["work_mode"].value_counts().rename("jobs").rename_axis("work mode")
    st.bar_chart(by_mode, horizontal=True, height=260, x_label="jobs", y_label="")

# ---- Tables ----
left, right = st.columns(2)
with left, st.container(border=True):
    st.markdown("**Upcoming deadlines**")
    open_statuses = {"ready_for_review", "approved"}
    upcoming = (
        df[df["deadline"].notna() & df["status"].isin(open_statuses)]
        .loc[lambda d: d["deadline"] >= date.today()]
        .sort_values("deadline")
        .head(8)
    )
    if upcoming.empty:
        st.caption("No open applications with a known deadline.")
    else:
        upcoming = upcoming.assign(days_left=[(d - date.today()).days for d in upcoming["deadline"]])
        st.dataframe(
            upcoming[["deadline", "days_left", "company", "role", "status"]],
            hide_index=True,
            column_config={
                "deadline": st.column_config.DateColumn("Deadline"),
                "days_left": st.column_config.NumberColumn("Days left", format="%d"),
                "status": st.column_config.TextColumn("Status"),
            },
        )
with right, st.container(border=True):
    st.markdown("**Recently found**")
    recent = df.sort_values("date_found", ascending=False).head(8)
    st.dataframe(
        recent[["date_found", "company", "role", "location", "url"]],
        hide_index=True,
        column_config={
            "date_found": st.column_config.DateColumn("Found"),
            "url": st.column_config.LinkColumn("Ad", display_text="Open"),
        },
    )

with st.expander("Results per agent"):
    per_agent = (
        df.groupby("agent_id")["status"]
        .value_counts()
        .unstack(fill_value=0)
        .reindex(columns=[s for s in store.STATUSES if s in counts.index], fill_value=0)
        .rename(columns=lambda s: STATUS_META[s]["label"])
    )
    per_agent.insert(0, "Total", per_agent.sum(axis=1))
    st.dataframe(per_agent)
