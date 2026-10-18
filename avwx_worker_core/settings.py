"""Settings every worker shares.

A worker repo subclasses `CoreSettings` with its own fields and instantiates it once. The
core modules take the settings object as an argument rather than reading a global, so two
repos with different settings classes can both use them.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class CoreSettings(BaseSettings):
    """Environment-sourced settings common to every worker."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    mongo_uri: str = "mongodb://localhost:27017"
    # Appends "-tests" to every database name, matching the API's MongoStore behavior.
    testing: bool = False

    sentry_dsn: str | None = None
    environment: str = "development"

    log_level: str = "INFO"
    # Human-readable logs instead of JSON. Useful when running a worker by hand.
    log_plain: bool = False

    def database_name(self, base: str) -> str:
        """A database name with the test suffix applied when testing."""
        return f"{base}-tests" if self.testing else base
