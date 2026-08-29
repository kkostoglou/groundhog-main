# Groundhog Desktop User's Guide

## PCPT Processing and Shallow-Foundation Capacity Analysis

This guide explains how to install, start, and use the native Groundhog desktop application in `GroundhogDesktopGUI.py`. The application supports:

- manual drained or undrained shallow-foundation analysis;
- PCPT-assisted derivation of soil parameters from Excel data;
- rectangular and circular foundations, including eccentricity and skirts;
- unfactored and factored vertical-horizontal (V-H) capacity envelopes;
- detailed analytical calculation reports; and
- export of calculations and graphs to PDF.

The interface is a local Tkinter desktop application. It does not start a web server and does not upload project data.

> **Engineering notice:** The software is a calculation aid, not a substitute for engineering judgement. Verify input data, correlations, drainage assumptions, resistance factors, load combinations, governing standards, and all results before design use. The report documents the implemented calculation basis; it does not certify code compliance.

## 1. System requirements

The application is primarily intended for a Windows desktop, although Tkinter and the Python package are cross-platform.

You need:

- Python 3.7 or newer;
- Tkinter (normally included with the Windows Python installer);
- the packages listed in `requirements.txt` and `optional-requirements.txt`;
- a graphical desktop session; and
- an installed PDF viewer if you want the application to open exported reports automatically.

The principal desktop dependencies are NumPy, pandas, SciPy, Matplotlib, Pillow, `openpyxl`, and `xlrd`.

## 2. Installation

Open PowerShell or a command prompt in the directory containing this guide.

### 2.1 Create a virtual environment

```powershell
py -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell script execution is disabled, either use Command Prompt:

```bat
.venv\Scripts\activate.bat
```

or run the environment's Python executable directly in the following commands.

### 2.2 Install dependencies and Groundhog

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r optional-requirements.txt
python -m pip install -e .
```

The editable installation (`-e`) makes the local `groundhog` package available while retaining this source directory as the working copy.

## 3. Starting the application

From the package directory, run:

```powershell
.\.venv\Scripts\python.exe GroundhogDesktopGUI.py
```

The start page offers two workflows:

1. **Start manual analysis** — enter soil parameters directly.
2. **Start PCPT-assisted analysis** — process an Excel sounding, derive parameters, and transfer them to the foundation form.

The status bar at the bottom of the window reports the current action, completion state, or error. Use **Back to workflow selection** whenever you need to return to the start page.

## 4. Units and notation

Use the displayed units throughout the interface. The main units are:

| Quantity | Unit |
|---|---:|
| Length, width, diameter, depth, eccentricity | m |
| Unit weight | kN/m³ |
| Soil stress and undrained shear strength | kPa |
| Cone resistance, sleeve friction, pore pressure | MPa |
| Friction and interface angles | degrees |
| Vertical and horizontal capacity | kN |
| Resistance factors | dimensionless |

Common symbols include:

- `L`, `B`, `D`: foundation length, width/diameter, and depth;
- `eL`, `eB`: load eccentricities in the length and width directions;
- `L′`, `B′`, `A′`: effective dimensions and effective area;
- `γ`, `γ′`: total and effective unit weight;
- `φ′`, `δ′`: effective soil friction and foundation-interface friction angles;
- `su`: undrained shear strength;
- `κ`: increase in undrained strength with depth;
- `qu`: ultimate bearing pressure; and
- `Vult`, `Hmax`: ultimate vertical capacity and maximum horizontal envelope resistance.

Do not enter unit text or thousands separators in an input box. Enter only a valid number, such as `18.5`.

## 5. Manual foundation analysis

Select **Start manual analysis**. The application opens the **Shallow Foundation Bearing Capacity** tab.

### 5.1 Step 1 — Foundation geometry

Select one of the following:

- **Rectangle:** enter length `L` and width `B`.
- **Circular:** enter diameter `B`. Length and rectangular width are disabled.

Then enter:

