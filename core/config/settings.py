from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    AUTH0_DOMAIN: str
    AUTH0_AUDIENCE: str
    
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
