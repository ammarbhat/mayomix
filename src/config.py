from pydantic_settings import BaseSettings, SettingsConfigDict


class EnvSettings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    ALGORITHM: str
    ORIGINS: list[str]
    MUSICBRAINZ_USER_AGENT: str

    model_config = SettingsConfigDict(env_file=".env")


settings = EnvSettings()