- **Foundation depth, D:** embedment depth below the reference surface.
- **Width eccentricity, eB:** eccentricity acting across the width. For a circle, this is the single radial eccentricity used by the model.
- **Length eccentricity, eL:** eccentricity acting along a rectangular foundation. This is disabled for a circle.
- **Skirted foundation:** select when the foundation includes skirts and the skirted formulation is required.

Eccentricity reduces the effective dimensions. Check that the resulting effective width and length remain physically meaningful. Very large eccentricities may cause the Groundhog model to reject the geometry.

### 5.2 Step 2 — Select the drainage condition

Choose **Drained** when effective-stress parameters and frictional resistance govern. Choose **Undrained** when total-stress clay behavior and undrained shear strength govern.

#### Drained inputs

- **Effective unit weight, γ′:** effective/submerged unit weight used in the unit-weight bearing term.
- **Friction angle, φ′:** effective soil friction angle.
- **Interface friction angle, δ′:** friction angle at the foundation-soil interface. It must be from zero through `φ′`, inclusive.
- **Effective stress at base, σ′v0:** initial vertical effective stress at foundation-base level.

#### Undrained inputs

- **Total unit weight, γ:** total soil unit weight.
- **Undrained strength, su:** shear strength at foundation-base level.
- **su increase, κ:** linear strength increase with depth in kPa/m. Enter `0` for constant strength.

Keep **Parameter source** set to **Manual input** when values are entered directly.

### 5.3 Step 3 — Resistance factors

Enter:

- **Bearing factor:** divisor applied to bearing resistance.
- **Sliding factor:** divisor applied to sliding resistance.

Both values must be at least `1.0`. The appropriate values depend on the governing standard and project design basis; the application's defaults must not be assumed to be suitable for every project.

### 5.4 Step 4 — Calculate

Select **Calculate bearing capacity**. If the entries are valid, the application:

1. calculates bearing and sliding components;
2. constructs unfactored and factored V-H capacity envelopes;
3. displays a summary and envelope graph;
4. generates the detailed analytical report; and
5. opens **Analytical Calculation Results**.

If a calculation fails, read the dialog and the bottom status bar, correct the highlighted or relevant input, and calculate again.

## 6. PCPT-assisted analysis

Select **Start PCPT-assisted analysis**. The application opens **PCPT Processing**.

### 6.1 Prepare the Excel workbook

The first worksheet must contain a header row with these exact column names:

| Required column | Meaning | Required unit |
|---|---|---:|
| `z [m]` | Depth below the reference level | m |
| `qc [MPa]` | Measured cone resistance | MPa |
| `fs [MPa]` | Sleeve friction | MPa |
| `u2 [MPa]` | Pore pressure at the cone shoulder | MPa |

An optional `Push` column can identify sounding pushes. If it is absent, the application assigns every row to push 1. Other columns are retained and shown in the editable table.

Important preparation rules:

- values must already use the units shown above;
- headers must match exactly, including capitalization, spaces, and bracketed units;
- depth and measurement cells should be numeric;
- avoid merged cells, title rows above the headers, and repeated header rows inside the data;
- keep depths ordered and verify the depth reference; and
- preserve the original workbook outside the application.

The bundled example is `notebooks/Data/cpt.xlsx` and can be used to learn the workflow or confirm installation.

### 6.2 Step 1 — Select and normalize PCPT data

Choose one source:

- **Choose Excel file:** select an `.xlsx` or `.xls` workbook. Selection starts loading automatically.
- **Use and load bundled example:** loads the supplied example.

Review the processing inputs before selecting **Load and normalise PCPT**:

- **Cone area ratio, a:** net-area correction for corrected cone resistance `qt`.
- **Mapping unit weight, γmap:** total unit weight used to create the stress profile during normalization.
- **Water level, zw:** depth of the water level measured in the same coordinate system as `z`.

Loading maps cone and soil properties, calculates total and effective vertical stress, and normalizes the PCPT measurements. A progress indicator appears while processing.

After loading:

