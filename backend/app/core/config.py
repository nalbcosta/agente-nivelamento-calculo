from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
	app_name: str = "Agente Nivelamento Calculo"
	app_version: str = "0.1.0"
	api_v1_prefix: str = "/api/v1"
	database_url: str = (
		"postgresql+psycopg://postgres:postgres@localhost:5432/agente_nivelamento"
	)

	model_config = SettingsConfigDict(
		env_file=".env",
		env_file_encoding="utf-8",
		case_sensitive=False,
		extra="ignore",
	)


settings = Settings()
