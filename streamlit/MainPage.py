import streamlit as st
from PIL import Image
import os
import sys

# Prefer the Groundhog source code in this repository over any separately
# installed copy in the active Python environment.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Allow this file to be launched with a normal Python "Run" command.
# When Streamlit is not already executing the script, restart it through
# Streamlit's command-line entry point.
if __name__ == "__main__":
    from streamlit.runtime.scriptrunner import get_script_run_ctx

    if get_script_run_ctx(suppress_warning=True) is None:
        from streamlit.web import cli as streamlit_cli

        sys.argv = ["streamlit", "run", os.path.abspath(__file__)]
        raise SystemExit(streamlit_cli.main())

# Import Tools
from streamlitIntroduction import streamlitIntroduction
from streamlitPCPT import streamlitPCPT
from streamlitShallowFoundation import streamlitShallowFoundation

# Load favicon.
images_path = os.path.join(os.path.dirname(__file__), 'images')

favicon = Image.open("%s/favicon.ico" % images_path)

# Page setup
st.set_page_config(
    page_title="Groundhog",
    page_icon=favicon,
    layout="wide",
    initial_sidebar_state="expanded",
)

# Create sidebar and load logo.
SIDEBAR = st.sidebar
LOGO = Image.open("%s/logo.png" % images_path)
SIDEBAR.image(
    LOGO,
    width="stretch",
)

# Tool List will be updated as new tools are loaded.
TOOL_LIST = ["Introduction", "Shallow Foundation Bearing Capacity", "PCPT Graph"]

# Apply page changes requested by buttons before the sidebar selector is rendered.
REQUESTED_TOOL = st.session_state.pop("requested_tool", None)
if REQUESTED_TOOL in TOOL_LIST:
    st.session_state["tool_selected"] = REQUESTED_TOOL

TOOL_SELECTED = SIDEBAR.selectbox("Tool List", TOOL_LIST, key="tool_selected")

# Can be converted to Switch-Case with new Python updates.
# TOOL_LIST is compared with text, because the order of names in TOOL_LIST may change in the future, so using TOOL_LIST to compare the selection is risky.
if TOOL_SELECTED == "Introduction":
    streamlitIntroduction()
elif TOOL_SELECTED == "Shallow Foundation Bearing Capacity":
    streamlitShallowFoundation()
elif TOOL_SELECTED == "PCPT Graph":
    streamlitPCPT()
