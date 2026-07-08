# app/web/components/header.py

def render_header(current_page: str = "home", user=None) -> str:
    return f"""
    <header id="main-header">
        <div id="header-nav">
            <a href="/" id="header-logo">руми.</a>
            <button id="header-burger" aria-label="Открыть меню">
                <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-menu" aria-hidden="true">
                    <path d="M3 12h18"></path>
                    <path d="M3 6h18"></path>
                    <path d="M3 18h18"></path>
                </svg>
            </button>
        </div>
    </header>
    """