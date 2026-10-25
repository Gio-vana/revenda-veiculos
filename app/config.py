from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuração lida de variáveis de ambiente (ou do arquivo .env)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./revenda.db"

    # Contrato com o serviço de identidade (outro repositório)
    jwks_url: str = "http://identidade-api:8000/.well-known/jwks.json"
    jwt_issuer: str = "revenda-identidade"
    jwt_audience: str = "revenda-api"

    # Segredo compartilhado com o gateway de pagamento (simulado)
    webhook_secret: str | None = None
