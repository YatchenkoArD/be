# app/core/config.py
from pathlib import Path
from typing import List

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Корень проекта (…/be) — чтобы пути к ключам и .env не зависели от cwd
BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    PROJECT_NAME: str = "Beauty Platform"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"

    # Окружение: development | production. Влияет на флаги cookie, HSTS и т.п.
    ENVIRONMENT: str = "development"

    # --- Аутентификация (JWT RS256, асимметричная подпись) ---
    ALGORITHM: str = "RS256"
    # Пути к PEM-ключам. Приватным подписываем, публичным проверяем.
    # Генерация: python -m app.scripts.gen_keys  (см. README)
    JWT_PRIVATE_KEY_PATH: str = str(BASE_DIR / "keys" / "jwt_private.pem")
    JWT_PUBLIC_KEY_PATH: str = str(BASE_DIR / "keys" / "jwt_public.pem")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # короткий access-токен (был 24ч)

    # Секрет для подписи CSRF-токенов и прочих HMAC. ОБЯЗАТЕЛЕН из окружения.
    SECRET_KEY: str

    # --- Cookie ---
    # В проде обязательно True (cookie только по HTTPS).
    COOKIE_SECURE: bool = False

    # --- CORS ---
    # Явный список разрешённых origin'ов (FastAPI не закрывает это по умолчанию).
    CORS_ORIGINS: List[str] = ["http://localhost:8000"]

    # --- Redis (rate limiting, блокировка по аккаунту) ---
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- База данных ---
    POSTGRES_USER: str = "beauty_user"
    POSTGRES_PASSWORD: str  # ОБЯЗАТЕЛЕН из окружения, без дефолта в коде
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: str = "5432"
    POSTGRES_DB: str = "beauty_platform"

    # SQL-эхо в логи. В проде ДОЛЖНО быть False (иначе параметры запросов утекают).
    SQL_ECHO: bool = False

    # --- OTP (подтверждение телефона при регистрации) ---
    # Код и его состояние живут только в Redis (TTL) — своей БД не нужно.
    OTP_METHOD: str = "flash_call"  # flash_call (дешевле) или sms
    OTP_LENGTH: int = 4
    OTP_TTL_MINUTES: int = 5
    MAX_VERIFY_ATTEMPTS: int = 3

    # Провайдер отправки: mock (код никуда не уходит, виден в dev_code ответа
    # и в логах) или live (SMSC.ru, резерв SMS.ru — см. app/services/sms_provider.py).
    SMS_MODE: str = "mock"
    SMSC_LOGIN: str = ""
    SMSC_PASSWORD: str = ""
    SMSC_SENDER_ID: str = ""
    SMSRU_API_ID: str = ""

    # Временный рубильник: пока нет официального подключения SMS-провайдера,
    # OTP_ENABLED=false пропускает реальную отправку/проверку кода (otp.py
    # возвращает фиктивный request_id и считает любой код верным).
    OTP_ENABLED: bool = True

    # Выключенный OTP в production = регистрация без подтверждения телефона.
    # Чтобы рубильник не дожил до релиза незамеченным, в production такое
    # состояние надо подтверждать явно вторым флагом — иначе приложение
    # не стартует (та же логика, что принудительный COOKIE_SECURE).
    OTP_DISABLED_ACK: bool = False

    @model_validator(mode="after")
    def _otp_guard_in_prod(self) -> "Settings":
        # model_validator (не field_validator): должен срабатывать и на дефолтах
        if (
            self.ENVIRONMENT == "production"
            and not self.OTP_ENABLED
            and not self.OTP_DISABLED_ACK
        ):
            raise ValueError(
                "OTP_ENABLED=false в production: любой код подтверждения будет "
                "принят. Если это осознанно (SMS-провайдер ещё не подключён), "
                "задайте OTP_DISABLED_ACK=true; иначе включите OTP_ENABLED."
            )
        if (
            self.ENVIRONMENT == "production"
            and self.OTP_ENABLED
            and self.SMS_MODE == "mock"
        ):
            raise ValueError(
                "SMS_MODE=mock в production при включённом OTP: коды не уходят "
                "на телефон, а возвращаются в ответе /send-code любому, кто их "
                "запросил (dev_code) — проверка телефона превращается в бутафорию. "
                "Настройте SMS_MODE=live с кредами SMSC, либо отключите OTP "
                "осознанно (OTP_ENABLED=false + OTP_DISABLED_ACK=true)."
            )
        return self

    @field_validator("COOKIE_SECURE")
    @classmethod
    def _force_secure_in_prod(cls, v: bool, info) -> bool:
        # Подстраховка: в production cookie всегда secure.
        if info.data.get("ENVIRONMENT") == "production":
            return True
        return v

    @property
    def DATABASE_URL(self) -> str:
        """Строка подключения для asyncpg."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
