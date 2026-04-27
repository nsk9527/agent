"""配置管理模块"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """应用配置类"""

    # LLM API 配置
    LLM_API_KEY = os.getenv("LLM_API_KEY", "")
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "")
    LLM_MODEL_ID = os.getenv("LLM_MODEL_ID", "")


# 导出配置实例
config = Config()
