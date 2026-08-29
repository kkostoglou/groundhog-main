# Building and Publishing Groundhog Desktop

This repository contains both the editable source and a reproducible Windows executable build.

## Files intended for GitHub

Commit these files with the application source:

- `GroundhogDesktopGUI.py`
- `groundhog/`
- `notebooks/Data/cpt.xlsx`
- `run_groundhog.bat`
- `requirements-desktop.txt`
- `requirements-build.txt`
- `build_windows_exe.ps1`
- `USER_GUIDE.md`
- `.github/workflows/windows-executable.yml`

Generated `build/`, `dist/`, `.build-venv/`, and `release/` directories are intentionally ignored by Git. They are reproducible outputs and should not be committed to the source repository.

## Run directly from source

After following the installation section in `USER_GUIDE.md`, double-click `run_groundhog.bat` or run:

```powershell
.\.venv\Scripts\python.exe GroundhogDesktopGUI.py
```

## Build locally on Windows

From PowerShell in the repository root:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\build_windows_exe.ps1
```

The script creates an isolated `.build-venv`, installs build dependencies, and produces:

- `release/GroundhogDesktop/GroundhogDesktop.exe`
- `release/GroundhogDesktop/` with the user guide, license, source directory, and executable checksum
- `release/GroundhogDesktop-Windows.zip`, ready for distribution

The executable is a one-file Windows application. End users can extract the ZIP and double-click `GroundhogDesktop.exe`; Python is not required on their computer.

## Build with GitHub Actions

1. Push the source repository to GitHub.
2. Open the repository's **Actions** tab.
3. Select **Build Windows executable**.
4. Choose **Run workflow**.
5. When the job finishes, download the `GroundhogDesktop-Windows` artifact.

The workflow also runs automatically after relevant files are pushed to the `main` branch.

## Publish a GitHub release

1. Open **Releases** in the GitHub repository.
2. Select **Draft a new release**.
3. Create a version tag, for example `v1.0.0`.
4. Add release notes describing calculation or interface changes.
5. Upload `GroundhogDesktop-Windows.zip` from the local build or downloaded Actions artifact.
6. Publish the release.

Distribute the ZIP through GitHub Releases instead of committing the binary to Git history. This keeps clones small and ensures each binary is tied to a tagged source revision.

## Verify a downloaded executable

Compare its SHA-256 checksum with `SHA256SUMS.txt`:

```powershell
Get-FileHash .\GroundhogDesktop.exe -Algorithm SHA256
```

Windows may display a SmartScreen warning for an unsigned executable. Code signing with a trusted certificate is required to establish publisher identity and reduce these warnings. A checksum confirms file integrity but is not a substitute for code signing.
