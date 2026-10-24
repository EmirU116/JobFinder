import time

import streamlit as st

from jobfinder import config, runner
from ui.common import PAGES

st.title("Run search")
st.caption(
    "The lead agent splits the search and runs the job-hunters in parallel. "
    "Each job they find is added to the CSV as **To review**."
)

has_cv = config.CV_PATH.exists()
has_profile = config.PROFILE_PATH.exists()

# ---- Checklist + settings ----
left, right = st.columns([2, 3], gap="large")
with left, st.container(border=True):
    st.markdown("**Before you start**")
    st.markdown(f"{':material/check_circle:' if has_cv else ':material/radio_button_unchecked:'} CV uploaded")
    st.markdown(f"{':material/check_circle:' if has_profile else ':material/radio_button_unchecked:'} Profile built")
    if not (has_cv and has_profile):
        st.page_link(PAGES["profile"], label="Set up CV & profile", icon=":material/arrow_forward:")

with right, st.container(border=True):
    st.markdown("**Settings**")
    c1, c2 = st.columns(2)
    agents = c1.number_input("Job-hunter agents", min_value=1, max_value=5, value=config.NUM_AGENTS)
    jobs = c2.number_input("Jobs per agent", min_value=1, max_value=20, value=config.JOBS_PER_AGENT)
    st.caption(
        f"Up to **{agents * jobs}** jobs this run. The run stops if its cost reaches "
        f"**${config.MAX_BUDGET_USD:.0f}** (`MAX_BUDGET_USD` in `config.py`)."
    )
    with st.container(horizontal=True):
        if st.button(
            "Start search",
            type="primary",
            icon=":material/rocket_launch:",
            disabled=runner.is_running() or not has_profile,
        ):
            runner.start(f"Search ({agents} agents × {jobs} jobs)", "--agents", str(agents), "--jobs-per-agent", str(jobs))
            st.rerun()
        if st.button("Stop", icon=":material/stop_circle:", disabled=not runner.is_running()):
            runner.stop()
            st.rerun()


# ---- Live log ----
@st.fragment(run_every=2 if runner.is_running() else None)
def live_log() -> None:
    run = runner.current()
    if run is None:
        st.caption("No run has been started since the app launched.")
        return

    elapsed = int(time.time() - run.started)
    if runner.is_running():
        st.info(f"**{run.label}** running · {elapsed // 60}m {elapsed % 60}s", icon=":material/progress_activity:")
        st.session_state.was_running = True
    else:
        if run.process.returncode == 0:
            st.success(f"**{run.label}** finished.", icon=":material/check_circle:")
            st.page_link(PAGES["review"], label="Review the new applications", icon=":material/arrow_forward:")
        else:
            st.error(f"**{run.label}** stopped with exit code {run.process.returncode}.", icon=":material/error:")
        if st.session_state.pop("was_running", False):
            st.rerun()  # full rerun: turns off auto-refresh and re-enables the buttons

    log = runner.read_log()
    with st.container(height=480, border=True):
        st.code(log[-20_000:] or "Waiting for output…", language=None, wrap_lines=True)


st.subheader("Activity", anchor=False)
live_log()
