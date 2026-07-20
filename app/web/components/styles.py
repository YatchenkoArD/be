# app/web/components/styles.py
import hashlib
import os

# Vite собирает бандл с ФИКСИРОВАННЫМИ именами (main.js/main.css, см. vite.config.js),
# а StaticFiles не шлёт Cache-Control → браузеры эвристически кэшируют старый файл
# без ревалидации. После деплоя URL тот же, содержимое другое → у разных людей
# разные закэшированные версии staging. Лечим cache-busting'ом: ?v=<хэш содержимого>
# меняется при каждой пересборке, между деплоями браузер спокойно кэширует.
_DIST_DIR = "static/dist"


def _asset_version(filename: str) -> str:
    try:
        with open(os.path.join(_DIST_DIR, filename), "rb") as f:
            return hashlib.md5(f.read()).hexdigest()[:10]
    except OSError:
        return "dev"


# Считаем один раз при импорте = при старте контейнера = отражает задеплоенный бандл.
_CSS_V = _asset_version("main.css")
_JS_V = _asset_version("main.js")


def get_base_styles() -> str:
    """HTML-теги подключения собранного CSS/JS-бандла (с cache-busting по хэшу)."""
    return f"""
    <link rel="stylesheet" href="/static/dist/main.css?v={_CSS_V}">
    <script type="module" src="/static/dist/main.js?v={_JS_V}"></script>
    """
