# activate_env.ps1 — Bail Reckoner environment pins (C1-a)
# Dot-source this before any Python/pip/model work:  . H:\Bail_Reckoner\06_src\activate_env.ps1
# Pins every tool cache inside H:\Bail_Reckoner\.cache\ per CLAUDE.md C1-a.
# If any tool ignores these pins, report it in PROGRESS.md — do not hide it.

$root = 'H:\Bail_Reckoner'

$env:PIP_CACHE_DIR          = "$root\.cache\pip"
$env:HF_HOME                = "$root\.cache\hf"
$env:TRANSFORMERS_CACHE     = "$root\.cache\hf\transformers"   # legacy alias; HF_HOME is the modern pin
$env:TORCH_HOME             = "$root\.cache\torch"
$env:UV_CACHE_DIR           = "$root\.cache\uv"
$env:UV_PYTHON_INSTALL_DIR  = "$root\.cache\uv\python"

# Activate the project venv (CPython 3.12.13, standalone build pinned under .cache\uv\python)
& "$root\06_src\.venv\Scripts\Activate.ps1"
