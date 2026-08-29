from copy import deepcopy
from io import BytesIO
from pathlib import Path

import numpy as np
import streamlit as st

from groundhog.general.soilprofile import SoilProfile, profile_from_dataframe
from groundhog.siteinvestigation.insitutests.pcpt_processing import (
    DEFAULT_CONE_PROPERTIES,
    PCPTProcessing,
)
from groundhog.siteinvestigation.insitutests.pcpt_correlations import (
    frictionangle_sand_kulhawymayne,
    undrainedshearstrength_clay_radlunne,
    unitweight_mayne,
)


def _optional_column(value):
    """Convert an empty column override to Groundhog's default (None)."""
    value = value.strip()
    return value or None


def _return_to_foundation():
    values = st.session_state.get("pcpt_foundation_parameters")
    if values:
        source = "PCPT correlations"
        transfer_id = values.get("transfer_id", 0)
        key_suffix = f"{source}_{transfer_id}"
        st.session_state[f"drained_unit_weight_{key_suffix}"] = float(values["effective_unit_weight"])
        st.session_state[f"friction_angle_{key_suffix}"] = float(values["friction_angle"])
        st.session_state[f"effective_stress_{key_suffix}"] = float(values["effective_stress"])
        st.session_state[f"undrained_unit_weight_{key_suffix}"] = float(values["total_unit_weight"])
        st.session_state[f"su_base_{key_suffix}"] = float(values["undrained_shear_strength"])
        st.session_state[f"su_increase_{key_suffix}"] = max(float(values["su_increase"]), 0.0)
    st.session_state["parameter_source"] = "PCPT correlations"
    st.session_state["requested_tool"] = "Shallow Foundation Bearing Capacity"


