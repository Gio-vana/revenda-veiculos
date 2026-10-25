from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./revenda.db"

    jwks_url: str = "http://identidade-api:8000/.well-known/jwks.json"
    jwt_issuer: str = "revenda-identidade"
    jwt_audience: str = "revenda-api"

    webhook_secret: str | None = None
