from pydantic_settings import BaseSettings, SettingsConfigDict



class Settings(BaseSettings):
    APP_ENV: str = "dev"
    PORT: int = 8084
    DATABASE_URL: str
    JWT_SECRET: str
    JWT_ALGORITHM: str
    RAZORPAY_KEY_ID: str | None = None
    RAZORPAY_KEY_SECRET: str | None = None
    RAZORPAY_WEBHOOK_SECRET: str | None = None
    BOOKING_SERVICE_URL: str = "http://localhost:8083"
    REDIS_URL: str = "redis://localhost:6379/0"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    ANONYMOUS_TOKEN_EXPIRE_MINUTES: int = 60
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


Config = Settings()


broker_url = Config.REDIS_URL
broker_connection_retry_on_startup = True
