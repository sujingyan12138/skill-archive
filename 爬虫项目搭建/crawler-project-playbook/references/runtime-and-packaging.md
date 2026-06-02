# Runtime And Packaging

## Runtime Path Rules

When a crawler may be packaged, decide runtime paths early.

Use a stable application directory for:

- `config.json`
- output folders
- logs
- resume manifests

For Python source, `os.path.dirname(os.path.abspath(__file__))` is often enough.

For PyInstaller EXE:

```python
APP_DIR = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
```

This prevents config and outputs from drifting into unexpected working directories.

## Packaging Checklist

Create these files if the project is meant to be redistributed:

- `requirements-build.txt`
- build script such as `build_exe.ps1`
- PyInstaller `.spec`

Recommended flow:

1. Make Python execution stable
2. Add build dependencies
3. Build once
4. Run the EXE for real
5. Fix missing modules, paths, or assets
6. Rebuild and retest

## Why Commit The `.spec`

Commit the `.spec` when it contains project-specific build knowledge such as:

- hidden imports
- added data files
- explicit executable naming
- excluded modules

Do not treat it as disposable if it encodes hard-won fixes.

## GitHub Release Guidance

For Windows-first crawler tools:

- keep source in Git
- keep binaries out of regular commit history
- upload EXE or ZIP artifacts to GitHub Releases

This keeps the repository clean while still giving end users a direct download.

## Branch Flow

Recommended small-project flow:

1. Work on a feature branch
2. Commit packaging/runtime fixes there
3. Fast-forward or merge into `master` or the stable branch
4. Push both branches if that is your team habit
5. Switch back to the feature branch for continued work

## Proxy Guidance

If `git push`, `pip install`, or other networked CLI actions fail, try local proxy environment variables first:

```powershell
$env:HTTP_PROXY="http://127.0.0.1:10808"
$env:HTTPS_PROXY="http://127.0.0.1:10808"
```

If a tool requires SOCKS:

```powershell
$env:ALL_PROXY="socks5://127.0.0.1:10808"
```
