import json
from datetime import datetime

import streamlit as st

from jobfinder import config, prompts, runner
from ui.common import PAGES

st.title("CV & profile")
st.caption("The agents use this profile to decide which jobs to look for and what to write in the letters.")

# ---- CV ----
with st.container(border=True):
    st.subheader("CV", anchor=False)
    if config.CV_PATH.exists():
        stat = config.CV_PATH.stat()
        modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
        st.markdown(f":material/description: `{config.CV_PATH.name}` · {stat.st_size / 1024:.0f} KB · updated {modified}")
    else:
        st.warning("No CV uploaded yet.", icon=":material/warning:")

    uploaded = st.file_uploader("Upload a new CV (PDF)", type="pdf")
    if uploaded is not None and st.button("Save CV", icon=":material/upload:"):
        config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        config.CV_PATH.write_bytes(uploaded.getvalue())
        st.toast("CV saved. Rebuild the profile so the agents use it.", icon=":material/check:")
        st.rerun()

# ---- Profile ----
with st.container(border=True):
    with st.container(horizontal=True, vertical_alignment="center"):
        st.subheader("Profile", anchor=False)
        st.space("stretch")
        rebuild = st.button(
            "Rebuild from CV",
            icon=":material/auto_awesome:",
            disabled=not config.CV_PATH.exists() or runner.is_running(),
            help="An agent reads the CV and writes a new profile. Overwrites your edits.",
        )
    if rebuild:
        runner.start("Build profile from CV", "--profile-only", "--refresh-profile")
        st.switch_page(PAGES["run"])

    if not config.PROFILE_PATH.exists():
        st.info("No profile yet. Upload your CV and click **Rebuild from CV**.", icon=":material/info:")
        st.stop()

    profile = json.loads(config.PROFILE_PATH.read_text(encoding="utf-8"))
    schema = prompts.PROFILE_SCHEMA["properties"]
    st.caption("List fields take one item per line.")

    with st.form("profile"):
        updated = {}
        cols = st.columns(2)
        for i, (field, spec) in enumerate(schema.items()):
            label = field.replace("_", " ").capitalize()
            target = st if field == "summary" or spec["type"] == "array" else cols[i % 2]
            value = profile.get(field)
            if spec["type"] == "array":
                choices = spec["items"].get("enum")
                if choices:
                    updated[field] = target.multiselect(label, choices, default=[v for v in value or [] if v in choices])
                else:
                    text = target.text_area(label, value="\n".join(value or []), help=spec.get("description"))
                    updated[field] = [line.strip() for line in text.splitlines() if line.strip()]
            elif "enum" in spec:
                options = spec["enum"]
                updated[field] = target.selectbox(label, options, index=options.index(value) if value in options else 0)
            elif spec["type"] == "number":
                updated[field] = target.number_input(label, value=float(value or 0), min_value=0.0, step=0.5)
            elif field == "summary":
                updated[field] = target.text_area(label, value=value or "", height=120)
            else:
                updated[field] = target.text_input(label, value=value or "")

        if st.form_submit_button("Save profile", type="primary", icon=":material/save:"):
            config.PROFILE_PATH.write_text(json.dumps({**profile, **updated}, indent=2, ensure_ascii=False), encoding="utf-8")
            st.toast("Profile saved", icon=":material/check:")
