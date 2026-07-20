# app/web/components/hint.py


def hint(text: str) -> str:
    """Значок ⓘ с пояснением по наведению/тапу рядом с заголовком блока."""
    escaped = text.replace('"', '&quot;')
    return f'<span class="info-hint" tabindex="0" data-tooltip="{escaped}">i</span>'
