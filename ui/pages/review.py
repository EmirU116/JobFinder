import streamlit as st

from jobfinder import store
from ui.common import empty_state, job_card, letter_editor, load_df, set_status

st.title("Review queue")
st.caption("Read each letter, edit it if needed, then approve or skip. Approved jobs are yours to submit.")

df = load_df()
pending = df[df["status"] == "ready_for_review"].sort_values("date_found").to_dict("records")

if not pending:
    if df.empty:
        empty_state("Nothing to review yet. Run a search first.")
    else:
        st.success("You're all caught up. No applications are waiting for review.", icon=":material/task_alt:")
    st.stop()

# Clamp the position: the queue shrinks as jobs are approved or skipped.
idx = min(st.session_state.get("review_idx", 0), len(pending) - 1)
row = pending[idx]

with st.container(horizontal=True, vertical_alignment="center"):
    st.markdown(f"**{idx + 1} of {len(pending)}** waiting")
    if st.button("Previous", icon=":material/chevron_left:", disabled=idx == 0):
        st.session_state.review_idx = idx - 1
        st.rerun()
    if st.button("Next", icon=":material/chevron_right:", disabled=idx >= len(pending) - 1):
        st.session_state.review_idx = idx + 1
        st.rerun()
st.progress((idx + 1) / len(pending))

left, right = st.columns([2, 3], gap="large")
with left, st.container(border=True):
    job_card(row)

with right:
    text = letter_editor(row, key="review")

st.divider()
with st.container(horizontal=True):
    if st.button("Approve", type="primary", icon=":material/thumb_up:"):
        if text != store.read_letter(row):
            store.write_letter(row, text)  # approving keeps any unsaved edits
        set_status(row["job_id"], "approved")
        st.session_state.review_idx = idx  # the next job slides into this position
        st.rerun()
    if st.button("Skip", icon=":material/skip_next:"):
        set_status(row["job_id"], "skipped")
        st.session_state.review_idx = idx
        st.rerun()