- the summary shows the workbook name, row count, and maximum depth;
- the imported data appears in a scrollable table; and
- raw and normalized PCPT plots appear below the table.

### 6.3 Inspect and edit imported data

Double-click a table cell to edit it. Confirm the new value to re-normalize the dataset. After any edit:

- existing correlation results are invalidated;
- the correlations must be calculated again; and
- **Save edited Excel as…** becomes available.

Use **Save edited Excel as…** to preserve edits in a new `.xlsx` file. The application deliberately refuses to overwrite the source workbook. Choose a different filename.

### 6.4 Step 2 — Calculate foundation correlations

Enter:

- **Depth from, zfrom:** upper boundary of the selected interval.
- **Depth to, zto:** lower boundary of the interval; it must be greater than `zfrom`.
- **Cone factor, Nk:** factor for the undrained-strength correlation; accepted range is 8 through 30.
- **Statistic:** `Median` or `Mean`, used to adopt representative interval values.

Select **Calculate PCPT correlations**. The interval must contain at least one PCPT row and must yield finite correlation results.

The application calculates:

- corrected cone resistance `qt`;
- net cone resistance `qnet`;
- effective vertical stress;
- effective friction angle using Kulhawy and Mayne (1990);
- undrained shear strength using Rad and Lunne (1988);
- total unit weight using Mayne, Peuchen, and Bouwmeester (2010); and
- a linear `su`-depth regression when at least two valid samples are available.

For transfer to the foundation form:

- total unit weight is the selected interval statistic;
- effective unit weight is calculated as `max(total unit weight − 10.25, 0)` kN/m³;
- interface angle is calculated as `max(φ′ − 5°, 0)`; and
- a negative `su` regression slope is transferred as zero for the foundation strength-increase input, although the original regression remains documented in the analytical report.

The fixed value `10.25 kN/m³` represents seawater in this application. If another water unit weight is required, review and adjust the derived effective unit weight manually with appropriate engineering justification.

### 6.5 Step 3 — Transfer values

Select **Transfer to foundation form**. The application opens the foundation tab, changes **Parameter source** to **PCPT correlations**, and fills both the drained and undrained soil fields with the derived values.

The **PCPT processing reference** records the source workbook, area ratio, mapping unit weight, water level, selected interval, `Nk`, and adopted statistic.

Next:

1. select the required drainage condition;
2. enter and verify foundation geometry;
3. review every transferred soil value;
4. enter the project resistance factors; and
5. select **Calculate bearing capacity**.

If you return to the PCPT tab and change the source data or processing settings, recalculate and transfer the parameters again before rerunning the foundation analysis.

## 7. Reading the results

### 7.1 Summary values

The result summary reports:

- ultimate bearing pressure `qu`;
- factored bearing pressure `qu,f`;
- ultimate vertical capacity `Vult`; and
- factored vertical capacity `Vult,f`.

Calculated resistances are not utilizations. The application does not accept applied design loads, so it does not produce utilization ratios or pass/fail decisions.

### 7.2 V-H capacity envelope

The graph plots horizontal resistance `H` against vertical resistance `V` and shows:

- the unfactored bearing envelope;
- the factored bearing envelope; and
- applicable sliding limits or cutoffs.

Use the Matplotlib toolbar to zoom, pan, return to the original view, configure the plot, or save an image. A load point inside an applicable factored envelope has available calculated resistance according to the implemented model; a load outside exceeds it. For drained loading, also check the relevant load-dependent sliding limit.

### 7.3 Analytical calculation report

The left side of **Analytical Calculation Results** contains the detailed report, including:

1. input summary and analysis basis;
2. soil inputs and, when used, PCPT derivation statistics;
3. resistance factors;
4. symbols and units;
5. principal results and derivations;
6. bearing-capacity components;
7. sliding-capacity components;
8. formula sources and standards;
9. design notes; and
10. calculation-results summary.

Scroll through the complete report and check that its recorded inputs match the intended design case. Recalculate after changing any foundation or soil entry; an old report does not update until **Calculate bearing capacity** is selected again.

