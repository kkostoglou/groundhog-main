"""Native desktop GUI for Groundhog PCPT and shallow-foundation analysis.

Run from the repository root with:
    .venv\\Scripts\\python.exe GroundhogDesktopGUI.py

This application uses Tkinter and Matplotlib. It does not start a web server.
"""

from copy import deepcopy
import os
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.figure import Figure

from groundhog.general.soilprofile import SoilProfile, profile_from_dataframe
from groundhog.shallowfoundations.capacity import (
    ShallowFoundationCapacityDrained,
    ShallowFoundationCapacityUndrained,
)
from groundhog.siteinvestigation.insitutests.pcpt_correlations import (
    frictionangle_sand_kulhawymayne,
    undrainedshearstrength_clay_radlunne,
    unitweight_mayne,
)
from groundhog.siteinvestigation.insitutests.pcpt_processing import (
    DEFAULT_CONE_PROPERTIES,
    PCPTProcessing,
)


ROOT_DIR = Path(__file__).resolve().parent
EXAMPLE_PCPT = ROOT_DIR / "notebooks" / "Data" / "cpt.xlsx"
WATER_UNIT_WEIGHT = 10.25


class GroundhogDesktopApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Groundhog – PCPT and Shallow Foundation")
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        window_width = min(1250, max(980, int(screen_width * 0.86)))
        window_height = min(780, max(640, int(screen_height * 0.82)))
        x_position = max(0, (screen_width - window_width) // 2)
        y_position = max(10, ((screen_height - window_height) // 2) - 50)
        self.geometry(
            f"{window_width}x{window_height}+{x_position}+{y_position}"
        )
        self.minsize(980, 640)

        self.pcpt = None
        self.pcpt_parameters = None
        self.pcpt_dirty = False
        self._pcpt_loading = False
        self._pcpt_load_queue = queue.Queue()
        self._input_metadata = {}
        self.pcpt_file = tk.StringVar(value=str(EXAMPLE_PCPT))
        self.pcpt_source_choice = tk.StringVar(value="example")
        self.status = tk.StringVar(value="Ready. Load the bundled PCPT example or select your own Excel file.")

        self._configure_style()
        self._build_header()
        self.tabs = ttk.Notebook(self, style="Groundhog.TNotebook")
        self.tabs.pack(fill="both", expand=True, padx=10, pady=(0, 6))
        self._build_start_tab()
        self._build_pcpt_tab()
        self._build_foundation_tab()
        self._build_results_tab()
        self._show_start_only()
        ttk.Label(self, textvariable=self.status, relief="sunken", anchor="w").pack(
            fill="x", side="bottom"
        )

    def _configure_style(self):
        style = ttk.Style(self)
        # The native Vista notebook uses very pale tab outlines.  The clam
        # theme honours explicit border colours, keeping long tab titles easy
        # to distinguish on Windows displays.
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"))
        style.configure("Heading.TLabel", font=("Segoe UI", 11, "bold"))
        style.configure("Result.TLabel", font=("Segoe UI", 10), foreground="#175a8a")
        style.configure(
            "ResultsSummary.TLabel",
            font=("Segoe UI", 9),
            foreground="#175a8a",
        )
        style.configure("Note.TLabel", font=("Segoe UI", 9, "normal"), foreground="#356b8c")
        style.configure("Invalid.TEntry", foreground="#b00020", fieldbackground="#ffe8e8")
        # A dedicated table style is required because the default native
        # Treeview heading is only tall enough for one line and clips the
        # symbol/unit line used by the PCPT column headings.
        style.configure(
            "PCPT.Treeview.Heading",
            font=("Segoe UI", 9, "bold"),
            padding=(1, 1),
            anchor="center",
            background="#e7e5e1",
        )
        style.configure("PCPT.Treeview", font=("Segoe UI", 8), rowheight=22)
        style.configure(
            "Groundhog.TNotebook",
            background="#d5d9de",
            bordercolor="#8a9299",
            darkcolor="#8a9299",
            lightcolor="#8a9299",
            borderwidth=1,
            relief="solid",
            tabmargins=(2, 2, 2, 0),
        )
        style.configure(
            "Groundhog.TNotebook.Tab",
            background="#d9dde2",
            foreground="#20252a",
            bordercolor="#8a9299",
            darkcolor="#8a9299",
            lightcolor="#8a9299",
            borderwidth=1,
            relief="solid",
            padding=(12, 7),
            font=("Segoe UI", 10),
        )
        style.map(
            "Groundhog.TNotebook.Tab",
            background=[("disabled", "#eceff2"), ("selected", "#ffffff"), ("active", "#eef3f7")],
            foreground=[("disabled", "#9aa1a8"), ("selected", "#0b3557"), ("active", "#102f47")],
            bordercolor=[("selected", "#66717a"), ("active", "#78838c")],
            lightcolor=[("selected", "#66717a"), ("active", "#78838c")],
            darkcolor=[("selected", "#66717a"), ("active", "#78838c")],
            font=[("selected", ("Segoe UI", 10, "bold"))],
            padding=[("selected", (12, 7)), ("!selected", (12, 7))],
        )
        style.configure(
            "SourceChoice.Toolbutton",
            font=("Segoe UI", 9),
            padding=(8, 5),
            borderwidth=1,
        )
        style.map(
            "SourceChoice.Toolbutton",
            background=[("selected", "#c8d9e8"), ("active", "#e7eef4")],
            foreground=[("selected", "#0b3557")],
            relief=[("selected", "sunken"), ("!selected", "raised")],
        )

    def _build_header(self):
        frame = ttk.Frame(self, padding=(14, 10))
        frame.pack(fill="x")
        ttk.Label(frame, text="Groundhog Desktop", style="Title.TLabel").pack(side="left")
        ttk.Label(
            frame,
            text="Native PCPT processing and shallow-foundation capacity analysis",
        ).pack(side="left", padx=18)

    def _entry(self, parent, label, variable, row, column=0, width=14, help_text=None):
        ttk.Label(parent, text=label).grid(row=row, column=column, sticky="w", padx=5, pady=4)
        entry = ttk.Entry(parent, textvariable=variable, width=width)
        entry.grid(row=row, column=column + 1, sticky="ew", padx=5, pady=4)
        self._input_metadata[str(variable)] = (entry, variable, label)
        entry.bind(
            "<FocusOut>",
            lambda _event, item=entry, value=variable, name=label:
                self._validate_input_cell(item, value, name, show_warning=True),
            add="+",
        )
        if help_text:
            entry.bind("<Enter>", lambda _event: entry.configure(takefocus=True))
        return entry

    def _validate_input_cell(self, entry, variable, label, show_warning=False):
        """Validate one numeric input and visually identify values needing correction."""
        if "disabled" in entry.state():
            entry.configure(style="TEntry")
            return True
        try:
            value = float(variable.get())
        except (TypeError, ValueError):
            message = f"{label}: enter a valid numeric value."
        else:
            message = self._input_range_message(label, value)
        if message:
            entry.configure(style="Invalid.TEntry")
            self.status.set(f"Invalid input — {message}")
            if show_warning:
                messagebox.showwarning("Invalid input", message, parent=self)
            return False
        entry.configure(style="TEntry")
        return True

    def _input_range_message(self, label, value):
        """Return user-facing correction guidance, or None for a valid value."""
        positive = ("Length,", "Width,", "Diameter,")
        nonnegative = (
            "Foundation depth,", "Width eccentricity,", "Length eccentricity,",
            "Effective stress at base,", "Undrained strength,", "su increase,",
            "Water level,", "Depth from,", "Depth to,",
        )
        if label.startswith(positive) and value <= 0:
            return f"{label}: enter a value greater than zero."
        if label.startswith(nonnegative) and value < 0:
            return f"{label}: enter zero or a positive value."
        if label.startswith("Width eccentricity,"):
            try:
                limiting_width = (
                    float(self.width_var.get())
                    if self.geometry_var.get() == "Rectangle"
                    else float(self.diameter_var.get())
                )
            except (TypeError, ValueError):
                limiting_width = 0.0
            if value >= limiting_width / 2:
                return (
                    f"{label}: enter a value smaller than half the active width/diameter "
                    f"({limiting_width / 2:g} m)."
                )
        if label.startswith("Length eccentricity,"):
            try:
                limiting_length = float(self.length_var.get())
            except (TypeError, ValueError):
                limiting_length = 0.0
            if value >= limiting_length / 2:
                return (
                    f"{label}: enter a value smaller than half the foundation length "
                    f"({limiting_length / 2:g} m)."
                )
        if label.startswith("Effective unit weight,") and not 3 <= value <= 12:
            return f"{label}: enter a value from 3 to 12 kN/m³."
        if label.startswith("Total unit weight,") and not 12 <= value <= 22:
            return f"{label}: enter a value from 12 to 22 kN/m³."
        if label.startswith("Friction angle,") and not 20 <= value <= 50:
            return f"{label}: enter an angle from 20° to 50°."
        if label.startswith("Interface friction angle,"):
            try:
                soil_angle = float(self.phi_var.get())
            except (TypeError, ValueError):
                soil_angle = 50.0
            if not 0 <= value <= soil_angle:
                return f"{label}: enter an angle from 0° to the soil friction angle ({soil_angle:g}°)."
        if label.startswith(("Bearing factor,", "Sliding factor,")) and value < 1:
            return f"{label}: enter a resistance factor of at least 1.0."
        if label.startswith("Cone area ratio,") and not 0 < value <= 1:
            return f"{label}: enter a dimensionless value greater than 0 and no greater than 1."
        if label.startswith("Mapping unit weight,") and value <= 0:
            return f"{label}: enter a value greater than zero."
        if label.startswith("Cone factor,") and not 8 <= value <= 30:
            return f"{label}: enter a value from 8 to 30."
        return None

    @staticmethod
    def _float(variable, name):
        try:
            return float(variable.get())
        except (TypeError, ValueError) as error:
            raise ValueError(f"{name} must be a valid number.") from error

    # --------------------------- Start tab ---------------------------
    def _build_start_tab(self):
        self.start_tab = ttk.Frame(self.tabs, padding=30)
        self.tabs.add(self.start_tab, text="Start")
        self.start_tab.columnconfigure(0, weight=1, uniform="workflow")
        self.start_tab.columnconfigure(1, weight=1, uniform="workflow")

        ttk.Label(
            self.start_tab,
            text="Choose one analysis workflow",
            style="Title.TLabel",
        ).grid(row=0, column=0, columnspan=2, pady=(20, 8))
        ttk.Label(
            self.start_tab,
            text="You can return to this screen at any time. PCPT processing is optional.",
        ).grid(row=1, column=0, columnspan=2, pady=(0, 25))

        manual = ttk.LabelFrame(self.start_tab, text="Manual foundation analysis", padding=22)
        manual.grid(row=2, column=0, sticky="nsew", padx=12, pady=8)
        ttk.Label(
            manual,
            text="1. Enter geometry\n2. Enter soil parameters manually\n"
                 "3. Select resistance factors\n4. Calculate capacity",
            justify="left",
        ).pack(anchor="w", pady=(0, 20))
        ttk.Button(manual, text="Start manual analysis", command=self.start_manual_workflow).pack(
            fill="x", ipady=7
        )

        assisted = ttk.LabelFrame(self.start_tab, text="PCPT-assisted foundation analysis", padding=22)
        assisted.grid(row=2, column=1, sticky="nsew", padx=12, pady=8)
        ttk.Label(
            assisted,
            text="1. Select and load PCPT Excel data\n2. Select a depth interval\n"
                 "3. Calculate correlations\n4. Transfer and calculate capacity",
            justify="left",
        ).pack(anchor="w", pady=(0, 20))
        ttk.Button(assisted, text="Start PCPT-assisted analysis", command=self.start_pcpt_workflow).pack(
            fill="x", ipady=7
        )

    def start_manual_workflow(self):
        self.source_var.set("Manual input")
        # A newly started manual analysis should expose the drained inputs by
        # default.  Otherwise an Undrained choice retained from an earlier
        # workflow hides the friction-angle and effective-stress cells.
        self.drainage_var.set("Drained")
        self._set_source_controls()
        self._update_soil_fields()
        self._enable_workflow_tab(self.foundation_tab)
        self.tabs.select(self.foundation_tab)
        self.update_idletasks()
        self.status.set("Manual workflow: complete Steps 1–4 on the foundation tab.")

    def start_pcpt_workflow(self):
        self.source_var.set("PCPT correlations")
        self._set_source_controls()
        self._enable_workflow_tab(self.pcpt_tab)
        self.tabs.select(self.pcpt_tab)
        self.status.set("PCPT workflow: begin with Step 1 – load and normalise an Excel file.")

    def _show_start_only(self):
        """Require a workflow selection before any analysis tab can open."""
        for tab in (self.pcpt_tab, self.foundation_tab, self.results_tab):
            self.tabs.tab(tab, state="disabled")
        self.tabs.tab(self.start_tab, state="normal")
        self.tabs.select(self.start_tab)

    def _enable_workflow_tab(self, tab):
        """Enable the selected next step while keeping stale results locked."""
        self.tabs.tab(tab, state="normal")
        self.tabs.tab(self.results_tab, state="disabled")

    # ------------------------- Foundation tab -------------------------
    def _build_foundation_tab(self):
        self.foundation_tab = ttk.Frame(self.tabs)
        self.tabs.add(self.foundation_tab, text="Shallow Foundation Bearing Capacity")
        self.foundation_tab.columnconfigure(1, weight=1)
        self.foundation_tab.rowconfigure(0, weight=1)

        controls_panel = ttk.Frame(self.foundation_tab)
        controls_panel.grid(row=0, column=0, sticky="nsew")
        controls_panel.rowconfigure(0, weight=1)
        controls_panel.columnconfigure(0, weight=1)

        controls_canvas = tk.Canvas(
            controls_panel,
            width=430,
            yscrollincrement=24,
            highlightthickness=0,
            borderwidth=0,
        )
        controls_scrollbar = ttk.Scrollbar(
            controls_panel, orient="vertical", command=controls_canvas.yview
        )
        controls_canvas.configure(yscrollcommand=controls_scrollbar.set)
        controls_canvas.grid(row=0, column=0, sticky="nsew")
        controls_scrollbar.grid(row=0, column=1, sticky="ns")

        controls = ttk.Frame(controls_canvas, padding=10)
        controls_window = controls_canvas.create_window((0, 0), window=controls, anchor="nw")
        controls.bind(
            "<Configure>",
            lambda _event: controls_canvas.configure(scrollregion=controls_canvas.bbox("all")),
        )
        controls_canvas.bind(
            "<Configure>",
            lambda event: controls_canvas.itemconfigure(controls_window, width=event.width),
        )

        def scroll_foundation_form(event):
            controls_canvas.yview_scroll(int(-event.delta / 120), "units")

        plot_frame = ttk.Frame(self.foundation_tab, padding=8)
        plot_frame.grid(row=0, column=1, sticky="nsew")
        plot_frame.rowconfigure(1, weight=1)
        plot_frame.columnconfigure(0, weight=1)

        ttk.Button(controls, text="← Back to workflow selection", command=lambda: self.tabs.select(self.start_tab)).pack(
            fill="x", pady=(0, 6)
        )

        self.geometry_var = tk.StringVar(value="Rectangle")
        self.length_var = tk.StringVar(value="8.0")
        self.width_var = tk.StringVar(value="5.0")
        self.diameter_var = tk.StringVar(value="10.0")
        self.depth_var = tk.StringVar(value="0.0")
        self.skirted_var = tk.BooleanVar(value=False)
        self.drainage_var = tk.StringVar(value="Drained")
        self.source_var = tk.StringVar(value="Manual input")
        self.ecc_width_var = tk.StringVar(value="0.0")
        self.ecc_length_var = tk.StringVar(value="0.0")
        self.bearing_factor_var = tk.StringVar(value="2.0")
        self.sliding_factor_var = tk.StringVar(value="1.5")
        self.total_unit_weight_var = tk.StringVar(value="16.0")
        self.su_var = tk.StringVar(value="10.0")
        self.su_gradient_var = tk.StringVar(value="0.0")
        self.effective_unit_weight_var = tk.StringVar(value="9.0")
        self.phi_var = tk.StringVar(value="38.0")
        self.interface_friction_var = tk.StringVar(value="33.0")
        self.effective_stress_var = tk.StringVar(value="0.0")

        geometry_box = ttk.LabelFrame(controls, text="Step 1 – Foundation geometry", padding=8)
        geometry_box.pack(fill="x", pady=5)
        ttk.Label(geometry_box, text="Geometry").grid(row=0, column=0, sticky="w", padx=5, pady=4)
        geometry_selector = ttk.Combobox(
            geometry_box, textvariable=self.geometry_var,
            values=["Rectangle", "Circular"], state="readonly", width=18,
        )
        geometry_selector.grid(row=0, column=1, sticky="ew", padx=5, pady=4)
        geometry_selector.bind("<<ComboboxSelected>>", lambda _event: self._update_geometry_fields())
        self.length_entry = self._entry(geometry_box, "Length, L (m)", self.length_var, 1)
        self.width_entry = self._entry(geometry_box, "Width, B (m)", self.width_var, 2)
        self.diameter_entry = self._entry(geometry_box, "Diameter, B (m)", self.diameter_var, 3)
        self._entry(geometry_box, "Foundation depth, D (m)", self.depth_var, 4)
        self._entry(geometry_box, "Width eccentricity, eB (m)", self.ecc_width_var, 5)
        self.ecc_length_entry = self._entry(
            geometry_box, "Length eccentricity, eL (m)", self.ecc_length_var, 6
        )
        ttk.Checkbutton(geometry_box, text="Skirted foundation", variable=self.skirted_var).grid(
            row=7, column=0, columnspan=2, sticky="w", padx=5, pady=4
        )

        soil_box = ttk.LabelFrame(controls, text="Step 2 – Soil parameters", padding=8)
        soil_box.pack(fill="x", pady=5)
        ttk.Label(soil_box, text="Drainage").grid(row=0, column=0, sticky="w", padx=5, pady=4)
        drainage = ttk.Combobox(
            soil_box, textvariable=self.drainage_var,
            values=["Drained", "Undrained"], state="readonly", width=18,
        )
        drainage.grid(row=0, column=1, sticky="ew", padx=5, pady=4)
        drainage.bind("<<ComboboxSelected>>", lambda _event: self._update_soil_fields())

        ttk.Label(soil_box, text="Parameter source").grid(row=1, column=0, sticky="w", padx=5, pady=4)
        source = ttk.Combobox(
            soil_box, textvariable=self.source_var,
            values=["Manual input", "PCPT correlations"], state="readonly", width=18,
        )
        source.grid(row=1, column=1, sticky="ew", padx=5, pady=4)
        source.bind("<<ComboboxSelected>>", lambda _event: self._source_changed())
        self.open_pcpt_button = ttk.Button(
            soil_box, text="Open PCPT tab", command=self._open_pcpt_tab
        )
        self.open_pcpt_button.grid(
            row=2, column=0, sticky="ew", padx=5, pady=4
        )
        self.load_saved_pcpt_button = ttk.Button(
            soil_box, text="Load saved PCPT values", command=self.use_pcpt_parameters
        )
        self.load_saved_pcpt_button.grid(
            row=2, column=1, sticky="ew", padx=5, pady=4
        )

        self.pcpt_reference_var = tk.StringVar(value="No PCPT correlation values transferred.")
        self.pcpt_reference_frame = ttk.LabelFrame(
            soil_box, text="PCPT processing reference", padding=6
        )
        self.pcpt_reference_frame.grid(
            row=3, column=0, columnspan=2, sticky="ew", padx=2, pady=5
        )
        ttk.Label(
            self.pcpt_reference_frame,
            textvariable=self.pcpt_reference_var,
            style="Note.TLabel",
            justify="left",
            wraplength=390,
        ).pack(fill="x", padx=3, pady=2)

        self.drained_frame = ttk.LabelFrame(soil_box, text="Drained inputs", padding=5)
        self.drained_frame.grid(row=4, column=0, columnspan=2, sticky="ew", padx=2, pady=5)
        self._entry(self.drained_frame, "Effective unit weight, γ′ (kN/m³)", self.effective_unit_weight_var, 0)
        self._entry(self.drained_frame, "Friction angle, φ′ (deg)", self.phi_var, 1)
        self._entry(
            self.drained_frame, "Interface friction angle, δ′ (deg)",
            self.interface_friction_var, 2,
        )
        self._entry(self.drained_frame, "Effective stress at base, σ′v0 (kPa)", self.effective_stress_var, 3)
        ttk.Label(
            self.drained_frame,
            text=(
                "PCPT conversion: effective unit weight = total unit weight - water unit weight.\n"
                "Current setting: seawater = 10.25 kN/m³; freshwater reference = 9.81 kN/m³."
            ),
            style="Note.TLabel",
            justify="left",
            wraplength=380,
        ).grid(row=4, column=0, columnspan=2, sticky="w", padx=5, pady=(3, 5))

        self.undrained_frame = ttk.LabelFrame(soil_box, text="Undrained inputs", padding=5)
        self.undrained_frame.grid(row=5, column=0, columnspan=2, sticky="ew", padx=2, pady=5)
        self._entry(self.undrained_frame, "Total unit weight, γ (kN/m³)", self.total_unit_weight_var, 0)
        self._entry(self.undrained_frame, "Undrained strength, su (kPa)", self.su_var, 1)
        self._entry(self.undrained_frame, "su increase, κ (kPa/m)", self.su_gradient_var, 2)

        factors = ttk.LabelFrame(controls, text="Step 3 – Resistance factors", padding=8)
        factors.pack(fill="x", pady=5)
        self._entry(factors, "Bearing factor, γb (-)", self.bearing_factor_var, 0)
        self._entry(factors, "Sliding factor, γs (-)", self.sliding_factor_var, 1)
        ttk.Button(controls, text="Step 4 – Calculate bearing capacity", command=self.calculate_foundation).pack(
            fill="x", pady=(10, 5), ipady=5
        )
        # Keep the final action fully visible when the form is scrolled to its limit.
        ttk.Frame(controls, height=70).pack(fill="x")

        self.foundation_result = tk.StringVar(value="Enter parameters and calculate.")
        ttk.Label(plot_frame, textvariable=self.foundation_result, style="Result.TLabel", justify="left").grid(
            row=0, column=0, sticky="ew", pady=(0, 5)
        )
        self.foundation_figure = Figure(figsize=(8, 6), dpi=100)
        self.foundation_axis = self.foundation_figure.add_subplot(111)
        self.foundation_canvas = FigureCanvasTkAgg(self.foundation_figure, master=plot_frame)
        self.foundation_canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew")
        NavigationToolbar2Tk(self.foundation_canvas, plot_frame, pack_toolbar=False).grid(
            row=2, column=0, sticky="ew"
        )

        def bind_mousewheel(widget):
            widget.bind("<MouseWheel>", scroll_foundation_form, add="+")
            for child in widget.winfo_children():
                bind_mousewheel(child)

        bind_mousewheel(controls)
        self._update_geometry_fields()
        self._set_source_controls()
        self._update_soil_fields()

    def _update_geometry_fields(self):
        """Enable only the dimensions used by the selected foundation shape."""
        if self.geometry_var.get() == "Rectangle":
            self.length_entry.configure(state="normal")
            self.width_entry.configure(state="normal")
            self.diameter_entry.configure(state="disabled")
            self.ecc_length_entry.configure(state="normal")
        else:
            self.length_entry.configure(state="disabled")
            self.width_entry.configure(state="disabled")
            self.diameter_entry.configure(state="normal")
            self.ecc_length_entry.configure(state="disabled")

    def _update_soil_fields(self):
        if self.drainage_var.get() == "Drained":
            self.drained_frame.grid()
            self.undrained_frame.grid_remove()
        else:
            self.undrained_frame.grid()
            self.drained_frame.grid_remove()

    # --------------------------- Results tab ---------------------------
    def _build_results_tab(self):
        self.results_tab = ttk.Frame(self.tabs, padding=8)
        self.tabs.add(self.results_tab, text="Analytical Calculation Results")
        self.results_tab.columnconfigure(0, weight=2)
        self.results_tab.columnconfigure(1, weight=3)
        self.results_tab.rowconfigure(1, weight=1)

        ttk.Button(
            self.results_tab,
            text="← Return to foundation inputs",
            command=lambda: self.tabs.select(self.foundation_tab),
        ).grid(row=0, column=0, sticky="w", padx=4, pady=(0, 8))
        ttk.Button(
            self.results_tab,
            text="Save PDF",
            command=self.print_analytical_report,
        ).grid(row=0, column=1, sticky="e", padx=4, pady=(0, 8))

        report_frame = ttk.LabelFrame(self.results_tab, text="Analytical calculation report", padding=5)
        report_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 5))
        report_frame.rowconfigure(0, weight=1)
        report_frame.columnconfigure(0, weight=1)
        report_scrollbar = ttk.Scrollbar(report_frame, orient="vertical")
        report_scrollbar.grid(row=0, column=1, sticky="ns")
        self.results_text = tk.Text(
            report_frame,
            wrap="word",
            font=("Consolas", 10),
            padx=10,
            pady=10,
            yscrollcommand=report_scrollbar.set,
        )
        self.results_text.grid(row=0, column=0, sticky="nsew")
        report_scrollbar.configure(command=self.results_text.yview)
        self.results_text.insert("1.0", "Run a foundation calculation to generate the analytical report.")
        self.results_text.configure(state="disabled")

        chart_frame = ttk.LabelFrame(self.results_tab, text="Bearing-capacity envelope", padding=5)
        chart_frame.grid(row=1, column=1, sticky="nsew", padx=(5, 0))
        chart_frame.rowconfigure(1, weight=1)
        chart_frame.columnconfigure(0, weight=1)
        self.results_summary = tk.StringVar(value="Run a calculation to generate the results summary.")
        ttk.Label(
            chart_frame,
            textvariable=self.results_summary,
            style="ResultsSummary.TLabel",
            justify="left",
        ).grid(row=0, column=0, sticky="w", padx=10, pady=(4, 8))
        self.results_figure = Figure(figsize=(8, 6), dpi=100)
        self.results_axis = self.results_figure.add_subplot(111)
        self.results_axis.text(
            0.5, 0.5, "No calculation results yet", ha="center", va="center",
            transform=self.results_axis.transAxes,
        )
        self.results_canvas = FigureCanvasTkAgg(self.results_figure, master=chart_frame)
        self.results_canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew")
        NavigationToolbar2Tk(self.results_canvas, chart_frame, pack_toolbar=False).grid(
            row=2, column=0, sticky="ew"
        )

    def print_analytical_report(self):
        """Create a paginated PDF of the analytical report and available graphs."""
        report_text = self.results_text.get("1.0", "end-1c").strip()
        if not report_text or report_text.startswith("Run a foundation calculation"):
            messagebox.showwarning(
                "No analytical results",
                "Run a foundation calculation before printing the analytical report.",
            )
            return

        output_path = filedialog.asksaveasfilename(
            parent=self,
            title="Save printable analytical report",
            defaultextension=".pdf",
            filetypes=[("PDF document", "*.pdf")],
            initialfile="Groundhog_Analytical_Calculation_Report.pdf",
        )
        if not output_path:
            return

        try:
            report_lines = report_text.splitlines()
            # Use the minimum number of text pages and distribute the lines
            # evenly. Fixed-size chunks made the last pages unnecessarily
            # sparse even when the report could fit comfortably on fewer A4
            # sheets at this font size.
            maximum_lines_per_page = 110
            text_page_count = max(
                1,
                (len(report_lines) + maximum_lines_per_page - 1)
                // maximum_lines_per_page,
            )
            base_page_lines, pages_with_extra_line = divmod(
                len(report_lines), text_page_count
            )
            with PdfPages(output_path) as pdf:
                page_start = 0
                for page_index in range(text_page_count):
                    line_count = base_page_lines + (
                        1 if page_index < pages_with_extra_line else 0
                    )
                    page_lines = report_lines[page_start:page_start + line_count]
                    page_start += line_count
                    page_number = page_index + 1
                    # Expand the line spacing on shorter pages so the report
                    # uses the available A4 height instead of leaving a large
                    # blank band at the bottom. Keep the range conservative
                    # so dense pages still fit and sparse pages remain easy
                    # to read.
                    page_font_size = 7.2
                    target_text_height_points = 735.0
                    page_line_spacing = min(
                        1.38,
                        max(
                            1.0,
                            target_text_height_points
                            / max(line_count * page_font_size, 1.0),
                        ),
                    )
                    page = Figure(figsize=(8.27, 11.69), dpi=100)
                    page.text(
                        0.045,
                        0.975,
                        "\n".join(page_lines),
                        ha="left",
                        va="top",
                        family="monospace",
                        fontsize=page_font_size,
                        linespacing=page_line_spacing,
                    )
                    page.text(
                        0.945,
                        0.015,
                        f"Analytical calculations — page {page_number}",
                        ha="right",
                        va="bottom",
                        fontsize=7,
                        color="0.35",
                    )
                    pdf.savefig(page)

                pdf.savefig(self.results_figure, bbox_inches="tight")

                if self.source_var.get() == "PCPT correlations" and self.pcpt is not None:
                    pcpt_source = Path(
                        self.pcpt_parameters.get("derivation", {}).get(
                            "source_file", self.pcpt_file.get()
                        )
                    ).name
                    self.pcpt_figure.suptitle(
                        f"PCPT data and interpreted parameters — source: {pcpt_source}",
                        fontsize=13,
                        y=0.995,
                    )
                    pdf.savefig(self.pcpt_figure, bbox_inches="tight")
                    self.pcpt_figure.suptitle("")

            self.status.set(f"Printable analytical report saved to {output_path}")
            open_choice = messagebox.askyesno(
                "PDF report created",
                f"The report was saved to:\n{output_path}\n\n"
                "Open the PDF for preview?",
            )
            if open_choice:
                try:
                    if not hasattr(os, "startfile"):
                        raise OSError("System PDF opening is not available.")
                    os.startfile(output_path, "open")
                except OSError as error:
                    messagebox.showinfo(
                        "PDF report saved",
                        f"Automatic opening is not available ({error}).\n\n"
                        f"Open the saved PDF manually:\n{output_path}",
                    )
        except Exception as error:
            messagebox.showerror(
                "Could not create printable report",
                f"The PDF report could not be created:\n{error}",
            )

    def _source_changed(self):
        self._set_source_controls()
        if self.source_var.get() == "PCPT correlations":
            if self.pcpt_parameters:
                self.use_pcpt_parameters()
            else:
                self._open_pcpt_tab()
                messagebox.showinfo(
                    "PCPT parameters required",
                    "Load and process a PCPT file, then click 'Use in foundation form'.",
                )

    def _open_pcpt_tab(self):
        self._enable_workflow_tab(self.pcpt_tab)
        self.tabs.select(self.pcpt_tab)

    def _set_source_controls(self):
        """Enable PCPT actions only when the PCPT parameter source is active."""
        if not hasattr(self, "open_pcpt_button"):
            return
        pcpt_selected = self.source_var.get() == "PCPT correlations"
        self.open_pcpt_button.configure(state="normal" if pcpt_selected else "disabled")
        self.load_saved_pcpt_button.configure(
            state="normal" if pcpt_selected and self.pcpt_parameters else "disabled"
        )
        if hasattr(self, "pcpt_reference_frame"):
            if pcpt_selected:
                self.pcpt_reference_frame.grid()
            else:
                self.pcpt_reference_frame.grid_remove()

    def use_pcpt_parameters(self):
        if not self.pcpt_parameters:
            messagebox.showwarning("No PCPT values", "Calculate PCPT correlations first.")
            return
        p = self.pcpt_parameters
        self.source_var.set("PCPT correlations")
        self._set_source_controls()
        self._enable_workflow_tab(self.foundation_tab)
        self.tabs.select(self.foundation_tab)
        # Set destination variables after the notebook selects the foundation
        # tab, so its drained Entry widgets cannot redraw stale/default values
        # during the tab transition.
        transferred_values = (
            (self.total_unit_weight_var, p["total_unit_weight"]),
            (self.su_var, p["undrained_shear_strength"]),
            (self.su_gradient_var, max(p["su_increase"], 0.0)),
            (self.effective_unit_weight_var, p["effective_unit_weight"]),
            (self.phi_var, p["friction_angle"]),
            (self.interface_friction_var, max(p["friction_angle"] - 5.0, 0.0)),
            (self.effective_stress_var, p["effective_stress"]),
        )
        for variable, value in transferred_values:
            variable.set(f"{value:.6g}")
        derivation = p.get("derivation", {})
        source_path = Path(self.pcpt_file.get()).expanduser()
        source_name = source_path.name or str(source_path)
        self.pcpt_reference_var.set(
            f"Source file: {source_name}\n"
            f"a = {derivation.get('area_ratio', float('nan')):.4g}   |   "
            f"γmap = {derivation.get('mapping_unit_weight', float('nan')):.4g} kN/m³   |   "
            f"zw = {derivation.get('water_level', float('nan')):.4g} m\n"
            f"zPCPT = [{p['depth_from']:.4g}, {p['depth_to']:.4g}] m   |   "
            f"Nk = {p['nk']:.4g}   |   Statistic = "
            f"{derivation.get('statistic', self.statistic_var.get())}"
        )
        self._update_soil_fields()
        self.update_idletasks()
        self.status.set(
            f"PCPT values transferred from {p['depth_from']:.2f}–{p['depth_to']:.2f} m. "
            f"Transferred φ′ = {p['friction_angle']:.2f}°, "
            f"σ′v0 = {p['effective_stress']:.2f} kPa, and "
            f"su = {p['undrained_shear_strength']:.2f} kPa."
        )

    def calculate_foundation(self):
        try:
            geometry = self.geometry_var.get()
            depth = self._float(self.depth_var, "Foundation depth")
            ecc_width = self._float(self.ecc_width_var, "Width eccentricity")
            ecc_length = self._float(self.ecc_length_var, "Length eccentricity")
            bearing_factor = self._float(self.bearing_factor_var, "Bearing factor")
            sliding_factor = self._float(self.sliding_factor_var, "Sliding factor")
            if bearing_factor < 1 or sliding_factor < 1:
                raise ValueError("Resistance factors must be at least 1.0.")

            if self.drainage_var.get() == "Drained":
                model = ShallowFoundationCapacityDrained("Desktop drained analysis")
            else:
                model = ShallowFoundationCapacityUndrained("Desktop undrained analysis")

            if geometry == "Rectangle":
                model.set_geometry(
                    option="rectangle",
                    length=self._float(self.length_var, "Length"),
                    width=self._float(self.width_var, "Width"),
                    depth=depth,
                    skirted=self.skirted_var.get(),
                )
                model.set_eccentricity(eccentricity_width=ecc_width, eccentricity_length=ecc_length)
            else:
                model.set_geometry(
                    option="circle",
                    diameter=self._float(self.diameter_var, "Diameter"),
                    depth=depth,
                    skirted=self.skirted_var.get(),
                )
                model.set_eccentricity(eccentricity_width=ecc_width)

            if self.drainage_var.get() == "Drained":
                interface_friction = self._float(
                    self.interface_friction_var, "Interface friction angle"
                )
                soil_friction = self._float(self.phi_var, "Friction angle")
                if not 0 <= interface_friction <= soil_friction:
                    raise ValueError(
                        "Interface friction angle must be between 0 and the soil friction angle."
                    )
                model.set_soilparameters_drained(
                    effective_unit_weight=self._float(
                        self.effective_unit_weight_var, "Effective unit weight"
                    ),
                    friction_angle=soil_friction,
                    effective_stress_base=self._float(
                        self.effective_stress_var, "Effective stress at base"
                    ),
                )
                model.calculate_bearing_capacity()
                # A separate design V has not been entered. V=0 is used only to
                # obtain the V-independent skirt and earth-pressure components;
                # drained sliding is reported and plotted as Hu(V), not at an
                # arbitrary fixed vertical load.
                model.calculate_sliding_capacity(
                    vertical_load=0.0,
                    interface_frictionangle=interface_friction,
                )
            else:
                model.set_soilparameters_undrained(
                    unit_weight=self._float(self.total_unit_weight_var, "Total unit weight"),
                    su_base=self._float(self.su_var, "Undrained shear strength"),
                    su_increase=self._float(self.su_gradient_var, "Strength increase"),
                )
                model.calculate_bearing_capacity()
                model.calculate_sliding_capacity()

            envelope_options = {}
            if self.drainage_var.get() == "Drained":
                envelope_options["effective_friction_angle_sliding"] = interface_friction
            model.calculate_envelope(
                factor_bearing=bearing_factor,
                factor_sliding=sliding_factor,
                **envelope_options,
            )
            factored_pressure = model.net_bearing_pressure / bearing_factor
            factored_capacity = model.ultimate_capacity / bearing_factor
            self.foundation_result.set(
                f"Input su: {self.su_var.get()} kPa" if self.drainage_var.get() == "Undrained" else
                f"Input φ′: {self.phi_var.get()}°"
            )
            self.foundation_result.set(
                self.foundation_result.get()
                + f"    |    Ultimate bearing pressure (qu [kPa]): {model.net_bearing_pressure:,.2f} kPa"
                + f"    |    Factored pressure: {factored_pressure:,.2f} kPa\n"
                + f"Ultimate vertical capacity: {model.ultimate_capacity:,.2f} kN"
                + f"    |    Factored vertical capacity: {factored_capacity:,.2f} kN"
            )
            summary_input = (
                f"Input su: {self.su_var.get()} kPa"
                if self.drainage_var.get() == "Undrained"
                else f"Input φ′: {self.phi_var.get()}°"
            )
            if self.source_var.get() == "PCPT correlations" and self.pcpt_parameters:
                source_file = Path(
                    self.pcpt_parameters.get("derivation", {}).get(
                        "source_file", self.pcpt_file.get()
                    )
                ).name
                summary_input = f"PCPT source: {source_file}\n" + summary_input
            self.results_summary.set(
                summary_input
                + f"   |   qu: {model.net_bearing_pressure:,.2f} kPa"
                + f"   |   qu,f: {factored_pressure:,.2f} kPa\n"
                + f"Vult: {model.ultimate_capacity:,.2f} kN"
                + f"   |   Vult,f: {factored_capacity:,.2f} kN"
            )

            self._draw_capacity_envelope(self.foundation_axis, model)
            self.foundation_figure.tight_layout()
            self.foundation_canvas.draw_idle()
            self._draw_capacity_envelope(self.results_axis, model)
            self.results_figure.tight_layout()
            self.results_canvas.draw_idle()
            self._write_analytical_report(
                model=model,
                bearing_factor=bearing_factor,
                sliding_factor=sliding_factor,
                factored_pressure=factored_pressure,
                factored_capacity=factored_capacity,
            )
            self.tabs.tab(self.results_tab, state="normal")
            self.tabs.select(self.results_tab)
            self.status.set("Bearing-capacity calculation completed. Analytical results are shown in the Results tab.")
        except Exception as error:
            messagebox.showerror("Calculation error", str(error))
            self.status.set(f"Foundation calculation failed: {error}")

    def _draw_capacity_envelope(self, axis, model):
        axis.clear()
        unfactored_line, = axis.plot(
            model.envelope_H_unfactored,
            model.envelope_V_unfactored,
            label="Unfactored bearing envelope",
        )
        factored_line, = axis.plot(
            model.envelope_H_factored,
            model.envelope_V_factored,
            label="Factored bearing envelope",
        )
        if hasattr(model, "sliding_cutoff_H"):
            axis.plot(
                model.sliding_cutoff_H,
                model.sliding_cutoff_V,
                "--",
                label="Unfactored sliding limit",
            )
        if hasattr(model, "sliding_cutoff_H_factored"):
            axis.plot(
                model.sliding_cutoff_H_factored,
                model.sliding_cutoff_V_factored,
                "--",
                label="Factored sliding limit",
            )

        # Shade only the region satisfying every applicable factored limit state.
        factored_h = np.asarray(model.envelope_H_factored, dtype=float)
        factored_v = np.asarray(model.envelope_V_factored, dtype=float)
        if hasattr(model, "sliding_cutoff_H_factored"):
            cutoff_h = np.asarray(model.sliding_cutoff_H_factored, dtype=float)
            cutoff_v = np.asarray(model.sliding_cutoff_V_factored, dtype=float)

            def boundary_by_vertical(horizontal, vertical):
                finite = np.isfinite(horizontal) & np.isfinite(vertical)
                horizontal = horizontal[finite]
                vertical = vertical[finite]
                order = np.argsort(vertical)
                vertical = vertical[order]
                horizontal = horizontal[order]
                unique_v, inverse = np.unique(vertical, return_inverse=True)
                maximum_h = np.full(unique_v.shape, -np.inf, dtype=float)
                np.maximum.at(maximum_h, inverse, horizontal)
                return unique_v, maximum_h

            bearing_v, bearing_h = boundary_by_vertical(factored_h, factored_v)
            sliding_v, sliding_h = boundary_by_vertical(cutoff_h, cutoff_v)
            common_v_max = min(float(np.nanmax(bearing_v)), float(np.nanmax(sliding_v)))
            common_v = np.linspace(0.0, common_v_max, 300)
            bearing_limit = np.interp(common_v, bearing_v, bearing_h)
            sliding_limit = np.interp(common_v, sliding_v, sliding_h)
            combined_limit = np.minimum(bearing_limit, sliding_limit)
            axis.fill_betweenx(
                common_v,
                0.0,
                combined_limit,
                color="tab:green",
                alpha=0.13,
                label="Acceptable: bearing + sliding",
                zorder=0.5,
            )
        else:
            axis.fill(
                np.append(factored_h, 0.0),
                np.append(factored_v, 0.0),
                color="tab:green",
                alpha=0.10,
                label="Acceptable inside factored envelope",
                zorder=0.5,
            )

        axis.text(
            0.03,
            0.04,
            "Green area: acceptable for all factored limits",
            transform=axis.transAxes,
            fontsize=8,
            color="darkgreen",
            bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "darkgreen", "alpha": 0.9},
        )
        axis.set_title(
            f"{self.drainage_var.get()} shallow-foundation V-H capacity envelope",
            pad=10,
        )
        axis.set_xlabel("Horizontal load (kN)")
        axis.set_ylabel("Vertical load (kN)")
        axis.set_xlim(left=0)
        axis.set_ylim(bottom=0)
        axis.grid(True, alpha=0.3)
        axis.legend(fontsize=8, loc="best", ncol=2)

    @staticmethod
    def _report_value(value):
        if isinstance(value, (float, int, np.floating, np.integer)):
            return f"{float(value):,.4f}"
        return str(value)

    def _write_analytical_report(
        self, model, bearing_factor, sliding_factor, factored_pressure, factored_capacity
    ):
        input_summary = [
            "INPUT SUMMARY",
            "-" * 43,
            f"   Foundation geometry      : {self.geometry_var.get()}",
            f"   Foundation depth, D      : {model.depth:,.4f} m",
            f"   Skirted                  : {'Yes' if model.skirted else 'No'}",
        ]
        if self.geometry_var.get() == "Rectangle":
            input_summary.extend([
                f"   Foundation length, L     : {model.length:,.4f} m",
                f"   Foundation width, B      : {model.width:,.4f} m",
                f"   Length eccentricity, eL  : {model.eccentricity_length:,.4f} m",
                f"   Width eccentricity, eB   : {model.eccentricity_width:,.4f} m",
            ])
        else:
            input_summary.extend([
                f"   Foundation diameter, B   : {model.diameter:,.4f} m",
                f"   Load eccentricity, e     : {model.eccentricity:,.4f} m",
            ])
        input_summary.extend([
            f"   Drainage condition       : {self.drainage_var.get()}",
            f"   Parameter source         : {self.source_var.get()}",
        ])
        if self.drainage_var.get() == "Drained":
            input_summary.extend([
                f"   Effective unit weight, γ′: {model.effective_unit_weight:,.4f} kN/m³",
                f"   Friction angle, φ′       : {model.friction_angle:,.4f} deg",
                f"   Interface angle, δ′      : "
                f"{float(self.interface_friction_var.get()):,.4f} deg",
                f"   Effective stress, σ′v0   : {model.effective_stress_base:,.4f} kPa",
            ])
        else:
            input_summary.extend([
                f"   Total unit weight, γ     : {model.unit_weight:,.4f} kN/m³",
                f"   Shear strength, su       : {model.su_base:,.4f} kPa",
                f"   Strength increase, κ     : {model.su_increase:,.4f} kPa/m",
            ])
        input_summary.extend([
            f"   Bearing factor, RFb      : {bearing_factor:,.4f}",
            f"   Sliding factor, RFs      : {sliding_factor:,.4f}",
        ])
        if self.source_var.get() == "PCPT correlations" and self.pcpt_parameters:
            p = self.pcpt_parameters
            source_file = Path(
                p.get("derivation", {}).get("source_file", self.pcpt_file.get())
            ).name
            input_summary.extend([
                f"   PCPT source workbook     : {source_file}",
                f"   PCPT interval, zPCPT     : [{p['depth_from']:.2f}, {p['depth_to']:.2f}] m",
                f"   PCPT cone factor, Nk     : {p['nk']:,.4f}",
                f"   PCPT statistic           : {self.statistic_var.get()}",
            ])

        lines = [
            "GROUNDHOG SHALLOW FOUNDATION ANALYSIS",
            "=" * 43,
            "",
            *input_summary,
            "",
            "1. ANALYSIS BASIS",
            f"   Drainage condition       : {self.drainage_var.get()}",
            f"   Parameter source         : {self.source_var.get()}",
            f"   Foundation geometry      : {self.geometry_var.get()}",
            f"   D [m]                    : {model.depth:,.4f}",
            f"   Skirted                  : {'Yes' if model.skirted else 'No'}",
        ]
        if self.geometry_var.get() == "Rectangle":
            lines.extend([
                f"   L x B [m]                : {model.length:,.4f} x {model.width:,.4f}",
                f"   eL x eB [m]              : {model.eccentricity_length:,.4f} x "
                f"{model.eccentricity_width:,.4f}",
                f"   L' x B' [m]              : {model.effective_length:,.4f} x {model.effective_width:,.4f}",
                f"     L' = L - 2eL = {model.length:,.4f} - 2 x "
                f"{model.eccentricity_length:,.4f} = {model.effective_length:,.4f} m",
                f"     B' = B - 2eB = {model.width:,.4f} - 2 x "
                f"{model.eccentricity_width:,.4f} = {model.effective_width:,.4f} m",
                f"     A = L x B = {model.length:,.4f} x {model.width:,.4f} = "
                f"{model.full_area:,.4f} m^2",
                f"     A' = L' x B' = {model.effective_length:,.4f} x "
                f"{model.effective_width:,.4f} = {model.effective_area:,.4f} m^2",
            ])
        else:
            radius = 0.5 * model.diameter
            eccentricity = model.eccentricity
            segment_area = 0.5 * model.effective_area
            lines.extend([
                f"   B [m]                    : {model.diameter:,.4f}",
                f"   R [m]                    : {radius:,.4f}",
                f"   e [m]                    : {eccentricity:,.4f}",
                f"   L' x B' [m]              : {model.effective_length:,.4f} x {model.effective_width:,.4f}",
                f"     A = pi x B^2 / 4 = pi x {model.diameter:,.4f}^2 / 4 = "
                f"{model.full_area:,.4f} m^2",
                "     s = pi R^2/2 - [e x sqrt(R^2-e^2) + R^2 x asin(e/R)]",
                f"       = {segment_area:,.4f} m^2",
                "     L' = sqrt(2s x sqrt((R+e)/(R-e)))",
                f"       = {model.effective_length:,.4f} m",
                "     B' = L' x sqrt((R-e)/(R+e))",
                f"       = {model.effective_width:,.4f} m",
                f"     A' = L' x B' = {model.effective_length:,.4f} x "
                f"{model.effective_width:,.4f} = {model.effective_area:,.4f} m^2",
            ])
        lines.extend([
            f"   A [m²]                   : {model.full_area:,.4f}",
            f"   A' [m²]                  : {model.effective_area:,.4f}",
            "",
            "2. SOIL INPUTS",
        ])
        if self.drainage_var.get() == "Undrained":
            lines.extend([
                f"   gamma [kN/m³]            : {model.unit_weight:,.4f}",
                f"   su [kPa]                 : {model.su_base:,.4f}",
                f"   kappa [kPa/m]            : {model.su_increase:,.4f}",
                f"   su,a [kPa]               : {model.su_above_base:,.4f}",
                f"   sigma_v0 [kPa]           : {model.unit_weight * model.depth:,.4f}",
                "   Bearing model            : qu = su x Nc x Kc",
            ])
        else:
            lines.extend([
                f"   gamma' [kN/m³]           : {model.effective_unit_weight:,.4f}",
                f"   phi' [deg]               : {model.friction_angle:,.4f}",
                f"   delta [deg]              : {float(self.interface_friction_var.get()):,.4f}",
                f"   sigma'v0 [kPa]           : {model.effective_stress_base:,.4f}",
                "   Bearing model            : API drained Nq-Ngamma formulation with Kq and Kgamma",
            ])
        if self.source_var.get() == "PCPT correlations" and self.pcpt_parameters:
            p = self.pcpt_parameters
            derivation = p.get("derivation", {})
            statistics = derivation.get("statistics", {})
            intermediate = derivation.get("intermediate_statistics", {})
            regression = derivation.get("su_regression", {})
            statistic = derivation.get("statistic", self.statistic_var.get())
            lines.extend([
                "", "2A. PCPT PARAMETER DERIVATION",
                f"   zPCPT = [zfrom, zto]      : [{p['depth_from']:.4f}, {p['depth_to']:.4f}] m",
                f"   Rows in interval         : {derivation.get('row_count', 'not retained')}",
                f"   Adopted statistic        : {statistic}",
                f"   Cone area ratio, a       : {derivation.get('area_ratio', np.nan):,.4f}",
                f"   Mapping unit weight      : {derivation.get('mapping_unit_weight', np.nan):,.4f} kN/m^3",
                f"   Water level              : {derivation.get('water_level', np.nan):,.4f} m",
                f"   Water unit weight        : {derivation.get('water_unit_weight', WATER_UNIT_WEIGHT):,.4f} kN/m^3",
                f"   Cone factor, Nk          : {p['nk']:,.4f}",
                "", "   Processing equations and assumptions",
                "   qt = qc + u2(1-a)",
                "   qnet = qt - sigma_v0/1000                         [MPa]",
                "   sigma'_v0 = sigma_v0 - hydrostatic pore pressure  [kPa]",
                "   phi' = 17.6 + 11 log10[(1000 qt/Pa)/sqrt(sigma'_v0/Pa)]",
                "          with Pa = 100 kPa",
                "   su = 1000 qnet/Nk                                 [kPa]",
                "   gamma = 1.95 gamma_w (1000 ft/Pa)^0.06",
                "           x (sigma'_v0/Pa)^0.06                      [kN/m^3]",
                "   gamma' = max(gamma - gamma_w, 0)                  [kN/m^3]",
                "   delta' = max(phi' - 5 degrees, 0)",
                "   ft is pressure-corrected sleeve friction where sleeve geometry",
                "   is available; otherwise ft = fs.",
                "", "   Interval statistics (valid n; min / mean / median / max)",
            ])
            labels = {
                "PCPT phi [deg]": "phi' [deg]",
                "PCPT Su [kPa]": "su [kPa]",
                "PCPT total unit weight [kN/m3]": "gamma [kN/m^3]",
                "Vertical effective stress [kPa]": "sigma'_v0 [kPa]",
            }
            for column, label in labels.items():
                stats = statistics.get(column, {})
                lines.append(
                    f"   {label:<22}: n={stats.get('valid_count', 0):<5d} "
                    f"{stats.get('minimum', np.nan):,.4f} / {stats.get('mean', np.nan):,.4f} / "
                    f"{stats.get('median', np.nan):,.4f} / {stats.get('maximum', np.nan):,.4f}"
                )
            if intermediate:
                lines.extend(["", "   Intermediate PCPT statistics (valid n; min / mean / median / max)"])
                for column, stats in intermediate.items():
                    lines.append(
                        f"   {column:<22}: n={stats.get('valid_count', 0):<5d} "
                        f"{stats.get('minimum', np.nan):,.4f} / {stats.get('mean', np.nan):,.4f} / "
                        f"{stats.get('median', np.nan):,.4f} / {stats.get('maximum', np.nan):,.4f}"
                    )
            lines.extend([
                "", "   su-depth linear regression",
                f"   Valid samples            : {regression.get('sample_count', 0)}",
                "   su(z) = slope x z + intercept",
                f"   Slope                    : {regression.get('slope', np.nan):,.4f} kPa/m",
                f"   Intercept                : {regression.get('intercept', np.nan):,.4f} kPa",
                f"   R^2                      : {regression.get('r_squared', np.nan):,.4f}",
                "", "   Adopted foundation parameters",
                f"   phi'                     : {p['friction_angle']:,.4f} deg",
                f"   su                       : {p['undrained_shear_strength']:,.4f} kPa",
                f"   su increase              : {p['su_increase']:,.4f} kPa/m "
                f"(foundation input = {max(p['su_increase'], 0.0):,.4f})",
                f"   gamma                    : {p['total_unit_weight']:,.4f} kN/m^3",
                f"   gamma'                   : {p['effective_unit_weight']:,.4f} kN/m^3",
                f"   sigma'_v0                : {p['effective_stress']:,.4f} kPa",
                f"   delta'                   : {max(p['friction_angle'] - 5.0, 0.0):,.4f} deg",
            ])
        effective_area_ratio = 100.0 * model.effective_area / model.full_area
        vertical_unfactored_max = float(np.nanmax(model.envelope_V_unfactored))
        vertical_factored_max = float(np.nanmax(model.envelope_V_factored))
        horizontal_unfactored_max = float(np.nanmax(model.envelope_H_unfactored))
        horizontal_factored_max = float(np.nanmax(model.envelope_H_factored))
        vertical_reduction = (
            100.0 * (1.0 - vertical_factored_max / vertical_unfactored_max)
            if vertical_unfactored_max else 0.0
        )
        horizontal_reduction = (
            100.0 * (1.0 - horizontal_factored_max / horizontal_unfactored_max)
            if horizontal_unfactored_max else 0.0
        )
        if self.drainage_var.get() == "Undrained" and model.su_base:
            pressure_ratio_text = (
                f"qu/su = {model.net_bearing_pressure:,.4f} / {model.su_base:,.4f} "
                f"= {model.net_bearing_pressure / model.su_base:,.3f}; "
                "Nc and geometry/depth corrections amplify su."
            )
        elif self.drainage_var.get() == "Drained" and model.effective_stress_base:
            pressure_ratio_text = (
                f"qu/base effective stress = "
                f"{model.net_bearing_pressure:,.4f} / {model.effective_stress_base:,.4f} "
                f"= {model.net_bearing_pressure / model.effective_stress_base:,.3f}; "
                "Nq, Ngamma and correction factors amplify resistance."
            )
        else:
            pressure_ratio_text = "A pressure ratio is not available because the reference input is zero."
        area_effect_text = (
            "Eccentricity reduces effective area and available resistance."
            if effective_area_ratio < 99.99
            else "Entered eccentricities cause no effective-area reduction."
        )
        area_ratio_derivation = (
            f"A'/A x 100 = {model.effective_area:,.4f} / {model.full_area:,.4f} x 100 "
            f"= {effective_area_ratio:,.2f}%"
        )
        vertical_reduction_derivation = (
            f"(1 - Vult,f/Vult) x 100 = (1 - {vertical_factored_max:,.4f} / "
            f"{vertical_unfactored_max:,.4f}) x 100 = {vertical_reduction:,.2f}%"
        )
        horizontal_reduction_derivation = (
            f"(1 - Hmax,f/Hmax) x 100 = (1 - {horizontal_factored_max:,.4f} / "
            f"{horizontal_unfactored_max:,.4f}) x 100 = {horizontal_reduction:,.2f}%"
        )
        if self.drainage_var.get() == "Drained":
            envelope_derivation = [
                "     For each positive envelope point i:",
                "       Hi = Vi x tan(theta_i) + Hb,outside,i + Hs,i",
                "     Hmax = max(Hi)",
                f"       = max(envelope H coordinates) = {horizontal_unfactored_max:,.4f} kN",
                "     Hmax is a bearing-envelope coordinate; it is not the load-dependent Hu(V)",
                "     described in Section 7. The sliding limit must",
                "     also be satisfied at the relevant vertical load.",
            ]
        else:
            envelope_derivation = [
                "     Hmax = max(envelope H coordinates) = Hu",
                f"       = {horizontal_unfactored_max:,.4f} kN",
            ]
        summary_soil_input = (
            f"phi' [deg]              : {model.friction_angle:,.4f}"
            if self.drainage_var.get() == "Drained"
            else f"su [kPa]                : {model.su_base:,.4f}"
        )
        if self.drainage_var.get() == "Drained":
            nq_used = (
                model.capacity["N_q [-]"]
                if not model.skirted and model.depth > 0
                else model.capacity["N_q [-]"] - 1.0
            )
            q_term = (
                model.effective_stress_base
                * nq_used
                * model.capacity["K_q [-]"]
            )
            gamma_term = (
                0.5
                * model.effective_unit_weight
                * model.effective_width
                * model.capacity["N_gamma [-]"]
                * model.capacity["K_gamma [-]"]
            )
            qu_derivation_text = (
                "     qu [kPa] = sigma'v0 [kPa] x Nq* [-] x Kq [-]\n"
                "                + 0.5 x gamma' [kN/m3] x B' [m]\n"
                "                x Ngamma [-] x Kgamma [-]\n"
                f"       phi' [deg] = {model.friction_angle:,.4f}\n"
                f"       B' [m] / L' [m] = "
                f"{model.effective_width:,.4f}/{model.effective_length:,.4f} = "
                f"{model.effective_width / model.effective_length:,.4f}\n"
                "       Nq [-] = exp(pi x tan(phi')) x tan^2(45 deg + phi'/2)\n"
                f"          = exp(pi x tan({model.friction_angle:,.4f})) x "
                f"tan^2(45 + {model.friction_angle:,.4f}/2) = "
                f"{model.capacity['N_q [-]']:,.4f}\n"
                f"       Nq* [-] = {model.capacity['N_q [-]']:,.4f}"
                f"{' (N_q [-])' if nq_used == model.capacity['N_q [-]'] else ' - 1.0000'}"
                f" = {nq_used:,.4f}\n"
                "       Ngamma [-] = 1.5 x (Nq [-] - 1) x tan(phi')\n"
                f"              = 1.5 x ({model.capacity['N_q [-]']:,.4f} - 1) x "
                f"tan({model.friction_angle:,.4f}) = {model.capacity['N_gamma [-]']:,.4f}\n"
                "       Kq [-] = iq [-] x sq [-] x dq [-] x bq [-] x gq [-]\n"
                f"          = {model.capacity['i_q [-]']:,.4f} x {model.capacity['s_q [-]']:,.4f} x "
                f"{model.capacity['d_q [-]']:,.4f} x {model.capacity['b_q [-]']:,.4f} x "
                f"{model.capacity['g_q [-]']:,.4f} = {model.capacity['K_q [-]']:,.4f}\n"
                "       Kgamma [-] = igamma [-] x sgamma [-] x dgamma [-]\n"
                "                       x bgamma [-] x ggamma [-]\n"
                f"              = {model.capacity['i_gamma [-]']:,.4f} x "
                f"{model.capacity['s_gamma [-]']:,.4f} x {model.capacity['d_gamma [-]']:,.4f} x "
                f"{model.capacity['b_gamma [-]']:,.4f} x {model.capacity['g_gamma [-]']:,.4f} = "
                f"{model.capacity['K_gamma [-]']:,.4f}\n"
                f"       qv [kPa] = {model.effective_stress_base:,.4f} x "
                f"{nq_used:,.4f} x "
                f"{model.capacity['K_q [-]']:,.4f} = {q_term:,.4f} kPa\n"
                f"       qgamma [kPa] = 0.5 x {model.effective_unit_weight:,.4f} x "
                f"{model.effective_width:,.4f} x {model.capacity['N_gamma [-]']:,.4f} x "
                f"{model.capacity['K_gamma [-]']:,.4f} = {gamma_term:,.4f} kPa\n"
                f"       qu [kPa] = {q_term:,.4f} + {gamma_term:,.4f} = "
                f"{model.net_bearing_pressure:,.4f} kPa"
            )
        else:
            nc = 5.14
            kc = model.capacity["K_c [-]"]
            kc_derivation = (
                "       Kc [-] = 1 + sc [-] + dc [-] - ic [-] - bc [-] - gc [-]\n"
                f"          = 1 + {model.capacity['s_c [-]']:,.4f} + "
                f"{model.capacity['d_c [-]']:,.4f} - {model.capacity['i_c [-]']:,.4f} - "
                f"{model.capacity['b_c [-]']:,.4f} - {model.capacity['g_c [-]']:,.4f} = {kc:,.4f}\n"
            )
            if model.su_increase == 0.0:
                qu_derivation_text = (
                    "     qu [kPa] = su [kPa] x Nc [-] x Kc [-]\n"
                    + f"       Nc [-] = {nc:,.4f}\n"
                    + kc_derivation
                    + f"       qu [kPa] = {model.su_base:,.4f} x {nc:,.4f} x {kc:,.4f}\n"
                    + f"       qu [kPa] = {model.net_bearing_pressure:,.4f} kPa"
                )
            else:
                factor_f = model.capacity["F [-]"]
                gradient_term = 0.25 * model.su_increase * model.effective_width
                qu_derivation_text = (
                    "     qu [kPa] = F [-] x Kc [-] x (su [kPa] x Nc [-]\n"
                    "                + 0.25 x kappa [kPa/m] x B' [m])\n"
                    + f"       Nc [-] = {nc:,.4f}; F [-] = {factor_f:,.4f}\n"
                    + kc_derivation
                    + f"       qu [kPa] = {factor_f:,.4f} x {kc:,.4f} x "
                    + f"({model.su_base:,.4f} x {nc:,.4f} + {gradient_term:,.4f})\n"
                    + f"       qu [kPa] = {model.net_bearing_pressure:,.4f} kPa"
                )

        bearing_area = model.effective_width * model.effective_length
        bearing_component = model.net_bearing_pressure * bearing_area
        additional_capacity = model.ultimate_capacity - bearing_component
        if self.drainage_var.get() == "Undrained" and not model.skirted:
            base_stress = model.unit_weight * model.depth
            additional_derivation = (
                f"       sigma_v0 [kPa] = gamma x D = {model.unit_weight:,.4f} x "
                f"{model.depth:,.4f} = {base_stress:,.4f} kPa\n"
                f"       Vadd [kN] = sigma_v0 x A' = {base_stress:,.4f} x "
                f"{bearing_area:,.4f} = {additional_capacity:,.4f} kN\n"
            )
        else:
            additional_derivation = (
                f"       Vadd [kN] = {additional_capacity:,.4f} "
                "(no additional base-stress contribution)\n"
            )
        capacity_derivation_text = (
            "     Vult [kN] = qu [kPa] x B' [m] x L' [m] + Vadd [kN]\n"
            f"       Vb [kN] = {model.net_bearing_pressure:,.4f} x "
            f"{model.effective_width:,.4f} x {model.effective_length:,.4f} = "
            f"{bearing_component:,.4f} kN\n"
            + additional_derivation
            + f"       Vult [kN] = {bearing_component:,.4f} + "
            f"{additional_capacity:,.4f} = "
            f"{model.ultimate_capacity:,.4f} kN"
        )

        symbol_lines = [
            "",
            "4. SYMBOLS AND UNITS",
            "   B [m]                 : Foundation width or diameter.",
            "   R [m]                 : Foundation radius.",
            "   L [m]                 : Foundation length.",
            "   e, eL, eB [m]         : Applied load eccentricities.",
            "   B' [m]                : Effective foundation width.",
            "   L' [m]                : Effective foundation length.",
            "   A [m^2]               : Full foundation area.",
            "   A' [m^2]              : Effective foundation area.",
            "   D [m]                 : Foundation embedment depth.",
            "   qu [kPa]              : Ultimate bearing pressure.",
            "   qu,f [kPa]            : Factored bearing pressure.",
            "   Vult [kN]             : Ultimate vertical capacity.",
            "   Vult,f [kN]           : Factored vertical capacity.",
            "   Vb [kN]               : Bearing component of vertical capacity.",
            "   Vadd [kN]             : Additional vertical-capacity contribution.",
            "   V [kN]                : Vertical load or resistance.",
            "   H [kN]                : Horizontal load or resistance.",
            "   Hmax [kN]             : Maximum horizontal resistance on the V-H envelope.",
            "   Hmax,f [kN]           : Factored maximum horizontal resistance.",
            "   theta [deg]           : Load inclination used for an envelope point.",
            "   Hb,outside [kN]       : Base sliding resistance outside the effective area.",
            "   Aemb [m^2]            : Embedded vertical section area.",
            "   Hb [kN]               : Base contribution to sliding resistance.",
            "   Hs [kN]               : Skirt contribution to sliding resistance.",
            "   Hu [kN]               : Ultimate sliding resistance.",
            "   Hu,f [kN]             : Factored ultimate sliding resistance.",
            "   RFb [-]               : Bearing resistance factor.",
            "   RFs [-]               : Sliding resistance factor.",
        ]
        if self.source_var.get() == "PCPT correlations" and self.pcpt_parameters:
            symbol_lines.extend([
                "   zfrom, zto [m]        : Lower and upper depth boundaries of the selected PCPT data.",
                "   zPCPT [m]             : Selected PCPT depth interval [zfrom, zto].",
            ])
        if self.drainage_var.get() == "Drained":
            symbol_lines.extend([
                "   gamma' [kN/m^3]      : Effective soil unit weight.",
                "   phi' [deg]            : Effective friction angle.",
                "   sigma'v0 [kPa]        : Effective vertical stress at foundation base.",
                "   Nq [-]                : Effective-overburden bearing-capacity factor.",
                "   Nq* [-]               : Nq term used in the bearing-pressure equation.",
                "   Ngamma [-]            : Unit-weight bearing-capacity factor.",
                "   Kq [-]                : Combined correction factor for the Nq term.",
                "   Kgamma [-]            : Combined correction factor for the Ngamma term.",
                "   qv [kPa]              : Effective-stress contribution to qu.",
                "   qgamma [kPa]          : Unit-weight contribution to qu.",
                "   sq, dq, iq, bq, gq [-]: Shape, depth, load, foundation and ground factors.",
                "   sgamma, dgamma, igamma, bgamma, ggamma [-]: Corresponding unit-weight factors.",
                "   delta [deg]           : Foundation-soil interface friction angle.",
                "   Kp [-]                : Passive earth-pressure coefficient.",
                "   Krd [-]               : Passive-resistance coefficient.",
            ])
        else:
            symbol_lines.extend([
                "   gamma [kN/m^3]       : Total soil unit weight.",
                "   su [kPa]              : Undrained shear strength at foundation base.",
                "   sigma_v0 [kPa]        : Total vertical stress at foundation base.",
                "   kappa [kPa/m]         : Undrained-strength increase with depth.",
                "   Nc [-]                : Undrained bearing-capacity factor.",
                "   Kc [-]                : Combined undrained correction factor.",
                "   sc, dc, ic, bc, gc [-]: Shape, depth, load, foundation and ground factors.",
                "   F [-]                 : Strength-increase correction factor.",
                "   su,a [kPa]            : Undrained shear strength above foundation base.",
                "   Kr [-]                : Undrained soil-reaction coefficient.",
            ])

        lines.extend([
            "",
            "3. RESISTANCE FACTORS",
            f"   RFb [-]: {bearing_factor:,.4f}",
            f"   RFs [-]: {sliding_factor:,.4f}",
        ])
        lines.extend(symbol_lines)
        lines.extend([
            "",
            "5. PRINCIPAL RESULTS",
            f"   qu [kPa]: {model.net_bearing_pressure:,.4f}",
            qu_derivation_text,
            f"   qu,f [kPa]: {factored_pressure:,.4f}",
            f"     qu,f = qu / RFb = {model.net_bearing_pressure:,.4f} / "
            f"{bearing_factor:,.4f} = "
            f"{factored_pressure:,.4f} kPa",
            f"   Vult [kN]: {model.ultimate_capacity:,.4f}",
            capacity_derivation_text,
            f"   Vult,f [kN]: {factored_capacity:,.4f}",
            f"     Vult,f = Vult / RFb = {model.ultimate_capacity:,.4f} / "
            f"{bearing_factor:,.4f} = "
            f"{factored_capacity:,.4f} kN",
            "",
            "   Analysis of principal results",
            f"   - Effective area retained: {effective_area_ratio:,.2f}% of full area.",
            f"     {area_ratio_derivation}.",
            f"   - {area_effect_text}",
            f"   - Bearing factor reduces vertical resistance by "
            f"{100.0 * (1.0 - 1.0 / bearing_factor):,.2f}%.",
            f"   - Maximum V: Vult={vertical_unfactored_max:,.2f} kN unfactored and "
            f"Vult,f={vertical_factored_max:,.2f} kN factored "
            f"({vertical_reduction:,.2f}% reduction).",
            f"     Vult,f = Vult / RFb = {vertical_unfactored_max:,.4f} / "
            f"{bearing_factor:,.4f} = {vertical_factored_max:,.4f} kN.",
            f"     Reduction = {vertical_reduction_derivation}.",
            f"   - Maximum H: Hmax={horizontal_unfactored_max:,.2f} kN unfactored and "
            f"Hmax,f={horizontal_factored_max:,.2f} kN factored "
            f"({horizontal_reduction:,.2f}% reduction).",
            f"     Hmax,f = Hmax / RFs = {horizontal_unfactored_max:,.4f} / "
            f"{sliding_factor:,.4f} = {horizontal_factored_max:,.4f} kN.",
            f"     Reduction = {horizontal_reduction_derivation}.",
            *envelope_derivation,
            f"   - {pressure_ratio_text}",
            "   - Loads inside the factored envelope have available calculated resistance;",
            "     loads outside the envelope exceed it. For drained loading, the factored",
            "     sliding cutoff must also be satisfied.",
            "   - No applied design loads were entered, so utilization and pass/fail",
            "     cannot be determined.",
            "",
            "6. BEARING-CAPACITY COMPONENTS",
        ])
        for key, value in model.capacity.items():
            lines.append(f"   {key:<34}: {self._report_value(value)}")
        lines.extend(self._bearing_components_analysis(model))
        lines.extend(["", "7. SLIDING-CAPACITY COMPONENTS"])
        for key, value in model.sliding.items():
            if self.drainage_var.get() == "Drained" and key in {
                "base_capacity [kN]",
                "sliding_capacity [kN]",
            }:
                continue
            lines.append(f"   {key:<34}: {self._report_value(value)}")
        lines.extend(self._sliding_components_analysis(model))

        lines.extend([
            "",
            "8. FORMULA SOURCES AND STANDARDS",
            "",
            "   FORMULATION BASIS",
            "   - API Recommended Practice 2GEO/ISO 19901-4:2003, Geotechnical and",
            "     Foundation Design Considerations, 1st Edition, April 2011.",
            "   - API RP 2GEO is a modified U.S. national adoption of",
            "     ISO 19901-4:2003. API issued Addendum 1 in October 2014.",
            "   - The Groundhog functions used by this application cite API RP 2GEO",
            "     (2011) for the drained and undrained shallow-foundation bearing",
            "     capacity, sliding resistance, effective-area and V-H failure-envelope",
            "     formulations.",
            "",
            "   CURRENT ISO EDITION",
            "   - ISO 19901-4:2025, Oil and gas industries including lower carbon",
            "     energy — Specific requirements for offshore structures — Part 4:",
            "     Geotechnical design considerations, 3rd Edition, February 2025.",
            "   - ISO 19901-4:2025 supersedes ISO 19901-4:2016; the earlier 2003 and",
            "     2016 editions are withdrawn by ISO.",
            "   - The equations in this application retain the API RP 2GEO (2011)",
            "     implementation. They have not been checked equation-by-equation",
            "     against ISO 19901-4:2025 and must not be represented as compliance",
            "     with, or verification to, the 2025 edition.",
            "",
            "   PCPT PARAMETER CORRELATIONS (WHEN PCPT INPUT IS SELECTED)",
            "   - Friction angle: Kulhawy, F.H. and Mayne, P.W. (1990), Manual on",
            "     Estimating Soil Properties for Foundation Design, EPRI EL-6800.",
            "   - Undrained shear strength: Rad, N.S. and Lunne, T. (1988), Direct",
            "     Correlations between Piezocone Test Results and Undrained Shear",
            "     Strength of Clay, ISOPT-1, Vol. 2, pp. 911-917.",
            "   - Soil unit weight: Mayne, P.W., Peuchen, J. and Bouwmeester, D.",
            "     (2010), Soil Unit Weight Estimation from CPTs, CPT'10, Paper 2-5.",
            "   - These are empirical parameter correlations, not foundation-design",
            "     standards. Their applicability and parameter selection require",
            "     engineering judgement and site-specific validation.",
            "",
            "   DESIGN-USE LIMITATION",
            "   - This report documents the calculation basis; it is not a declaration",
            "     of code compliance. Confirm the governing edition, national or project",
            "     requirements, load combinations, resistance factors and soil parameters",
            "     before using the results for design.",
            "",
            "9. DESIGN NOTE",
            "   The undrained shear strength is an input soil parameter; it is not",
            "   the bearing pressure. Bearing pressure includes capacity and geometry",
            "   factors. Confirm correlation choices and resistance factors against the",
            "   governing design standard and site-specific ground investigation.",
            "",
            "10. CALCULATION RESULTS SUMMARY",
            f"   Input {summary_soil_input}",
            f"   Ultimate bearing pressure, qu [kPa]       : {model.net_bearing_pressure:,.2f}",
            f"   Factored bearing pressure, qu,f [kPa]     : {factored_pressure:,.2f}",
            f"   Ultimate vertical capacity, Vult [kN]     : {model.ultimate_capacity:,.2f}",
            f"   Factored vertical capacity, Vult,f [kN]   : {factored_capacity:,.2f}",
            f"   Maximum envelope resistance, Hmax [kN]    : {horizontal_unfactored_max:,.2f}",
            f"   Factored maximum resistance, Hmax,f [kN]  : {horizontal_factored_max:,.2f}",
            f"   Effective foundation area, A' [m^2]       : {model.effective_area:,.4f}",
            "",
            "   These are calculated resistances. No applied design loads were entered,",
            "   so utilization and pass/fail cannot be determined.",
        ])
        # Present engineering notation consistently with the input form while
        # retaining the library's ASCII dictionary keys internally.
        symbol_replacements = (
            ("sigma'_v0", "σ′v0"),
            ("sigma'v0", "σ′v0"),
            ("sigma_v0", "σv0"),
            ("gamma'", "γ′"),
            ("gamma_w", "γw"),
            ("phi'", "φ′"),
            ("delta'", "δ′"),
            ("kappa", "κ"),
            ("gamma", "γ"),
            ("delta", "δ"),
            ("sigma", "σ"),
        )
        # Labels are padded above while they still contain ASCII symbol names.
        # Replacing (for example) ``gamma`` with ``γ`` shortens the label and
        # used to pull its value separator to the left.  Preserve the separator
        # column for table-style rows while still replacing symbols everywhere.
        for old_symbol, new_symbol in symbol_replacements:
            replaced_lines = []
            for line in lines:
                separator = line.find(" : ")
                label = line[:separator] if separator >= 0 else line
                removed_before_separator = label.count(old_symbol) * (
                    len(old_symbol) - len(new_symbol)
                )
                replaced = line.replace(old_symbol, new_symbol)
                if separator >= 0 and removed_before_separator > 0:
                    new_separator = replaced.find(" : ")
                    replaced = (
                        replaced[:new_separator]
                        + " " * removed_before_separator
                        + replaced[new_separator:]
                    )
                replaced_lines.append(replaced)
            lines = replaced_lines

        self.results_text.configure(state="normal")
        self.results_text.delete("1.0", "end")
        self.results_text.insert("1.0", "\n".join(lines))
        self.results_text.configure(state="disabled")
        self.results_text.see("1.0")

    @staticmethod
    def _factor_effect(name, value):
        if np.isnan(value):
            return f"   - {name} is not applicable for this calculation."
        if value > 1.0001:
            return f"   - {name} = {value:,.4f} increases the associated resistance term."
        if value < 0.9999:
            return f"   - {name} = {value:,.4f} reduces the associated resistance term."
        return f"   - {name} = {value:,.4f} has a neutral effect."

    def _bearing_components_analysis(self, model):
        c = model.capacity
        lines = ["", "   Analysis of Section 6 components"]
        if self.drainage_var.get() == "Drained":
            lines.extend([
                "   - For the principal vertical-capacity point, theta = nu = beta = 0 deg.",
                f"   - iq = [1 - 0.5 tan(theta)]^5 = [1 - 0.5 tan(0)]^5 = "
                f"{c['i_q [-]']:,.4f}.",
                f"   - igamma = [1 - 0.7 tan(theta)]^5 = [1 - 0.7 tan(0)]^5 = "
                f"{c['i_gamma [-]']:,.4f}.",
                f"   - sq = 1 + iq(B'/L')sin(phi') = 1 + {c['i_q [-]']:,.4f} x "
                f"({model.effective_width:,.4f}/{model.effective_length:,.4f}) x "
                f"sin({model.friction_angle:,.4f}) = {c['s_q [-]']:,.4f}.",
                f"   - sgamma = 1 - 0.4igamma(B'/L') = 1 - 0.4 x "
                f"{c['i_gamma [-]']:,.4f} x ({model.effective_width:,.4f}/"
                f"{model.effective_length:,.4f}) = {c['s_gamma [-]']:,.4f}.",
                "   - dq = 1 + 1.2(D/B')tan(phi')[1-sin(phi')]^2",
                f"     = 1 + 1.2 x ({model.depth:,.4f}/{model.effective_width:,.4f}) x "
                f"tan({model.friction_angle:,.4f}) x [1-sin({model.friction_angle:,.4f})]^2 "
                f"= {c['d_q [-]']:,.4f}.",
                f"   - dgamma = 1.0000 = {c['d_gamma [-]']:,.4f}.",
                f"   - bq = exp[-2 nu tan(phi')] = exp[-2 x 0 x tan({model.friction_angle:,.4f})] "
                f"= {c['b_q [-]']:,.4f}.",
                f"   - bgamma = exp[-2.7 nu tan(phi')] = {c['b_gamma [-]']:,.4f}.",
                f"   - gq = ggamma = [1 - 0.5 tan(beta)]^5 = "
                f"[1 - 0.5 tan(0)]^5 = {c['g_q [-]']:,.4f}.",
                f"   - N_q [-] = {c['N_q [-]']:,.4f} represents the effective-overburden",
                "     contribution controlled mainly by effective_friction_angle [deg].",
                f"   - N_gamma [-] = {c['N_gamma [-]']:,.4f} represents the soil-unit-weight",
                "     contribution beneath the effective foundation width.",
                self._factor_effect("s_q [-] (shape factor)", c["s_q [-]"]),
                self._factor_effect("d_q [-] (depth factor)", c["d_q [-]"]),
                self._factor_effect("i_q [-] (load-inclination factor)", c["i_q [-]"]),
                self._factor_effect("b_q [-] (foundation-inclination factor)", c["b_q [-]"]),
                self._factor_effect("g_q [-] (ground-inclination factor)", c["g_q [-]"]),
                f"   - K_q [-] = {c['K_q [-]']:,.4f} is the product of the five q factors above.",
                self._factor_effect("s_gamma [-] (shape factor)", c["s_gamma [-]"]),
                self._factor_effect("d_gamma [-] (depth factor)", c["d_gamma [-]"]),
                self._factor_effect("i_gamma [-] (load-inclination factor)", c["i_gamma [-]"]),
                self._factor_effect("b_gamma [-] (foundation-inclination factor)", c["b_gamma [-]"]),
                self._factor_effect("g_gamma [-] (ground-inclination factor)", c["g_gamma [-]"]),
                f"   - K_gamma [-] = {c['K_gamma [-]']:,.4f} is the product of the five gamma factors.",
            ])
        else:
            area_effective = model.effective_width * model.effective_length
            lines.extend([
                "   - For the principal vertical-capacity point, H' = nu = beta = 0.",
                f"   - ic = 0.5 - 0.5sqrt[1-H'/(A'su)] = 0.5 - 0.5sqrt[1-0/"
                f"({area_effective:,.4f} x {model.su_base:,.4f})] = {c['i_c [-]']:,.4f}.",
                f"   - bc = 2nu/(pi+2) = 0 = {c['b_c [-]']:,.4f}.",
                f"   - gc = 2beta/(pi+2) = 0 = {c['g_c [-]']:,.4f}.",
                f"   - s_c [-] = {c['s_c [-]']:,.4f} is added as the shape contribution to K_c [-].",
                f"   - d_c [-] = {c['d_c [-]']:,.4f} is added as the depth contribution to K_c [-].",
                f"   - i_c [-] = {c['i_c [-]']:,.4f} is subtracted for load inclination.",
                f"   - b_c [-] = {c['b_c [-]']:,.4f} is subtracted for foundation inclination.",
                f"   - g_c [-] = {c['g_c [-]']:,.4f} is subtracted for ground inclination.",
                f"   - K_c [-] = {c['K_c [-]']:,.4f} combines these effects with the base value 1.0.",
            ])
            if model.su_increase == 0.0:
                lines.extend([
                    f"   - sc = 0.18(1-2ic)(B'/L') = 0.18 x (1-2 x "
                    f"{c['i_c [-]']:,.4f}) x ({model.effective_width:,.4f}/"
                    f"{model.effective_length:,.4f}) = {c['s_c [-]']:,.4f}.",
                    f"   - dc = 0.3atan(D/B') = 0.3atan({model.depth:,.4f}/"
                    f"{model.effective_width:,.4f}) = {c['d_c [-]']:,.4f}.",
                ])
            else:
                dimensionless_increase = (
                    model.su_increase * model.effective_width / model.su_base
                )
                lines.extend([
                    f"   - x = kappa B'/su = {model.su_increase:,.4f} x "
                    f"{model.effective_width:,.4f} / {model.su_base:,.4f} = "
                    f"{dimensionless_increase:,.4f}.",
                    f"   - su,2 = F(Nc su + kappa B'/4)/Nc = {c['Su2 [kPa]']:,.4f} kPa.",
                    f"   - sc = scv(1-2ic)(B'/L') = {c['s_c [-]']:,.4f}.",
                    f"   - dc = 0.3(su,a/su,2)atan(D/B') = {c['d_c [-]']:,.4f}.",
                ])
            if np.isfinite(c.get("F [-]", np.nan)):
                lines.append(
                    f"   - F [-] = {c['F [-]']:,.4f} corrects for undrained strength increase with depth."
                )
            else:
                lines.append("   - F [-] is not applicable because su_increase [kPa/m] is zero.")
        lines.extend([
            f"   - qu [kPa] = {c['qu [kPa]']:,.4f} is the resulting ultimate bearing pressure.",
            f"   - vertical_capacity [kN] = {c['vertical_capacity [kN]']:,.4f} is the",
            "     corresponding vertical resistance over the effective dimensions, including",
            "     any additional base-stress contribution implemented by the method.",
        ])
        return lines

    def _sliding_components_analysis(self, model):
        s = model.sliding
        if model.option == "circle":
            out_of_plane = model.diameter
        else:
            out_of_plane = model.length
        embedded_area = model.depth * out_of_plane
        lines = ["", "   Analysis and derivation of Section 7 components"]
        if self.drainage_var.get() == "Drained":
            interface_angle = float(self.interface_friction_var.get())
            friction_coefficient = np.tan(np.radians(interface_angle))
            skirt_capacity = s["skirt_capacity [kN]"]
            lines.extend([
                "   - No arbitrary fixed vertical load is assumed. Sliding resistance is",
                "     evaluated as a function of the applied vertical load V.",
                f"   - delta [deg] = {interface_angle:,.4f} (drained input).",
                "   - Hb(V) [kN] = V [kN] x tan(delta)",
                f"     = V x tan({interface_angle:,.4f}) = {friction_coefficient:,.4f} x V.",
                "   - Kp [-] = tan^2(45 deg + delta/2)",
                f"     = tan^2(45 + {interface_angle:,.4f}/2) = {s['K_p [-]']:,.4f}.",
                "   - Krd [-] = Kp [-] - 1/Kp [-]",
                f"     = {s['K_p [-]']:,.4f} - 1/{s['K_p [-]']:,.4f} = {s['K_rd [-]']:,.4f}.",
                f"   - Aemb [m2] = D [m] x out-of-plane dimension [m] = "
                f"{model.depth:,.4f} x {out_of_plane:,.4f} = {embedded_area:,.4f} m2.",
                "   - Hs [kN] = 0.5 x Krd [-] x gamma' [kN/m3] x D [m] x Aemb [m2]",
                f"     = 0.5 x {s['K_rd [-]']:,.4f} x {model.effective_unit_weight:,.4f} x "
                f"{model.depth:,.4f} x {embedded_area:,.4f} = "
                f"{s['skirt_capacity [kN]']:,.4f} kN.",
                f"   - Hu(V) [kN] = Hb(V) + Hs = {friction_coefficient:,.4f} x V + "
                f"{skirt_capacity:,.4f}.",
                f"   - Hu,f(V) = Hu(V) / RFs = ({friction_coefficient:,.4f} x V + "
                f"{skirt_capacity:,.4f}) / {self.sliding_factor_var.get()}.",
                "   - The dashed graph lines plot these equations over the full V range.",
            ])
        else:
            reaction_coefficient = 4.0
            lines.extend([
                "   - Hb [kN] = su [kPa] x A [m2]",
                f"     = {model.su_base:,.4f} x {model.full_area:,.4f} = "
                f"{s['base_resistance [kN]']:,.4f} kN.",
                f"   - Aemb [m2] = {model.depth:,.4f} x "
                f"{out_of_plane:,.4f} = {embedded_area:,.4f} m2.",
                "   - Hs [kN] = Kr [-] x su,a [kPa] x Aemb [m2]",
                f"     = {reaction_coefficient:,.4f} x {model.su_above_base:,.4f} x "
                f"{embedded_area:,.4f} = {s['skirt_resistance [kN]']:,.4f} kN.",
                f"   - Hu [kN] = {s['base_resistance [kN]']:,.4f} + "
                f"{s['skirt_resistance [kN]']:,.4f} = {s['sliding_capacity [kN]']:,.4f} kN.",
                f"   - Hu,f = Hu / RFs = {s['sliding_capacity [kN]']:,.4f} / "
                f"{self.sliding_factor_var.get()} = "
                f"{s['sliding_capacity [kN]'] / float(self.sliding_factor_var.get()):,.4f} kN.",
            ])
        total = s["sliding_capacity [kN]"]
        if self.drainage_var.get() == "Undrained" and total:
            base_key = "base_capacity [kN]" if "base_capacity [kN]" in s else "base_resistance [kN]"
            lines.append(
                f"   - Base contribution is {100.0 * s[base_key] / total:,.2f}% of total sliding resistance."
            )
        lines.append(
            f"   - The sliding resistance factor {self.sliding_factor_var.get()} is applied to the factored V-H envelope."
        )
        return lines

    # ---------------------------- PCPT tab ----------------------------
    def _build_pcpt_tab(self):
        self.pcpt_tab = ttk.Frame(self.tabs)
        self.tabs.add(self.pcpt_tab, text="PCPT Processing")
        self.pcpt_tab.columnconfigure(1, weight=1)
        self.pcpt_tab.rowconfigure(0, weight=1)

        controls_panel = ttk.Frame(self.pcpt_tab)
        controls_panel.grid(row=0, column=0, sticky="nsew")
        controls_panel.rowconfigure(0, weight=1)
        controls_panel.columnconfigure(0, weight=1)

        controls_canvas = tk.Canvas(
            controls_panel,
            width=390,
            yscrollincrement=24,
            highlightthickness=0,
            borderwidth=0,
        )
        controls_scrollbar = ttk.Scrollbar(
            controls_panel, orient="vertical", command=controls_canvas.yview
        )
        controls_canvas.configure(yscrollcommand=controls_scrollbar.set)
        controls_canvas.grid(row=0, column=0, sticky="nsew")
        controls_scrollbar.grid(row=0, column=1, sticky="ns")

        controls = ttk.Frame(controls_canvas, padding=10)
        controls_window = controls_canvas.create_window((0, 0), window=controls, anchor="nw")
        controls.bind(
            "<Configure>",
            lambda _event: controls_canvas.configure(scrollregion=controls_canvas.bbox("all")),
        )
        controls_canvas.bind(
            "<Configure>",
            lambda event: controls_canvas.itemconfigure(controls_window, width=event.width),
        )

        def scroll_pcpt_form(event):
            controls_canvas.yview_scroll(int(-event.delta / 120), "units")

        charts_canvas = tk.Canvas(
            self.pcpt_tab, highlightthickness=0, borderwidth=0, yscrollincrement=32
        )
        charts_scrollbar = ttk.Scrollbar(
            self.pcpt_tab, orient="vertical", command=charts_canvas.yview
        )
        charts_canvas.configure(yscrollcommand=charts_scrollbar.set)
        charts_canvas.grid(row=0, column=1, sticky="nsew")
        charts_scrollbar.grid(row=0, column=2, sticky="ns")
        charts = ttk.Frame(charts_canvas, padding=8)
        charts_window = charts_canvas.create_window((0, 0), window=charts, anchor="nw")
        charts.bind(
            "<Configure>",
            lambda _event: charts_canvas.configure(scrollregion=charts_canvas.bbox("all")),
        )
        charts_canvas.bind(
            "<Configure>",
            lambda event: charts_canvas.itemconfigure(charts_window, width=event.width),
        )
        charts.rowconfigure(1, minsize=245)
        charts.rowconfigure(2, minsize=680)
        charts.columnconfigure(0, weight=1)

        ttk.Button(controls, text="← Back to workflow selection", command=lambda: self.tabs.select(self.start_tab)).pack(
            fill="x", pady=(0, 6)
        )

        file_box = ttk.LabelFrame(controls, text="Step 1 – Select PCPT Excel data", padding=8)
        file_box.pack(fill="x", pady=5)
        ttk.Entry(file_box, textvariable=self.pcpt_file, width=42).pack(fill="x", pady=4)
        self.choose_pcpt_file_button = ttk.Radiobutton(
            file_box,
            text="Choose Excel file",
            variable=self.pcpt_source_choice,
            value="custom",
            command=self.choose_pcpt_file,
            style="SourceChoice.Toolbutton",
        )
        self.choose_pcpt_file_button.pack(fill="x", pady=2)
        self.example_pcpt_file_button = ttk.Radiobutton(
            file_box,
            text="Use and load bundled example",
            variable=self.pcpt_source_choice,
            value="example",
            command=self.use_example_file,
            style="SourceChoice.Toolbutton",
        )
        self.example_pcpt_file_button.pack(fill="x", pady=2)
        self.save_pcpt_button = ttk.Button(
            file_box,
            text="Save edited Excel as…",
            command=self.save_edited_pcpt_as,
            state="disabled",
        )
        self.save_pcpt_button.pack(fill="x", pady=(8, 2))

        self.area_ratio_var = tk.StringVar(value="0.80")
        self.mapping_unit_weight_var = tk.StringVar(value="18.0")
        self.water_level_var = tk.StringVar(value="0.0")
        self.depth_from_var = tk.StringVar(value="1.0")
        self.depth_to_var = tk.StringVar(value="3.0")
        self.nk_var = tk.StringVar(value="15.0")
        self.statistic_var = tk.StringVar(value="Median")

        processing = ttk.LabelFrame(controls, text="Step 1 – Processing inputs", padding=8)
        processing.pack(fill="x", pady=5)
        self._entry(processing, "Cone area ratio, a (-)", self.area_ratio_var, 0)
        self._entry(processing, "Mapping unit weight, γmap (kN/m³)", self.mapping_unit_weight_var, 1)
        self._entry(processing, "Water level, zw (m)", self.water_level_var, 2)
        self.load_pcpt_button = ttk.Button(
            controls, text="Step 1 – Load and normalise PCPT", command=self.load_pcpt
        )
        self.load_pcpt_button.pack(
            fill="x", pady=(8, 5), ipady=4
        )
        self.pcpt_loading_frame = ttk.Frame(controls)
        ttk.Label(self.pcpt_loading_frame, text="Loading and normalising PCPT data…").pack(
            anchor="w", pady=(0, 3)
        )
        self.pcpt_loading_progress = ttk.Progressbar(
            self.pcpt_loading_frame, mode="indeterminate"
        )
        self.pcpt_loading_progress.pack(fill="x")

        correlations = ttk.LabelFrame(controls, text="Step 2 – Foundation correlations", padding=8)
        correlations.pack(fill="x", pady=5)
        self._entry(correlations, "Depth from, zfrom (m)", self.depth_from_var, 0)
        self._entry(correlations, "Depth to, zto (m)", self.depth_to_var, 1)
        self._entry(correlations, "Cone factor, Nk (-)", self.nk_var, 2)
        ttk.Label(correlations, text="Statistic").grid(row=3, column=0, sticky="w", padx=5, pady=4)
        ttk.Combobox(
            correlations, textvariable=self.statistic_var,
            values=["Median", "Mean"], state="readonly", width=14,
        ).grid(row=3, column=1, sticky="ew", padx=5, pady=4)
        self.correlate_button = ttk.Button(
            controls,
            text="Step 2 – Calculate PCPT correlations",
            command=self.calculate_pcpt_correlations,
            state="disabled",
        )
        self.correlate_button.pack(
            fill="x", pady=(8, 3), ipady=4
        )
        self.transfer_button = ttk.Button(
            controls,
            text="Step 3 – Transfer to foundation form",
            command=self.use_pcpt_parameters,
            state="disabled",
        )
        self.transfer_button.pack(
            fill="x", pady=3, ipady=4
        )

        self.pcpt_result = tk.StringVar(value="No PCPT data processed.")
        ttk.Label(charts, textvariable=self.pcpt_result, style="Result.TLabel", justify="left").grid(
            row=0, column=0, sticky="ew", pady=(0, 5)
        )

        data_box = ttk.LabelFrame(
            charts, text="Loaded Excel data (double-click a cell to edit)", padding=5
        )
        data_box.grid(row=1, column=0, sticky="nsew", pady=(0, 6))
        data_box.rowconfigure(1, weight=1)
        data_box.columnconfigure(0, weight=1)
        self.pcpt_header_canvas = tk.Canvas(
            data_box, height=40, background="#e7e5e1", highlightthickness=0
        )
        self.pcpt_header_frame = tk.Frame(self.pcpt_header_canvas, background="#e7e5e1")
        self.pcpt_header_window = self.pcpt_header_canvas.create_window(
            0, 0, window=self.pcpt_header_frame, anchor="nw"
        )
        self.pcpt_data_table = ttk.Treeview(
            data_box, show="", height=8, style="PCPT.Treeview"
        )
        data_y_scroll = ttk.Scrollbar(
            data_box, orient="vertical", command=self.pcpt_data_table.yview
        )
        def scroll_pcpt_x(*args):
            self.pcpt_data_table.xview(*args)
            self.pcpt_header_canvas.xview(*args)

        def update_pcpt_x_scroll(first, last):
            data_x_scroll.set(first, last)
            self.pcpt_header_canvas.xview_moveto(first)

        data_x_scroll = ttk.Scrollbar(data_box, orient="horizontal", command=scroll_pcpt_x)
        self.pcpt_data_table.configure(
            yscrollcommand=data_y_scroll.set, xscrollcommand=update_pcpt_x_scroll
        )
        self.pcpt_header_canvas.grid(row=0, column=0, sticky="ew")
        self.pcpt_data_table.grid(row=1, column=0, sticky="nsew")
        data_y_scroll.grid(row=1, column=1, sticky="ns")
        data_x_scroll.grid(row=2, column=0, sticky="ew")
        self.pcpt_table_loading_label = tk.Label(
            data_box,
            text="Loading PCPT data…",
            background="white",
            foreground="#666666",
            font=("Segoe UI", 12),
        )
        self.pcpt_table_loading_label.grid(row=1, column=0, sticky="nsew")
        self.pcpt_table_loading_label.grid_remove()
        self.pcpt_data_table.bind("<Double-1>", self._begin_pcpt_cell_edit)
        self.pcpt_data_editor = None
        self.pcpt_table_indices = []

        self.pcpt_figure = Figure(figsize=(10, 7), dpi=100)
        self.pcpt_canvas = FigureCanvasTkAgg(self.pcpt_figure, master=charts)
        graph_widget = self.pcpt_canvas.get_tk_widget()
        graph_widget.configure(height=680)
        graph_widget.grid(row=2, column=0, sticky="nsew")
        NavigationToolbar2Tk(self.pcpt_canvas, charts, pack_toolbar=False).grid(
            row=3, column=0, sticky="ew"
        )

        def scroll_pcpt_results(event):
            charts_canvas.yview_scroll(int(-event.delta / 120), "units")

        charts_canvas.bind("<MouseWheel>", scroll_pcpt_results, add="+")
        graph_widget.bind("<MouseWheel>", scroll_pcpt_results, add="+")

        def bind_mousewheel(widget):
            widget.bind("<MouseWheel>", scroll_pcpt_form, add="+")
            for child in widget.winfo_children():
                bind_mousewheel(child)

        bind_mousewheel(controls)

    def choose_pcpt_file(self):
        previous_choice = (
            "example" if Path(self.pcpt_file.get()) == EXAMPLE_PCPT else "custom"
        )
        filename = filedialog.askopenfilename(
            title="Select PCPT Excel file",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")],
        )
        if filename:
            self.pcpt_file.set(filename)
            self.pcpt_source_choice.set("custom")
            self.status.set(f"Loading selected Excel file: {Path(filename).name} …")
            self.update_idletasks()
            self.load_pcpt()
        else:
            self.pcpt_source_choice.set(previous_choice)

    def use_example_file(self):
        self.pcpt_source_choice.set("example")
        self.pcpt_file.set(str(EXAMPLE_PCPT))
        self.status.set(f"Loading bundled example: {EXAMPLE_PCPT.name} …")
        self.update_idletasks()
        self.load_pcpt()

    def load_pcpt(self):
        if self._pcpt_loading:
            return
        try:
            path = Path(self.pcpt_file.get()).expanduser().resolve()
            area_ratio = self._float(self.area_ratio_var, "Cone area ratio")
            unit_weight = self._float(self.mapping_unit_weight_var, "Mapping unit weight")
            water_level = self._float(self.water_level_var, "Water level")
        except Exception as error:
            messagebox.showerror("PCPT loading error", str(error))
            self.status.set(f"PCPT loading failed: {error}")
            return

        self._pcpt_loading = True
        self.load_pcpt_button.configure(state="disabled")
        self.choose_pcpt_file_button.configure(state="disabled")
        self.example_pcpt_file_button.configure(state="disabled")
        self.pcpt_loading_frame.pack(
            fill="x", pady=(0, 5), after=self.load_pcpt_button
        )
        self.pcpt_loading_progress.start(12)
        self.status.set("Loading and normalising PCPT Excel data…")
        self.update_idletasks()
        self.pcpt = None
        self.pcpt_parameters = None
        self.pcpt_dirty = False
        self.save_pcpt_button.configure(state="disabled")
        if hasattr(self, "pcpt_data_table"):
            self.pcpt_data_table.delete(*self.pcpt_data_table.get_children())
        self.pcpt_table_loading_label.grid()
        self.pcpt_table_loading_label.lift()
        self._clear_pcpt_plot("Loading PCPT data…")
        self._set_source_controls()
        self.correlate_button.configure(state="disabled")
        self.transfer_button.configure(state="disabled")
        threading.Thread(
            target=self._load_pcpt_worker,
            args=(path, area_ratio, unit_weight, water_level),
            daemon=True,
        ).start()
        self.after(50, self._poll_pcpt_load)

    def _load_pcpt_worker(self, path, area_ratio, unit_weight, water_level):
        """Read and process a PCPT workbook without blocking Tk's event loop."""
        try:
            if not path.is_file():
                raise FileNotFoundError(f"PCPT file not found: {path}")
            pcpt = PCPTProcessing(title=path.name)
            pcpt.load_excel(path, push_key="Push")
            input_columns = list(pcpt.data.columns)
            # Keep an unprocessed copy for the editable grid.  Groundhog adds
            # mapped/normalised columns to ``pcpt.data``; starting from this
            # clean copy prevents duplicate merge columns after a cell edit.
            raw_data = pcpt.data.copy(deep=True)
            maximum_depth = self._normalise_pcpt_data(
                pcpt, raw_data, area_ratio, unit_weight, water_level
            )
            self._pcpt_load_queue.put(
                ("success", path, pcpt, input_columns, raw_data, maximum_depth)
            )
        except Exception as error:
            self._pcpt_load_queue.put(("error", error))

    def _poll_pcpt_load(self):
        """Apply completed worker results on Tk's main thread."""
        try:
            result = self._pcpt_load_queue.get_nowait()
        except queue.Empty:
            self.after(50, self._poll_pcpt_load)
            return

        try:
            if result[0] == "error":
                raise result[1]
            _, path, pcpt, input_columns, raw_data, maximum_depth = result
            self.pcpt_input_columns = input_columns
            self.pcpt_raw_data = raw_data
            self.pcpt = pcpt
            self._populate_pcpt_data_table()
            self.correlate_button.configure(state="normal")
            self._plot_pcpt()
            self.pcpt_result.set(
                f"{path.name}: {len(pcpt.data):,} rows, maximum depth {maximum_depth:.3f} m"
            )
            self.status.set("PCPT loaded and normalised. Select a depth interval for correlations.")
        except Exception as error:
            messagebox.showerror("PCPT loading error", str(error))
            self.status.set(f"PCPT loading failed: {error}")
        finally:
            self._pcpt_loading = False
            self.pcpt_table_loading_label.grid_remove()
            self.pcpt_loading_progress.stop()
            self.pcpt_loading_frame.pack_forget()
            self.load_pcpt_button.configure(state="normal")
            self.choose_pcpt_file_button.configure(state="normal")
            self.example_pcpt_file_button.configure(state="normal")

    def save_edited_pcpt_as(self):
        """Save the user-edited source table to a new Excel workbook."""
        if self.pcpt is None or not hasattr(self, "pcpt_raw_data"):
            messagebox.showwarning("No PCPT data", "Load an Excel file before saving.")
            return
        source = Path(self.pcpt_file.get()).expanduser()
        suggested_name = f"{source.stem}_edited.xlsx"
        filename = filedialog.asksaveasfilename(
            title="Save edited PCPT Excel data as",
            initialdir=str(source.parent) if source.parent.exists() else str(ROOT_DIR),
            initialfile=suggested_name,
            defaultextension=".xlsx",
            filetypes=[("Excel workbook", "*.xlsx")],
        )
        if not filename:
            return
        destination = Path(filename).expanduser().resolve()
        try:
            if destination == source.resolve():
                raise ValueError("Choose a different filename so the original Excel file is preserved.")
            self.pcpt_raw_data.to_excel(destination, index=False)
            self.pcpt_file.set(str(destination))
            self.pcpt_source_choice.set("custom")
            self.pcpt_dirty = False
            self.save_pcpt_button.configure(state="disabled")
            self.status.set(f"Edited PCPT data saved as {destination.name}.")
            messagebox.showinfo(
                "PCPT Excel saved",
                f"The edited data was saved successfully as:\n{destination}",
            )
        except Exception as error:
            messagebox.showerror("Could not save PCPT Excel data", str(error))

    def _normalise_pcpt_data(
        self, pcpt, raw_data=None, area_ratio=None, unit_weight=None, water_level=None
    ):
        """Apply the processing inputs to the current, possibly edited, data."""
        source_data = self.pcpt_raw_data if raw_data is None else raw_data
        pcpt.data = source_data.copy(deep=True)
        if area_ratio is None:
            area_ratio = self._float(self.area_ratio_var, "Cone area ratio")
        if unit_weight is None:
            unit_weight = self._float(self.mapping_unit_weight_var, "Mapping unit weight")
        if water_level is None:
            water_level = self._float(self.water_level_var, "Water level")
        maximum_depth = float(pcpt.data["z [m]"].max())
        cone_data = deepcopy(DEFAULT_CONE_PROPERTIES)
        cone_data["Depth to [m]"] = cone_data["Depth to [m]"].astype(float)
        cone_data.loc[0, "Depth to [m]"] = maximum_depth
        cone_data.loc[0, "area ratio [-]"] = area_ratio
        cone_profile = profile_from_dataframe(cone_data)
        soil_profile = SoilProfile(
            {
                "Depth from [m]": [0.0],
                "Depth to [m]": [maximum_depth],
                "Total unit weight [kN/m3]": [unit_weight],
                "Soil type": ["Unspecified"],
            }
        )
        pcpt.map_properties(soil_profile, cone_profile, waterlevel=water_level)
        pcpt.normalise_pcpt()
        return maximum_depth

    @staticmethod
    def _display_pcpt_value(value):
        if value is None or (isinstance(value, (float, np.floating)) and np.isnan(value)):
            return ""
        if isinstance(value, (float, np.floating)):
            return f"{value:.8g}"
        return str(value)

    def _populate_pcpt_data_table(self):
        """Present every imported Excel row and its original columns."""
        table = self.pcpt_data_table
        table.delete(*table.get_children())
        columns = tuple(self.pcpt_input_columns)
        table.configure(columns=columns)
        column_headings = {
            "z [m]": ("Depth", "Z (m)"),
            "qc [MPa]": ("Measured cone resistance", "qᴄ [MPa]"),
            "fs [MPa]": ("Sleeve friction", "fₛ [MPa]"),
            "u2 [MPa]": ("Pore pressure", "u₂ [MPa]"),
            "Push": ("Sounding / push identifier", "Push"),
            "Bq [-]": ("Pore-pressure ratio", "Bₚ [-]"),
            "Rf [%]": ("Friction ratio", "Rᶠ [%]"),
            "Rf [pct]": ("Friction ratio", "Rᶠ [%]"),
            "qt [MPa]": ("Corrected total cone resistance", "qₜ [MPa]"),
            "qnet [MPa]": ("Net cone resistance", "qₙₑₜ [MPa]"),
            "Qt [-]": ("Normalised cone resistance", "Qₜ [-]"),
            "Fr [-]": ("Normalised friction ratio", "Fᵣ [-]"),
            "Fr [%]": ("Normalised friction ratio", "Fᵣ [%]"),
            "Ic [-]": ("Soil behaviour type index", "Iᴄ [-]"),
            "qc1N [-]": ("Corrected normalised cone resistance", "qᴄ₁N [-]"),
            "qc1 [-]": ("Normalised cone resistance", "qᴄ₁ [-]"),
            "qc1 [MPa]": ("Stress-corrected cone resistance", "qᴄ₁ [MPa]"),
            "ft [MPa]": ("Corrected total sleeve friction", "fₜ [MPa]"),
            "Dr [-]": ("Relative density", "Dᵣ [-]"),
            "Su [kPa]": ("Undrained shear strength", "Sᵤ [kPa]"),
            "PCPT Su [kPa]": ("CPT-derived undrained shear strength", "Sᵤ,CPT [kPa]"),
            "Total unit weight [kN/m3]": ("Total unit weight", "γ [kN/m³]"),
            "Submerged unit weight [kN/m3]": ("Submerged unit weight", "γ′ [kN/m³]"),
            "Water unit weight [kN/m3]": ("Water unit weight", "γₓ [kN/m³]"),
            "Effective unit weight [kN/m3]": ("Effective unit weight", "γ′ [kN/m³]"),
            "Hydrostatic pressure [kPa]": ("Hydrostatic pressure", "u₀ [kPa]"),
            "Vertical effective stress [kPa]": ("Vertical effective stress", "σ′ᵥ₀ [kPa]"),
            "Vertical total stress [kPa]": ("Vertical total stress", "σᵥ₀ [kPa]"),
            "area ratio [-]": ("Cone area ratio", "a [-]"),
            "gamma CPT [kN/m3]": ("CPT-derived total unit weight", "γᴄᴾᵀ [kN/m³]"),
            "Gamma CPT [kN/m3]": ("CPT-derived total unit weight", "γᴄᴾᵀ [kN/m³]"),
            "PCPT total unit weight [kN/m3]": ("CPT-derived total unit weight", "γᴄᴾᵀ [kN/m³]"),
            "Void ratio from CPT [-]": ("CPT-derived void ratio", "eᴄᴾᵀ [-]"),
            "Void ratio CPT [-]": ("CPT-derived void ratio", "eᴄᴾᵀ [-]"),
        }
        for child in self.pcpt_header_frame.winfo_children():
            child.destroy()
        horizontal_position = 0
        for column in columns:
            description, symbol = column_headings.get(column, ("Imported data", column))
            displayed_values = (
                self._display_pcpt_value(value)
                for value in self.pcpt_raw_data[column].dropna()
            )
            longest_value = max((len(value) for value in displayed_values), default=0)
            longest_text = max(len(description), len(symbol), longest_value)
            # Allow enough width for the complete description where needed,
            # while retaining a firm upper limit for unusually long fields.
            column_width = max(62, min(205, longest_text * 5 + 16))
            header = tk.Frame(
                self.pcpt_header_frame,
                background="#e7e5e1",
                relief="raised",
                borderwidth=1,
            )
            header.place(x=horizontal_position, y=0, width=column_width, height=40)
            tk.Label(
                header,
                text=symbol,
                font=("Segoe UI", 9),
                foreground="#20252a",
                background="#e7e5e1",
                anchor="n",
                justify="center",
                padx=1,
                pady=0,
            ).pack(side="top", fill="x", pady=(1, 0))
            tk.Label(
                header,
                text=description,
                font=("Segoe UI", 7),
                foreground="#20252a",
                background="#e7e5e1",
                anchor="n",
                justify="center",
                padx=1,
                pady=0,
                wraplength=max(column_width - 6, 48),
            ).pack(side="top", fill="x", pady=(0, 1))
            table.column(column, width=column_width, minwidth=45, stretch=False, anchor="center")
            horizontal_position += column_width
        self.pcpt_header_frame.configure(width=horizontal_position, height=40)
        self.pcpt_header_canvas.itemconfigure(
            self.pcpt_header_window, width=horizontal_position, height=40
        )
        self.pcpt_header_canvas.configure(scrollregion=(0, 0, horizontal_position, 40))
        self.pcpt_table_indices = list(self.pcpt.data.index)
        for position, index in enumerate(self.pcpt_table_indices):
            values = [
                self._display_pcpt_value(self.pcpt_raw_data.at[index, column])
                for column in columns
            ]
            table.insert("", "end", iid=str(position), values=values)

    def _begin_pcpt_cell_edit(self, event):
        """Place an entry over a double-clicked table cell."""
        if self.pcpt is None:
            return
        row_id = self.pcpt_data_table.identify_row(event.y)
        column_id = self.pcpt_data_table.identify_column(event.x)
        if not row_id or not column_id:
            return
        column_number = int(column_id[1:]) - 1
        if not 0 <= column_number < len(self.pcpt_input_columns):
            return
        bounds = self.pcpt_data_table.bbox(row_id, column_id)
        if not bounds:
            return
        if self.pcpt_data_editor is not None:
            self.pcpt_data_editor.destroy()
        editor = ttk.Entry(self.pcpt_data_table)
        editor.insert(0, self.pcpt_data_table.set(row_id, column_id))
        editor.select_range(0, "end")
        editor.place(x=bounds[0], y=bounds[1], width=bounds[2], height=bounds[3])
        editor.focus_set()
        self.pcpt_data_editor = editor
        editor.bind(
            "<Return>",
            lambda _event: self._commit_pcpt_cell_edit(row_id, column_number, editor),
        )
        editor.bind("<Escape>", lambda _event: self._cancel_pcpt_cell_edit(editor))
        editor.bind(
            "<FocusOut>",
            lambda _event: self._commit_pcpt_cell_edit(row_id, column_number, editor),
        )

    def _cancel_pcpt_cell_edit(self, editor):
        if editor.winfo_exists():
            editor.destroy()
        if self.pcpt_data_editor is editor:
            self.pcpt_data_editor = None

    def _commit_pcpt_cell_edit(self, row_id, column_number, editor):
        if self.pcpt_data_editor is not editor or not editor.winfo_exists():
            return
        text = editor.get().strip()
        index = self.pcpt_table_indices[int(row_id)]
        column = self.pcpt_input_columns[column_number]
        old_value = self.pcpt_raw_data.at[index, column]
        try:
            if isinstance(old_value, (int, float, np.integer, np.floating)):
                value = np.nan if text == "" else float(text)
            else:
                value = text
            self.pcpt_raw_data.at[index, column] = value
            maximum_depth = self._normalise_pcpt_data(self.pcpt)
            self.pcpt_data_table.set(row_id, column, self._display_pcpt_value(value))
            self.pcpt_dirty = True
            self.save_pcpt_button.configure(state="normal")
            self.pcpt_parameters = None
            self.transfer_button.configure(state="disabled")
            self._set_source_controls()
            self._plot_pcpt()
            self.pcpt_result.set(
                f"Edited {column}; {len(self.pcpt.data):,} rows, maximum depth {maximum_depth:.3f} m"
            )
            self.status.set("PCPT data updated and re-normalised. Recalculate the correlations.")
        except Exception as error:
            self.pcpt_raw_data.at[index, column] = old_value
            try:
                self._normalise_pcpt_data(self.pcpt)
            except Exception:
                pass
            messagebox.showerror("Invalid PCPT value", str(error))
        finally:
            self._cancel_pcpt_cell_edit(editor)

    def _clear_pcpt_plot(self, message="No PCPT data loaded."):
        """Remove stale PCPT graphs while a workbook is absent or reloading."""
        self.pcpt_figure.clear()
        placeholder = self.pcpt_figure.add_subplot(111)
        placeholder.set_axis_off()
        placeholder.text(
            0.5, 0.5, message,
            ha="center", va="center", transform=placeholder.transAxes,
            color="#666666", fontsize=12,
        )
        self.pcpt_canvas.draw_idle()

    def _plot_pcpt(self):
        data = self.pcpt.data
        fig = self.pcpt_figure
        fig.clear()
        raw_axes = [fig.add_subplot(2, 3, index) for index in range(1, 4)]
        norm_axes = [fig.add_subplot(2, 3, index) for index in range(4, 7)]
        raw_columns = [("qc [MPa]", "qc (MPa)"), ("fs [MPa]", "fs (MPa)"), ("u2 [MPa]", "u2 (MPa)")]
        norm_columns = [("Qt [-]", "Qt"), ("Fr [%]", "Fr (%)"), ("Bq [-]", "Bq")]
        for axis, (column, label) in zip(raw_axes, raw_columns):
            axis.plot(data[column], data["z [m]"], linewidth=0.8)
            axis.set_xlabel(label)
            axis.grid(True, alpha=0.25)
            axis.invert_yaxis()
        raw_axes[0].set_ylabel("Depth (m)")
        raw_axes[1].set_title("Raw PCPT")
        for axis, (column, label) in zip(norm_axes, norm_columns):
            axis.plot(data[column], data["z [m]"], linewidth=0.8)
            axis.set_xlabel(label)
            axis.grid(True, alpha=0.25)
            axis.invert_yaxis()
        norm_axes[0].set_ylabel("Depth (m)")
        norm_axes[1].set_title("Normalised PCPT")
        fig.tight_layout()
        self.pcpt_canvas.draw_idle()

    def calculate_pcpt_correlations(self):
        if self.pcpt is None:
            self.load_pcpt()
            if self.pcpt is None:
                return
        try:
            depth_from = self._float(self.depth_from_var, "Depth from")
            depth_to = self._float(self.depth_to_var, "Depth to")
            nk = self._float(self.nk_var, "Cone factor Nk")
            if depth_to <= depth_from:
                raise ValueError("Depth to must be greater than depth from.")
            if not 8 <= nk <= 30:
                raise ValueError("Nk must be between 8 and 30.")

            interval = self.pcpt.data.loc[
                self.pcpt.data["z [m]"].between(depth_from, depth_to)
            ].copy()
            if interval.empty:
                raise ValueError("No PCPT rows exist in the selected depth interval.")
            interval["PCPT phi [deg]"] = interval.apply(
                lambda row: frictionangle_sand_kulhawymayne(
                    qt=row["qt [MPa]"],
                    sigma_vo_eff=row["Vertical effective stress [kPa]"],
                )["Phi [deg]"], axis=1,
            )
            interval["PCPT Su [kPa]"] = interval.apply(
                lambda row: undrainedshearstrength_clay_radlunne(
                    qnet=row["qnet [MPa]"], Nk=nk,
                )["Su [kPa]"], axis=1,
            )
            interval["PCPT total unit weight [kN/m3]"] = interval.apply(
                lambda row: unitweight_mayne(
                    ft=row["ft [MPa]"],
                    sigma_vo_eff=row["Vertical effective stress [kPa]"],
                )["gamma [kN/m3]"], axis=1,
            )
            columns = [
                "PCPT phi [deg]", "PCPT Su [kPa]",
                "PCPT total unit weight [kN/m3]", "Vertical effective stress [kPa]",
            ]
            interval[columns] = interval[columns].replace([np.inf, -np.inf], np.nan)
            reducer = np.nanmedian if self.statistic_var.get() == "Median" else np.nanmean
            values = {column: float(reducer(interval[column])) for column in columns}
            su_rows = interval[["z [m]", "PCPT Su [kPa]"]].dropna()
            su_gradient = (
                float(np.polyfit(su_rows["z [m]"], su_rows["PCPT Su [kPa]"], 1)[0])
                if len(su_rows) >= 2 else 0.0
            )
            total_unit_weight = values["PCPT total unit weight [kN/m3]"]
            self.pcpt_parameters = {
                "depth_from": depth_from,
                "depth_to": depth_to,
                "nk": nk,
                "friction_angle": values["PCPT phi [deg]"],
                "undrained_shear_strength": values["PCPT Su [kPa]"],
                "su_increase": su_gradient,
                "total_unit_weight": total_unit_weight,
                "effective_unit_weight": max(total_unit_weight - WATER_UNIT_WEIGHT, 0.0),
                "effective_stress": values["Vertical effective stress [kPa]"],
            }
            if not all(np.isfinite(value) for value in self.pcpt_parameters.values()):
                raise ValueError("A correlation produced no valid value in the selected interval.")
            statistic = self.statistic_var.get()

            def column_statistics(column):
                valid = interval[column].dropna().astype(float)
                return {
                    "valid_count": int(valid.size),
                    "minimum": float(valid.min()) if not valid.empty else np.nan,
                    "maximum": float(valid.max()) if not valid.empty else np.nan,
                    "mean": float(valid.mean()) if not valid.empty else np.nan,
                    "median": float(valid.median()) if not valid.empty else np.nan,
                }

            regression_intercept = (
                float(np.polyfit(su_rows["z [m]"], su_rows["PCPT Su [kPa]"], 1)[1])
                if len(su_rows) >= 2 else np.nan
            )
            if len(su_rows) >= 2:
                predicted_su = su_gradient * su_rows["z [m]"] + regression_intercept
                residual_sum = float(np.sum((su_rows["PCPT Su [kPa]"] - predicted_su) ** 2))
                total_sum = float(
                    np.sum((su_rows["PCPT Su [kPa]"] - su_rows["PCPT Su [kPa]"].mean()) ** 2)
                )
                regression_r_squared = 1.0 - residual_sum / total_sum if total_sum > 0 else np.nan
            else:
                regression_r_squared = np.nan

            self.pcpt_parameters["derivation"] = {
                "row_count": int(len(interval)),
                "statistic": statistic,
                "statistics": {column: column_statistics(column) for column in columns},
                "intermediate_statistics": {
                    column: column_statistics(column)
                    for column in ["qt [MPa]", "qnet [MPa]", "ft [MPa]"]
                    if column in interval.columns
                },
                "su_regression": {
                    "sample_count": int(len(su_rows)),
                    "slope": su_gradient,
                    "intercept": regression_intercept,
                    "r_squared": regression_r_squared,
                },
                "mapping_unit_weight": self._float(
                    self.mapping_unit_weight_var, "Mapping unit weight"
                ),
                "water_level": self._float(self.water_level_var, "Water level"),
                "area_ratio": self._float(self.area_ratio_var, "Cone area ratio"),
                "water_unit_weight": WATER_UNIT_WEIGHT,
                "source_file": str(Path(self.pcpt_file.get()).expanduser().resolve()),
            }
            p = self.pcpt_parameters
            self._set_source_controls()
            self.transfer_button.configure(state="normal")
            self.pcpt_result.set(
                f"Interval {depth_from:.2f}–{depth_to:.2f} m ({self.statistic_var.get().lower()})\n"
                f"φ′ = {p['friction_angle']:.2f}°    |    su = {p['undrained_shear_strength']:.2f} kPa    |    "
                f"γ = {p['total_unit_weight']:.2f} kN/m³    |    σ′v = {p['effective_stress']:.2f} kPa"
            )
            self.status.set(
                "PCPT correlations calculated. Continue with Step 3 to transfer the values "
                "to the foundation form."
            )
        except Exception as error:
            messagebox.showerror("PCPT correlation error", str(error))
            self.status.set(f"PCPT correlation failed: {error}")

if __name__ == "__main__":
    app = GroundhogDesktopApp()
    app.mainloop()
