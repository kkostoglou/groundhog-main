"""Integrated Groundhog PCPT and shallow-foundation graphical interface.

This is a separate application entry point. It can be launched directly with
Python from CodeView; the script starts its own Streamlit server when needed.
"""

import os
import sys

import streamlit as st
from PIL import Image


# Import Groundhog from this repository instead of another installed version.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# Make CodeView's normal `python IntegratedFoundationGUI.py` action work.
if __name__ == "__main__":
    from streamlit.runtime.scriptrunner import get_script_run_ctx

    if get_script_run_ctx(suppress_warning=True) is None:
        from streamlit.web import cli as streamlit_cli

        sys.argv = ["streamlit", "run", os.path.abspath(__file__)]
        raise SystemExit(streamlit_cli.main())


from streamlitIntroduction import streamlitIntroduction
from streamlitPCPT import streamlitPCPT
from streamlitShallowFoundation import streamlitShallowFoundation


IMAGES_PATH = os.path.join(os.path.dirname(__file__), "images")
favicon = Image.open(os.path.join(IMAGES_PATH, "favicon.ico"))

st.set_page_config(
    page_title="Groundhog Integrated Foundation GUI",
    page_icon=favicon,
    layout="wide",
    initial_sidebar_state="expanded",
)

sidebar = st.sidebar
logo = Image.open(os.path.join(IMAGES_PATH, "logo.png"))
sidebar.image(logo, width="stretch")
sidebar.caption("Integrated PCPT and shallow-foundation analysis")

TOOLS = [
    "Introduction",
    "Shallow Foundation Bearing Capacity",
    "PCPT Graph",
]

# Navigation buttons set this request during one run. It is consumed before
# the sidebar selector is created during the following run.
requested_tool = st.session_state.pop("requested_tool", None)
if requested_tool in TOOLS:
    st.session_state["tool_selected"] = requested_tool

selected_tool = sidebar.selectbox("Tool List", TOOLS, key="tool_selected")

if selected_tool == "Introduction":
    streamlitIntroduction()
elif selected_tool == "Shallow Foundation Bearing Capacity":
    streamlitShallowFoundation()
elif selected_tool == "PCPT Graph":
    streamlitPCPT()