## 8. Exporting the analytical report

After a successful calculation, select **Save PDF** on the results tab.

1. Choose a destination and filename.
2. The application creates paginated A4 calculation-text pages.
3. It appends the capacity-envelope graph.
4. For a PCPT-assisted calculation, it also appends the PCPT plots.
5. Choose whether to open the PDF for preview.

The default filename is `Groundhog_Analytical_Calculation_Report.pdf`. If automatic preview is unavailable, the PDF remains saved and can be opened manually.

Before issuing a report, verify legibility, page completeness, source-file reference, calculation inputs, units, standards, and revision status.

## 9. Input checks and common messages

| Message or symptom | Likely cause | Action |
|---|---|---|
| “Please enter a numeric value…” | Blank or nonnumeric input | Enter only a number using a decimal point. |
| “Resistance factors must be at least 1.0” | Bearing or sliding factor is below 1 | Enter project-approved factors of 1 or greater. |
| “Interface friction angle must be between 0 and the soil friction angle” | `δ′ < 0` or `δ′ > φ′` | Correct the interface angle. |
| “PCPT file not found” | Workbook path is invalid or file was moved | Select the file again. |
| “Error during reading of PCPT data” | Workbook format, header, or cell data is unsuitable | Check the required columns and numeric units. |
| “Depth to must be greater than depth from” | Invalid interval order | Increase `zto` or reduce `zfrom`. |
| “Nk must be between 8 and 30” | Cone factor is outside the accepted range | Enter a justified value from 8 through 30. |
| “No PCPT rows exist in the selected depth interval” | Interval is outside data coverage or contains no rows | Review the table/plots and choose a populated interval. |
| “A correlation produced no valid value…” | Required normalized inputs are missing or invalid | Inspect `qc`, `fs`, `u2`, stress data, and the selected interval. |
| PCPT transfer button is disabled | Correlations have not completed or edits invalidated them | Calculate the PCPT correlations again. |
| Save PDF warns that no results exist | No successful foundation calculation has run | Complete the calculation first. |

## 10. Recommended quality-control workflow

For each design case:

1. Preserve the original source workbook.
2. Confirm units and depth datum before import.
3. Plot and visually inspect the PCPT traces.
4. Review anomalous or missing rows; document any edits.
5. Select a defensible soil interval and correlation factors.
6. Compare mean, median, minimum, and maximum values in the analytical report.
7. Check transferred values against independent interpretation or laboratory data.
8. Verify geometry, eccentricity, drainage condition, skirts, and base stress.
9. Confirm resistance factors against the governing design basis.
10. Independently check critical capacities and limiting cases.
11. Save the edited data and PDF with traceable revision names.
12. Record the application version/source revision used for the calculation.

## 11. Calculation basis and limitations

The desktop application calls Groundhog shallow-foundation functions based on the API RP 2GEO/ISO 19901-4 formulation documented in the generated report. The report also notes the current ISO edition and the limits of claiming compliance.

Key limitations include:

- empirical PCPT correlations may not suit every soil type or site;
- one mapped soil unit weight and one water level are used during PCPT normalization;
- transferred effective unit weight uses a fixed seawater unit weight of `10.25 kN/m³`;
- no applied design loads or load combinations are entered;
- no utilization or pass/fail result is produced;
- drained sliding resistance depends on vertical load and must be checked at the relevant design load; and
- standards, national annexes, project requirements, and software implementations may change.

Always retain the input workbook, calculation PDF, independent checks, and engineering approval together as the calculation record.

## 12. Package resources

- Desktop application: `GroundhogDesktopGUI.py`
- Bundled PCPT example: `notebooks/Data/cpt.xlsx`
- Package overview: `README.md`
- Python dependencies: `requirements.txt`
- Optional dependencies: `optional-requirements.txt`
- Automated library tests: `tests/`
- Groundhog source package: `groundhog/`
- License: `LICENSE`

For the broader Groundhog Python API, examples, and function-level theory, consult the notebooks and documentation referenced in `README.md`.
