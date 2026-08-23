from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    secret_key: SecretStr = SecretStr("")
    database_url: str
    mailtrap_api_token: SecretStr = SecretStr("")

    reset_token_expire_minutes: int = Field(default=60, gt=0)
    mail_server: str = "localhost"
    mail_port: int = Field(default=587, ge=1, le=65535)
    mail_username: str = ""
    mail_password: SecretStr = SecretStr("")
    mail_from: str = "noreply@example.com"
    mail_use_tls: bool = True
    mail_timeout_seconds: float = Field(default=10.0, gt=0)

    frontend_url: str = "http://localhost:8000"


settings = Settings()  # type: ignore
