import os
import hvac
from pydantic_settings import BaseSettings, SettingsConfigDict
import logging

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str
    
    GOOGLE_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash-lite"
    EMBEDDING_MODEL: str = "models/gemini-embedding-001"
    LOG_LEVEL: str = "INFO"
    ASILA_MASTER_KEY: str = ""
    ASILA_SETUP_TOKEN: str = ""
    ASILA_MULTI_TENANCY_ENABLED: bool = False
    OIDC_ISSUER: str = ""
    OIDC_AUDIENCE: str = ""
    OIDC_JWKS_URL: str = ""
    AI_PROVIDER: str = "ollama"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_GENERATION_MODEL: str = "llama3.2"
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"
    OPENAI_BASE_URL: str = ""
    OPENAI_API_KEY: str = ""
    OPENAI_GENERATION_MODEL: str = ""
    OPENAI_EMBEDDING_MODEL: str = ""
    ALLOWED_ORIGINS: str = ""
    ENVIRONMENT: str = "development"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

def load_settings() -> Settings:
    vault_url = os.environ.get("VAULT_URL")
    vault_token = os.environ.get("VAULT_TOKEN")
    vault_mount = os.environ.get("VAULT_MOUNT_POINT", "secret")
    vault_path = os.environ.get("VAULT_PATH", "asila/config")
    # Vault initialization still requires raw os.environ since Settings isn't loaded yet
    env = os.environ.get("ENVIRONMENT", "development")

    if vault_url and vault_token:
        try:
            client = hvac.Client(url=vault_url, token=vault_token)
            if not client.is_authenticated():
                raise Exception("Vault authentication failed")
                
            read_response = client.secrets.kv.v2.read_secret_version(mount_point=vault_mount, path=vault_path)
            secrets = read_response['data']['data']
            logger.info("Successfully loaded configuration from HashiCorp Vault", path=f"{vault_mount}/{vault_path}")
            return Settings(**secrets)
        except Exception as e:
            if env == "prod":
                logger.error(f"Failed to load secrets from Vault in production: {e}")
                raise ValueError("Strict Vault enforcement failed in production.")
            else:
                logger.warning(f"Failed to load secrets from Vault: {e}. Falling back to .env")
                return Settings()
    else:
        if env == "prod":
            logger.error("VAULT_URL or VAULT_TOKEN not provided in production!")
            raise ValueError("Vault configuration missing in production (Strict Mode)")
        return Settings()

settings = load_settings()
