import streamlit as st

from jobfinder import config, store
from ui.common import STATUS_META, empty_state, job_card, letter_editor, load_df, status_label

st.title("All applications")
st.caption(f"Everything in `{config.CSV_PATH.relative_to(config.ROOT)}`. Select a row to see and edit it.")

df = load_df(parse_dates=True)
if df.empty:
    empty_state("The CSV is empty. Run a search to let the agents find jobs.")
    st.stop()

# ---- Filters ----
with st.container(border=True):
    search = st.text_input(
        "Search", placeholder="Company, role, or location", icon=":material/search:", label_visibility="collapsed"
    )
    c1, c2, c3 = st.columns(3)
    statuses = c1.multiselect(
        "Status", store.STATUSES, format_func=status_label, placeholder="All statuses"
    )
    modes = c2.multiselect("Work mode", store.WORK_MODES, placeholder="All work modes")
    agents = c3.multiselect("Agent", sorted(df["agent_id"].unique()), placeholder="All agents")

view = df
if search:
    haystack = view["company"] + " " + view["role"] + " " + view["location"]
    view = view[haystack.str.contains(search, case=False, regex=False)]
if statuses:
    view = view[view["status"].isin(statuses)]
if modes:
    view = view[view["work_mode"].isin(modes)]
if agents:
    view = view[view["agent_id"].isin(agents)]
view = view.sort_values("date_found", ascending=False)

# ---- Table ----
with st.container(horizontal=True, vertical_alignment="center"):
    st.markdown(f"**{len(view)}** of {len(df)} jobs")
    st.space("stretch")
    st.download_button(
        "Download CSV",
        data=view.to_csv(index=False).encode("utf-8"),
        file_name="applications.csv",
        mime="text/csv",
        icon=":material/download:",
    )

table = view.assign(status=view["status"].map(lambda s: f"{status_label(s)}"))
selection = st.dataframe(
    table,
    hide_index=True,
    width="stretch",
    height=min(38 + 35 * max(len(table), 1), 480),
    on_select="rerun",
    selection_mode="single-row",
    key="applications_table",
    column_order=[
        "status", "company", "role", "location", "work_mode", "deadline",
        "date_found", "language", "source", "agent_id", "url",
    ],
    column_config={
        "status": st.column_config.TextColumn("Status", width="small"),
        "company": st.column_config.TextColumn("Company"),
        "role": st.column_config.TextColumn("Role", width="large"),
        "location": st.column_config.TextColumn("Location"),
        "work_mode": st.column_config.TextColumn("Work mode", width="small"),
        "deadline": st.column_config.DateColumn("Deadline", width="small"),
        "date_found": st.column_config.DateColumn("Found", width="small"),
        "language": st.column_config.TextColumn("Lang", width="small"),
        "source": st.column_config.TextColumn("Source", width="small"),
        "agent_id": st.column_config.TextColumn("Agent", width="small"),
        "url": st.column_config.LinkColumn("Ad", display_text="Open", width="small"),
    },
)

selected = selection.selection.rows
if not selected:
    st.caption(":material/touch_app: Select a row to view details and the cover letter.")
    st.stop()

# ---- Detail panel ----
job_id = table.iloc[selected[0]]["job_id"]
row = next(r for r in store.read_rows() if r["job_id"] == job_id)

st.divider()
details, letter = st.columns([2, 3], gap="large")
with details:
    with st.container(border=True):
        job_card(row)
    with st.form(f"edit-{job_id}", border=True):
        st.markdown("**Update**")
        status = st.selectbox(
            "Status",
            store.STATUSES,
            index=store.STATUSES.index(row["status"]) if row["status"] in store.STATUSES else 0,
            format_func=lambda s: f"{status_label(s)}",
        )
        work_mode = st.selectbox(
            "Work mode",
            store.WORK_MODES,
            index=store.WORK_MODES.index(row["work_mode"]) if row["work_mode"] in store.WORK_MODES else 3,
        )
        deadline = st.text_input("Deadline (YYYY-MM-DD)", value=row["deadline"])
        notes = st.text_area("Notes", value=row["notes"], height=100)
        if st.form_submit_button("Save changes", type="primary", icon=":material/save:"):
            store.update_row(job_id, status=status, work_mode=work_mode, deadline=deadline.strip(), notes=notes)
            st.toast("Saved", icon=STATUS_META[status]["icon"])
            st.rerun()
with letter:
    letter_editor(row, key="applications")
