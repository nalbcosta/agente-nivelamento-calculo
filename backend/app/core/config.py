from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
	app_name: str = "Agente Nivelamento Calculo"
	app_version: str = "0.1.0"
	api_v1_prefix: str = "/api/v1"
	lesson_markdown_path: str = "/app/data/calculo_i_aula.md"
	embedding_provider: str = "fastembed"
	embedding_model_name: str = "BAAI/bge-small-en-v1.5"
	embedding_dimension: int = 384
	llm_provider: str = "rule"
	llm_temperature: float = 0.2
	llm_max_new_tokens: int = 320
	ollama_base_url: str = "http://host.docker.internal:11434"
	ollama_embedding_model: str = "nomic-embed-text"
	ollama_chat_model: str = "llama3.1:8b"
	huggingface_api_token: str = ""
	huggingface_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
	huggingface_chat_model: str = "HuggingFaceH4/zephyr-7b-beta"
	rag_top_k_default: int = 4
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
