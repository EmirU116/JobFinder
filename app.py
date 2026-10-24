"""JobFinder web UI. Run with: streamlit run app.py"""

import streamlit as st

from jobfinder import runner
from ui.common import PAGES

st.set_page_config(page_title="JobFinder", page_icon=":material/work:", layout="wide")

pages = {
    "Overview": [
        st.Page(PAGES["dashboard"], title="Dashboard", icon=":material/dashboard:", default=True),
    ],
    "Applications": [
        st.Page(PAGES["review"], title="Review queue", icon=":material/rate_review:"),
        st.Page(PAGES["applications"], title="All applications", icon=":material/table_view:"),
    ],
    "Setup": [
        st.Page(PAGES["profile"], title="CV & profile", icon=":material/person:"),
        st.Page(PAGES["run"], title="Run search", icon=":material/rocket_launch:"),
    ],
}

nav = st.navigation(pages)

with st.sidebar:
    st.divider()
    run = runner.current()
    if runner.is_running():
        st.info(f"Running: {run.label}", icon=":material/progress_activity:")
    elif run is not None:
        code = run.process.returncode
        if code == 0:
            st.success(f"Finished: {run.label}", icon=":material/check_circle:")
        else:
            st.error(f"Failed: {run.label} (exit {code})", icon=":material/error:")
    st.caption("Agents prepare applications. You review and submit them yourself.")

nav.run()
