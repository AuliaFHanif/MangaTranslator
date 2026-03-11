from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)
    host: str = "127.0.0.1"
    port: int = 8000
    debug: bool = False
    lmstudio_host: str = "127.0.0.1"
    lmstudio_port: int = 1234
    max_concurrent_pages: int = 2
    job_queue_max_size: int = 500

settings = Settings()
