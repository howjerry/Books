"""配置管理模組"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """應用配置

    從環境變數或 .env 檔案載入配置。
    """

    # API Keys
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # 模型設定
    model_name: str = "claude-3-5-sonnet-20241022"
    temperature: float = 0.7
    max_tokens: int = 1024

    # 應用設定
    debug: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# 全域設定實例
settings = Settings()
