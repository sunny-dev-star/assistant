"""python -m nidari.bff --config-path /path/to/config.yaml"""

from ..cli import run_server

if __name__ == "__main__":
    run_server(
        "nidari.bff.main:app",
        default_port=8001,
        description="Nidari BFF API server",
    )
