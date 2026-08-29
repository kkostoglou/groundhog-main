# Groundhog Desktop — PCPT and Shallow-Foundation Analysis

## About this project

This repository is a modification and desktop extension of the open-source [Groundhog geotechnical Python package](https://github.com/snakesonabrain/groundhog). It retains the Groundhog calculation library and adds a user-friendly graphical interface for engineers who want to perform PCPT processing and shallow-foundation capacity calculations without writing Python code.

The desktop application provides:

- guided manual and PCPT-assisted calculation workflows;
- editable Excel PCPT data import, inspection, correction, and export;
- PCPT normalization and derivation of representative soil parameters;
- drained and undrained shallow-foundation analysis;
- rectangular and circular geometry, eccentric loading, and skirt options;
- unfactored and factored vertical-horizontal capacity envelopes;
- detailed, traceable analytical calculations; and
- export of calculation reports and graphs to PDF.

The added interface is implemented in [`GroundhogDesktopGUI.py`](GroundhogDesktopGUI.py). The original Groundhog library remains under [`groundhog/`](groundhog/) and is credited to its original author and contributors under the GNU GPLv3 license.

> **Engineering notice:** This software is a calculation aid. Users must independently verify soil parameters, correlations, drainage assumptions, resistance factors, load combinations, results, and compliance with the governing design requirements.

## New user? Start here

You do not need to understand Python or GitHub to use the Windows application. First decide what you want to do:

### I only want to use the program

1. On this GitHub repository page, find **Releases** in the right-hand sidebar. On a narrow screen, you may need to scroll down.
2. Click the newest release, such as **Groundhog Desktop v1.0.0**.
3. At the bottom of the release, expand **Assets** if it is collapsed.
4. Click `GroundhogDesktop-Windows.zip` to download it.
5. Open your Windows **Downloads** folder.
6. Right-click the downloaded ZIP and select **Extract All…**. Do not run the program from inside the ZIP.
7. Open the extracted `GroundhogDesktop` folder.
8. Double-click `GroundhogDesktop.exe`.
9. If Windows SmartScreen appears, confirm that the file came from this repository, select **More info**, and then select **Run anyway** if you trust it.

When the application opens:

1. Choose **Start manual analysis** if you already know the foundation and soil parameters.
2. Choose **Start PCPT-assisted analysis** if you want to load and process an Excel PCPT file.
3. Work through the numbered steps shown on the left side of the application.
4. Read the status bar at the bottom if a field or calculation needs attention.
5. After calculating, review **Analytical Calculation Results** and use **Save PDF** to export the report.

For a first trial, choose the PCPT-assisted workflow and select **Use and load bundled example**. This lets you explore the application without preparing your own workbook.

> **Important:** Do not use GitHub's green **Code → Download ZIP** button when you only want to run the program. That button downloads the source code. Download `GroundhogDesktop-Windows.zip` from **Releases → Assets** instead.

### I want to inspect or modify the source code

1. Select the green **Code** button near the top of the repository.
2. Select **Download ZIP**, or copy the displayed repository URL and clone it with Git.
3. Extract the source ZIP if you downloaded it.
4. Open `USER_GUIDE.md` for full operating instructions.
5. Follow **Run from source** below to create the Python environment and start the application.

The files shown on the main GitHub page are the editable source. The ready-to-run Windows executable is distributed separately through **Releases**.

## Quick start for Windows users

### Run the ready-made application

1. Open this repository's [Releases](../../releases) page.
2. Open the latest release.
3. Download `GroundhogDesktop-Windows.zip` from **Assets**.
4. Extract the complete ZIP file to a local folder.
5. Double-click `GroundhogDesktop.exe`.

Python is not required when using the packaged executable. Windows may show a SmartScreen warning because the executable is not digitally signed; verify that it came from this repository and compare its checksum with the included `SHA256SUMS.txt`.

### Main operating workflow

1. Choose **Manual foundation analysis** or **PCPT-assisted foundation analysis**.
2. For PCPT analysis, load an Excel file containing `z [m]`, `qc [MPa]`, `fs [MPa]`, and `u2 [MPa]` columns.
3. Review or edit the imported data and choose the calculation depth interval.
4. Calculate and transfer the PCPT-derived parameters to the foundation form.
5. Enter the foundation geometry, drainage condition, and resistance factors.
6. Calculate the bearing capacity and review the V-H envelope.
7. Review the analytical calculations and export the PDF report.

See the complete [User's Guide](USER_GUIDE.md) for field definitions, detailed procedures, result interpretation, troubleshooting, and engineering limitations.

## Run from source

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-desktop.txt
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
.\.venv\Scripts\python.exe GroundhogDesktopGUI.py
```

Alternatively, after installing the dependencies, double-click `run_groundhog.bat`. See [Building and Publishing Groundhog Desktop](RELEASE_GUIDE.md) for executable build instructions.

## Original Groundhog package

[![PyPI version](https://badge.fury.io/py/groundhog.svg)](https://badge.fury.io/py/groundhog)

![groundhog banner](https://github.com/snakesonabrain/groundhog/blob/main/groundhog_banner_wide.png?raw=true)

This Python package contains useful functionality for supporting automated geotechnical calculations.

Functionality for onshore and offshore geotechnical problems is included. This package is under constant development so any request for additional functionality can always be submitted to the package author.

groundhog bundles a large amount of knowledge and provides it to end users through extensively documented functions. The aim of the package is as follows:

   - Improve correctness through unit-tested functions with parameter validation
   - Raise awareness on underlying test data and theories supporting engineering correlations and design formulae
   - Promoting development of open-source engineering software by the worldwide community of engineers

groundhog is developed using a set of 10 Golden rules which are reflected in the groundhog function architecture and should also be followed by any contributors to the project.

For more information, consult the [documentation](https://groundhog.readthedocs.io/en/main/) or get started using the [tutorial notebooks](https://mybinder.org/v2/gh/snakesonabrain/groundhog/main). [![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/snakesonabrain/groundhog/main)

Installation requirements
-------------------------

groundhog is written for Python 3.7+. Downloading Anaconda3 is recommended for users not familiar with Python development. Plotting functionality included in the package is built on plotly. The plotly package also needs to be installed and is not included in the default Anaconda installation.

Installing groundhog is easily done with pip:`

```
pip install groundhog
```


Support groundhog
-------------------

You can support the development of groundhog by buying me a coffee

<a href="https://www.buymeacoffee.com/groundhog"><img src="https://img.buymeacoffee.com/button-api/?text=Buy me a coffee&emoji=&slug=groundhog&button_colour=FFDD00&font_colour=000000&font_family=Cookie&outline_colour=000000&coffee_colour=ffffff"></a>


License and copyright
-----------------------

groundhog. A general-purpose Python library for geotechnical engineering.
    Copyright (C) 2020, 2021, 2022, 2023, 2024, 2025  Bruno Stuyts

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.


Disclaimer
-------------

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
