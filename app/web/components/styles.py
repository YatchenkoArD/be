# app/web/components/styles.py

def get_base_styles() -> str:
    """
    Возвращает HTML-теги для подключения CSS-файлов.
    Костыль чтобы не переписывать все упоминания.
    ВОзможно позже будет заменен сборщиком 
    """
    return """
    <link rel="stylesheet" href="/static/dist/main.css">
    <script type="module" src="/static/dist/main.js"></script>
    """