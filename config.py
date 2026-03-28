"""
Configuration management for the Carbon Market Intelligence Agent.
Loads settings from environment variables / .env file.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if present
load_dotenv()


class Settings:
    """Central settings object loaded from environment."""

    # Anthropic
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    MODEL_NAME: str = os.getenv("MODEL_NAME", "claude-opus-4-6")

    # Tavily web search (optional)
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")

    # API server
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))

    # Output directory for generated Excel / Word files
    OUTPUT_DIR: Path = Path(os.getenv("OUTPUT_DIR", "./outputs"))

    def validate(self) -> None:
        """Raise if required settings are missing."""
        if not self.ANTHROPIC_API_KEY:
            raise ValueError(
                "ANTHROPIC_API_KEY is required. "
                "Set it in your environment or in a .env file."
            )

    def ensure_output_dir(self) -> None:
        """Create output directory if it does not exist."""
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


settings = Settings()
