from pydantic_settings import BaseSettings
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    # Bot settings
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "8284240552:AAGLlARMHz6tYT5vaQcy7p1LjepjPTFfxb0")
    ADMIN_IDS: list[int] = [int(x) for x in os.getenv("ADMIN_IDS", "7936351930").split(",") if x.strip()]
    
    # Database settings
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./bot.db")
    
    # Webhook settings (optional)
    WEBHOOK_HOST: Optional[str] = os.getenv("WEBHOOK_HOST")
    WEBHOOK_PORT: int = int(os.getenv("WEBHOOK_PORT", "8000"))
    WEBHOOK_PATH: str = os.getenv("WEBHOOK_PATH", "/webhook")
    
    # Other settings
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    REFERRAL_REWARD_PERCENT: float = float(os.getenv("REFERRAL_REWARD_PERCENT", "10.0"))
    
    # Support and channels
    SUPPORT_USERNAME: str = os.getenv("SUPPORT_USERNAME", "your_support_username")
    EARNING_CHANNEL: str = os.getenv("EARNING_CHANNEL", "https://t.me/your_earning_channel")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()