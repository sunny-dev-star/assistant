"""python -m nidari --config-path /path/to/config.yaml"""

from .cli import run_server

if __name__ == "__main__":
    run_server("nidari.main:app", default_port=8000, description="Nidari API server")
