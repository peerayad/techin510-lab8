"""Load config from .env (local) or st.secrets when secrets.toml is present."""

import os
from pathlib import Path
from typing import Optional

PROJECT_DIR = Path(__file__).parent
ENV_PATH = PROJECT_DIR / ".env"


def _secrets_toml_exists() -> bool:
    """True if Streamlit has a secrets file (local or Cloud-injected)."""
    return any(
        p.is_file()
        for p in (
            Path.home() / ".streamlit" / "secrets.toml",
            PROJECT_DIR / ".streamlit" / "secrets.toml",
        )
    )


def get_config_value(name: str) -> Optional[str]:
    """Read a config value from .env, or from st.secrets only if secrets.toml exists."""
    from dotenv import load_dotenv

    if ENV_PATH.exists():
        load_dotenv(ENV_PATH, override=True)
    else:
        load_dotenv()
    value = os.getenv(name)
    if value:
        return value

    if not _secrets_toml_exists():
        return None

    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        if get_script_run_ctx() is not None:
            import streamlit as st

            if name in st.secrets:
                return st.secrets[name]
    except Exception:
        pass
    return None
