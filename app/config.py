from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://bet:bet@db:5432/bet_tracker"
    app_password: str = "troque_isso"
    session_secret: str = "gere_uma_chave_aleatoria_longa"
    timezone: str = "America/Sao_Paulo"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
