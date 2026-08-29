# How to run: Open the cmd, cd to the folder of the Python file. "streamlit run streamlitShallowFoundation.py"

import streamlit as st


def _open_pcpt_page():
    """Preserve an uploaded file and navigate to the PCPT processing form."""
    uploaded_file = st.session_state.get("foundation_pcpt_upload")
    if uploaded_file is not None:
        st.session_state["transferred_pcpt_file"] = {
            "name": uploaded_file.name,
            "data": uploaded_file.getvalue(),
        }
    st.session_state["requested_tool"] = "PCPT Graph"

def streamlitShallowFoundation():
    from groundhog.shallowfoundations.capacity import (
        ShallowFoundationCapacityDrained,
        ShallowFoundationCapacityUndrained,
    )


    st.title("Groundhog Bearing Capacity Calculations")
    cols = st.columns([1, 1, 1])

    with cols[0]:
        FOUNDATION_GEOMETRY = st.selectbox(
            "Foundation geometry", options=["Rectangle", "Circular"]
        )

        if FOUNDATION_GEOMETRY == "Rectangle":
            LENGTH = st.number_input("Length of the foundation (m)", value=8.00)
            WIDTH = st.number_input("Width of the foundation (m)", value=5.00)
        elif FOUNDATION_GEOMETRY == "Circular":
            DIAMETER = st.number_input("Diameter of the foundation", value=10.0)
        else:
            st.write("Error on foundation geometry.")

        DEPTH = st.number_input("Depth of foundation (m)", value=0.00)

        DRAINAGE = st.selectbox(
            "Drainage type of the foundation", options=["Drained", "Undrained"]
        )

        PARAMETER_SOURCE = st.radio(
            "Soil parameter source",
            ["Manual input", "PCPT correlations"],
            key="parameter_source",
        )
        PCPT_VALUES = st.session_state.get("pcpt_foundation_parameters")
        if PARAMETER_SOURCE == "PCPT correlations" and PCPT_VALUES is None:
            st.warning("No PCPT parameters are saved. Use the PCPT Graph page first; manual defaults are shown.")
        elif PARAMETER_SOURCE == "PCPT correlations":
            st.caption(
                f"Values from {PCPT_VALUES['depth_from']:.2f}–{PCPT_VALUES['depth_to']:.2f} m "
                f"using the {PCPT_VALUES['statistic'].lower()}. You can edit them below."
            )

        if PARAMETER_SOURCE == "PCPT correlations":
            st.file_uploader(
                "Select PCPT Excel file",
                type=["xls", "xlsx"],
                key="foundation_pcpt_upload",
                help="The selected file will be carried to the PCPT processing form.",
            )
            st.button(
                "Open PCPT processing form",
                on_click=_open_pcpt_page,
                width="stretch",
            )

        SKIRTED = st.checkbox("Skirted Foundation?", value=False)

        st.markdown("### Resistance factors")
        BEARING_FACTOR = st.number_input(
            "Bearing resistance factor",
            min_value=1.0,
            value=2.0,
            step=0.1,
            help="The factored vertical bearing capacity is the ultimate capacity divided by this factor.",
        )
        SLIDING_FACTOR = st.number_input(
            "Sliding resistance factor",
            min_value=1.0,
            value=1.5,
            step=0.1,
            help="The factored horizontal sliding capacity is divided by this factor.",
        )


    if DRAINAGE == "Undrained":
        with cols[1]:
            use_pcpt = PARAMETER_SOURCE == "PCPT correlations" and PCPT_VALUES is not None
            key_suffix = f"{PARAMETER_SOURCE}_{PCPT_VALUES.get('transfer_id', 0) if use_pcpt else 0}"
            UNIT_WEIGHT = st.number_input(
                "Unit weight of the soil (kN/m3)",
                value=float(PCPT_VALUES["total_unit_weight"]) if use_pcpt else 16.0,
                key=f"undrained_unit_weight_{key_suffix}",
            )
            SU_BASE = st.number_input(
                "Undrained shear strength at base (kPa)",
                value=float(PCPT_VALUES["undrained_shear_strength"]) if use_pcpt else 10.0,
                key=f"su_base_{key_suffix}",
            )
            SU_INCREASE = st.number_input(
                "Increase of undrained shear strength with depth (kPa/m)",
                value=max(float(PCPT_VALUES["su_increase"]), 0.0) if use_pcpt else 0.0,
                key=f"su_increase_{key_suffix}",
            )

            ECCENTRICITY_WIDTH = st.number_input(
                "Eccentricity of load along the width (m)", value=0.0
            )
            ECCENTRICITY_LENGTH = st.number_input(
                "Eccentricity of load along the length (m)", value=0.0
            )

            undrained_centric = ShallowFoundationCapacityUndrained(
                title="Undrained capacity for centric loading"
            )

            if FOUNDATION_GEOMETRY == "Rectangle":
                undrained_centric.set_geometry(length=LENGTH, width=WIDTH)
            elif FOUNDATION_GEOMETRY == "Circular":
                undrained_centric.set_geometry(diameter=DIAMETER)

            undrained_centric.set_soilparameters_undrained(
                unit_weight=UNIT_WEIGHT, su_base=SU_BASE, su_increase=SU_INCREASE
            )

            undrained_centric.set_eccentricity(
                eccentricity_width=ECCENTRICITY_WIDTH,
                eccentricity_length=ECCENTRICITY_LENGTH,
            )

            undrained_centric.calculate_bearing_capacity()
            NET_BEARING_PRESSURE = undrained_centric.net_bearing_pressure
            CAPACITY = undrained_centric.capacity

            undrained_centric.calculate_sliding_capacity()
            SLIDING_FULL = undrained_centric.sliding_full

            undrained_centric.calculate_envelope(
                factor_bearing=BEARING_FACTOR,
                factor_sliding=SLIDING_FACTOR,
            )

            undrained_centric_plot = undrained_centric.plot_envelope(showfig=False)
        with cols[-1]:
            st.metric("Ultimate bearing pressure", f"{NET_BEARING_PRESSURE:,.2f} kPa")
            st.metric(
                "Factored bearing pressure",
                f"{NET_BEARING_PRESSURE / BEARING_FACTOR:,.2f} kPa",
            )
            st.metric("Ultimate vertical capacity", f"{undrained_centric.ultimate_capacity:,.2f} kN")
            st.metric(
                "Factored vertical capacity",
                f"{undrained_centric.ultimate_capacity / BEARING_FACTOR:,.2f} kN",
            )
            st.plotly_chart(undrained_centric_plot)

    elif DRAINAGE == "Drained":

        with cols[1]:
            use_pcpt = PARAMETER_SOURCE == "PCPT correlations" and PCPT_VALUES is not None
            key_suffix = f"{PARAMETER_SOURCE}_{PCPT_VALUES.get('transfer_id', 0) if use_pcpt else 0}"
            drained_centric = ShallowFoundationCapacityDrained(
                title="Drained capacity for centric loading"
            )

            if FOUNDATION_GEOMETRY == "Rectangle":
                drained_centric.set_geometry(length=LENGTH, width=WIDTH)
            elif FOUNDATION_GEOMETRY == "Circular":
                drained_centric.set_geometry(diameter=DIAMETER)

            UNIT_WEIGHT = st.number_input(
                "Effective unit weight of the soil (kN/m3)",
                value=float(PCPT_VALUES["effective_unit_weight"]) if use_pcpt else 9.0,
                key=f"drained_unit_weight_{key_suffix}",
                help="For PCPT input, this is estimated as correlated total unit weight minus 10.25 kN/m3.",
            )
            FRICTION_ANGLE = st.number_input(
                "Friction angle of the soil (deg)",
                value=float(PCPT_VALUES["friction_angle"]) if use_pcpt else 38.0,
                key=f"friction_angle_{key_suffix}",
            )
            EFFECTIVE_STRESS_BASE = st.number_input(
                "Effective stress at the base of the foundation (kPa)",
                value=float(PCPT_VALUES["effective_stress"]) if use_pcpt else 0.0,
                key=f"effective_stress_{key_suffix}",
            )

            drained_centric.set_soilparameters_drained(
                effective_unit_weight=UNIT_WEIGHT,
                friction_angle=FRICTION_ANGLE,
                effective_stress_base=EFFECTIVE_STRESS_BASE,
            )

            ECCENTRICITY_WIDTH = st.number_input(
                "Eccentricity of load along the width (m)", value=0.0
            )
            ECCENTRICITY_LENGTH = st.number_input(
                "Eccentricity of load along the length (m)", value=0.0
            )

            drained_centric.set_eccentricity(
                eccentricity_length=ECCENTRICITY_LENGTH,
                eccentricity_width=ECCENTRICITY_WIDTH,
            )

            drained_centric.calculate_bearing_capacity()

            drained_centric.calculate_sliding_capacity(vertical_load=1000)

            drained_centric.calculate_envelope(
                factor_bearing=BEARING_FACTOR,
                factor_sliding=SLIDING_FACTOR,
            )

            drained_centric_plot = drained_centric.plot_envelope(showfig=False)

        with cols[-1]:
            st.metric("Ultimate bearing pressure", f"{drained_centric.net_bearing_pressure:,.2f} kPa")
            st.metric(
                "Factored bearing pressure",
                f"{drained_centric.net_bearing_pressure / BEARING_FACTOR:,.2f} kPa",
            )
            st.metric("Ultimate vertical capacity", f"{drained_centric.ultimate_capacity:,.2f} kN")
            st.metric(
                "Factored vertical capacity",
                f"{drained_centric.ultimate_capacity / BEARING_FACTOR:,.2f} kN",
            )
            st.plotly_chart(drained_centric_plot)
