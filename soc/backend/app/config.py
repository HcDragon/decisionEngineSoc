"""
Application Configuration and Settings Module.
Loads environment variables, config paths, and operational defaults.
"""
from pathlib import Path
from typing import List, Literal, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def find_project_root() -> Path:
    """Find the root directory of the project."""
    current = Path(__file__).resolve().parent
    for parent in [current] + list(current.parents):
        if (parent / "ids_project").exists() or (parent / "soc" / "config").exists() or (parent / ".git").exists():
            return parent
    return Path.cwd()


PROJECT_ROOT = find_project_root()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Core Application
    ENVIRONMENT: str = Field(default="development")
    DEBUG: bool = Field(default=False)
    LOG_LEVEL: str = Field(default="INFO")
    API_HOST: str = Field(default="0.0.0.0")
    API_PORT: int = Field(default=8000)
    API_TOKEN: str = Field(default="soc-secret-token-change-in-production")

    # Automation Mode Kill Switch: "off" | "recommend_only" | "auto"
    AUTOMATION_MODE: Literal["off", "recommend_only", "auto"] = Field(default="recommend_only")

    # Database
    DATABASE_URL: str = Field(default="sqlite:///./soc.db")

    # Paths
    CONFIG_DIR: str = Field(default="soc/config")
    MODEL_DIR: str = Field(default="ids_project")

    # Capture interface the live monitor binds to. Empty/"any" captures all
    # interfaces; set to e.g. "veth-def" for the namespace test lab.
    SOC_CAPTURE_IFACE: str = Field(default="any")

    # Safety Guardrails
    SOC_EXECUTOR: Literal["dry_run", "simulated", "lab"] = Field(default="dry_run")
    SOC_LAB_MODE: bool = Field(default=False)
    LAB_ALLOWED_CIDRS: str = Field(default="10.10.0.0/16,10.66.0.0/24")
    MAX_AUTO_ACTIONS_PER_MIN: int = Field(default=10)
    MAX_ACTIVE_BLOCKS: int = Field(default=50)
    DEFAULT_BLOCK_TTL_S: int = Field(default=900)

    # Explainability Settings
    SHAP_RISK_THRESHOLD: float = Field(default=60.0)
    SHAP_BACKGROUND_SAMPLE_SIZE: int = Field(default=100)

    @property
    def config_path(self) -> Path:
        p = Path(self.CONFIG_DIR)
        return p if p.is_absolute() else (PROJECT_ROOT / p)

    @property
    def model_path(self) -> Path:
        p = Path(self.MODEL_DIR)
        return p if p.is_absolute() else (PROJECT_ROOT / p)

    @property
    def assets_file(self) -> Path:
        return self.config_path / "assets.yaml"

    @property
    def policies_file(self) -> Path:
        return self.config_path / "policies.yaml"

    @property
    def allowlist_file(self) -> Path:
        return self.config_path / "allowlist.yaml"

    @property
    def playbooks_dir(self) -> Path:
        return self.config_path / "playbooks"

    @property
    def blocklist_file(self) -> Path:
        return self.config_path / "intel" / "blocklist.csv"

    @property
    def lab_cidrs(self) -> List[str]:
        return [cidr.strip() for cidr in self.LAB_ALLOWED_CIDRS.split(",") if cidr.strip()]


# Global singleton instance
settings = Settings()
