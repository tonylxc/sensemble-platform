from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    secret_key: str = "change-me"
    access_token_expire_minutes: int = 720
    admin_username: str = "admin"
    admin_password: str = "admin123"
    cors_origins: str = "*"

    db_host: str = "db"
    db_port: int = 5432
    db_user: str = "sensemble"
    db_password: str = "sensemble"
    db_name: str = "sensemble"

    mqtt_host: str = "emqx"
    mqtt_port: int = 1883
    mqtt_topic: str = "sensemble/+/data"
    mqtt_enabled: bool = True
    # 后端 ingest 在 EMQX 上的服务账号（超级用户）；EMQX 认证回调共享密钥
    mqtt_backend_user: str = "backend-ingest"
    mqtt_backend_password: str = "backend-ingest-secret"
    mqtt_auth_secret: str = ""
    rate_limit_min_interval: float = 0.0      # 每设备最小上报间隔(秒)，0=不限流
    offline_monitor_enabled: bool = True
    offline_check_interval: int = 60          # 离线巡检周期(秒)

    @property
    def database_url(self) -> str:
        return (f"postgresql+psycopg2://{self.db_user}:{self.db_password}"
                f"@{self.db_host}:{self.db_port}/{self.db_name}")


settings = Settings()
