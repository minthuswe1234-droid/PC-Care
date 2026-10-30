# PC Care v0.2.0

Free Windows desktop utility built with Python and PySide6.

## Current features
- Dashboard: CPU, RAM, and system drive usage (psutil)
- Read-only junk scan: scans the current user's temporary directory
- Background worker, cancel, sample file table, and aggregate counts

**Important:** A temp file is not necessarily junk or safe to delete. v0.2 never deletes or quarantines files. File sizes are snapshots and may change during scanning. Scans may be partial when cancelled or after the 200,000-file safety limit.

## Run (Windows PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

If `.venv` already exists, skip the first command. Re-run pip only when requirements change.

## Test

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Git workflow

Create an empty GitHub repository called `PC-Care` (do not initialize it with a README), then from this folder:

```powershell
git init
git add .
git commit -m "feat: PC Care v0.2 read-only junk scanner"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/PC-Care.git
git push -u origin main
git tag v0.2.0
git push origin v0.2.0
```

If you already committed and tagged v0.1.0, keep that history; just commit the changed files and create the v0.2.0 tag. Do not reinitialize or force-push.

## License

Choose and add an appropriate `LICENSE` file before public distribution. Check dependency license obligations, including PySide6/Qt.
