"""Create a portable local Python environment without touching system Python."""
import pathlib, subprocess, sys, venv
ROOT = pathlib.Path(__file__).resolve().parents[1]
if sys.version_info[:2] != (3, 12):
    raise SystemExit('Please run setup with Python 3.12 (Windows: py -3.12 local/setup.py).')
env = ROOT / '.venv'
if not env.exists():
    venv.EnvBuilder(with_pip=True).create(env)
python = env / ('Scripts/python.exe' if sys.platform == 'win32' else 'bin/python')
subprocess.run([str(python), '-m', 'pip', 'install', '-r', str(ROOT/'local/requirements-lock.txt')], check=True)
subprocess.run([str(python), str(ROOT/'local/run.py'), 'doctor'], check=True)