def streamlitPCPT():
    """Render the PCPT upload, processing, and plotting page."""
    st.title("PCPT Processing and Graphs")
    st.write(
        "Upload an Excel PCPT data file, map its columns if necessary, and "
        "generate raw and normalised cone penetration test graphs."
    )

    controls, results = st.columns([1, 3])

    with controls:
        transferred_file = st.session_state.get("transferred_pcpt_file")
        source_options = []
        if transferred_file:
            source_options.append(f"From foundation form: {transferred_file['name']}")
        source_options.extend(["Bundled example", "Upload Excel file"])
        data_source = st.radio(
            "Data source", source_options, horizontal=True
        )
        example_file = Path(__file__).resolve().parents[1] / "notebooks" / "Data" / "cpt.xlsx"

        if data_source.startswith("From foundation form:"):
            uploaded_file = BytesIO(transferred_file["data"])
            uploaded_file.name = transferred_file["name"]
            st.success(f"File received from the foundation form: {uploaded_file.name}")
        elif data_source == "Bundled example":
            uploaded_file = example_file
            st.success("Using the bundled example: notebooks/Data/cpt.xlsx")
            st.download_button(
                "Download example Excel file",
                data=example_file.read_bytes(),
                file_name="pcpt_example.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        else:
            uploaded_file = st.file_uploader(
                "PCPT Excel file",
                type=["xls", "xlsx"],
                accept_multiple_files=False,
                help="Default columns: z [m], qc [MPa], fs [MPa], u2 [MPa], and Push.",
            )

        with st.expander("Column mapping and multipliers"):
            z_column = st.text_input("Depth column", placeholder="z [m]")
            qc_column = st.text_input("Cone resistance column", placeholder="qc [MPa]")
            qc_multiplier = st.number_input("Cone resistance multiplier", value=1.0, format="%.3f")
            fs_column = st.text_input("Sleeve friction column", placeholder="fs [MPa]")
            fs_multiplier = st.number_input("Sleeve friction multiplier", value=1.0, format="%.3f")
            u2_column = st.text_input("Pore pressure column", placeholder="u2 [MPa]")
            u2_multiplier = st.number_input("Pore pressure multiplier", value=1.0, format="%.3f")
            push_column = st.text_input("Push column", value="Push")

        area_ratio = st.number_input("Cone area ratio", value=0.80, step=0.01, format="%.2f")
        unit_weight = st.number_input(
            "Soil total unit weight (kN/m³)", value=18.0, step=0.1, format="%.1f"
        )
        water_level = st.number_input(
            "Water level below mudline (m)", value=0.0, step=0.1, format="%.1f"
        )

    with results:
        if uploaded_file is None:
            st.info("Upload an .xls or .xlsx PCPT file to display the graphs.")
            return

        file_name = uploaded_file.name if hasattr(uploaded_file, "name") else uploaded_file.name
        pcpt = PCPTProcessing(title=file_name)
        try:
            pcpt.load_excel(
                uploaded_file,
                z_key=_optional_column(z_column),
                qc_key=_optional_column(qc_column),
                qc_multiplier=qc_multiplier,
                fs_key=_optional_column(fs_column),
                fs_multiplier=fs_multiplier,
                u2_key=_optional_column(u2_column),
                u2_multiplier=u2_multiplier,
                push_key=_optional_column(push_column),
            )
        except Exception as error:
            st.error(f"Could not load the PCPT data: {error}")
            return

        st.subheader("Imported data")
        st.dataframe(pcpt.data, width="stretch")

        st.subheader("Raw PCPT data")
        raw_chart = pcpt.plot_raw_pcpt(return_fig=True)
        raw_chart.update_layout(autosize=True)
        st.plotly_chart(raw_chart, width="stretch")

        try:
            maximum_depth = float(pcpt.data["z [m]"].max())
            cone_data = deepcopy(DEFAULT_CONE_PROPERTIES)
            cone_data["Depth to [m]"] = cone_data["Depth to [m]"].astype(float)
            cone_data.loc[0, "Depth to [m]"] = maximum_depth
            cone_data.loc[0, "area ratio [-]"] = area_ratio
            cone_properties = profile_from_dataframe(cone_data)

            soil_layers = SoilProfile(
                {
                    "Depth from [m]": [0.0],
                    "Depth to [m]": [maximum_depth],
                    "Total unit weight [kN/m3]": [unit_weight],
                    "Soil type": ["Unspecified"],
                }
            )
            pcpt.map_properties(
                layer_profile=soil_layers,
                cone_profile=cone_properties,
                waterlevel=water_level,
            )
            pcpt.normalise_pcpt()

            st.subheader("Normalised PCPT data")
            normalised_chart = pcpt.plot_normalised_pcpt(return_fig=True)
            normalised_chart.update_layout(autosize=True)
            st.plotly_chart(normalised_chart, width="stretch")

            st.subheader("Foundation parameters from PCPT")
            st.caption(
                "Select a representative depth interval. Correlated values can be transferred "
                "to the bearing-capacity page and remain editable there."
            )
            correlation_columns = st.columns(4)
            with correlation_columns[0]:
                depth_from = st.number_input(
                    "Interval from (m)", min_value=0.0, max_value=maximum_depth,
                    value=min(1.0, maximum_depth), step=0.1,
                )
            with correlation_columns[1]:
                depth_to = st.number_input(
                    "Interval to (m)", min_value=0.0, max_value=maximum_depth,
                    value=min(3.0, maximum_depth), step=0.1,
                )
            with correlation_columns[2]:
                nk_factor = st.number_input(
                    "Cone factor Nk", min_value=8.0, max_value=30.0,
                    value=15.0, step=1.0,
                    help="Site-specific calibration against high-quality strength tests is recommended.",
                )
            with correlation_columns[3]:
                statistic = st.selectbox("Representative statistic", ["Median", "Mean"])

            if st.button("Calculate and use PCPT parameters", type="primary"):
                if depth_to <= depth_from:
                    st.error("Interval-to depth must be greater than interval-from depth.")
                else:
                    interval = pcpt.data.loc[
                        pcpt.data["z [m]"].between(depth_from, depth_to)
                    ].copy()
                    interval["PCPT phi [deg]"] = interval.apply(
                        lambda row: frictionangle_sand_kulhawymayne(
                            qt=row["qt [MPa]"],
                            sigma_vo_eff=row["Vertical effective stress [kPa]"],
                        )["Phi [deg]"], axis=1,
                    )
                    interval["PCPT Su [kPa]"] = interval.apply(
                        lambda row: undrainedshearstrength_clay_radlunne(
                            qnet=row["qnet [MPa]"], Nk=nk_factor,
                        )["Su [kPa]"], axis=1,
                    )
                    interval["PCPT total unit weight [kN/m3]"] = interval.apply(
                        lambda row: unitweight_mayne(
                            ft=row["ft [MPa]"],
                            sigma_vo_eff=row["Vertical effective stress [kPa]"],
                        )["gamma [kN/m3]"], axis=1,
                    )
                    parameter_columns = [
                        "PCPT phi [deg]", "PCPT Su [kPa]",
                        "PCPT total unit weight [kN/m3]", "Vertical effective stress [kPa]",
                    ]
                    interval[parameter_columns] = interval[parameter_columns].replace(
                        [np.inf, -np.inf], np.nan
                    )
                    reducer = np.nanmedian if statistic == "Median" else np.nanmean
                    values = {column: float(reducer(interval[column])) for column in parameter_columns}

                    su_rows = interval[["z [m]", "PCPT Su [kPa]"]].dropna()
                    su_gradient = (
                        float(np.polyfit(su_rows["z [m]"], su_rows["PCPT Su [kPa]"], 1)[0])
                        if len(su_rows) >= 2 else 0.0
                    )
                    total_unit_weight = values["PCPT total unit weight [kN/m3]"]
                    transferred = {
                        "transfer_id": st.session_state.get("pcpt_transfer_counter", 0) + 1,
                        "source_file": file_name,
                        "depth_from": depth_from,
                        "depth_to": depth_to,
                        "statistic": statistic,
                        "nk_factor": nk_factor,
                        "friction_angle": values["PCPT phi [deg]"],
                        "undrained_shear_strength": values["PCPT Su [kPa]"],
                        "su_increase": su_gradient,
                        "total_unit_weight": total_unit_weight,
                        "effective_unit_weight": max(total_unit_weight - 10.25, 0.0),
                        "effective_stress": values["Vertical effective stress [kPa]"],
                    }
                    if not all(np.isfinite(value) for key, value in transferred.items() if isinstance(value, float)):
                        st.error("One or more correlations produced no valid value in this interval.")
                    else:
                        st.session_state["pcpt_transfer_counter"] = transferred["transfer_id"]
                        st.session_state["pcpt_foundation_parameters"] = transferred
                        st.success("PCPT parameters saved. Open Shallow Foundation Bearing Capacity to use them.")
                        metrics = st.columns(4)
                        metrics[0].metric("Friction angle", f"{transferred['friction_angle']:.2f}°")
                        metrics[1].metric("Undrained strength", f"{transferred['undrained_shear_strength']:.2f} kPa")
                        metrics[2].metric("Total unit weight", f"{transferred['total_unit_weight']:.2f} kN/m³")
                        metrics[3].metric("Effective stress", f"{transferred['effective_stress']:.2f} kPa")

            saved = st.session_state.get("pcpt_foundation_parameters")
            if saved:
                st.info(
                    f"Saved PCPT parameters: {saved['depth_from']:.2f}–{saved['depth_to']:.2f} m "
                    f"({saved['statistic'].lower()}, {saved['source_file']})."
                )
                st.button(
                    "Use these values in Shallow Foundation Bearing Capacity",
                    on_click=_return_to_foundation,
                    type="primary",
                )
        except Exception as error:
            st.error(f"Could not normalise the PCPT data: {error}")
