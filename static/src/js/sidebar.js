// static/src/js/sidebar.js

document.addEventListener('DOMContentLoaded', function () {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    const burger = document.getElementById('header-burger');

    function openSidebar() {
        if (sidebar) sidebar.classList.add('open');
        if (overlay) overlay.classList.add('active');
        if (burger) burger.classList.add('hidden'); // скрываем бургер
    }

    function closeSidebar() {
        if (sidebar) sidebar.classList.remove('open');
        if (overlay) overlay.classList.remove('active');
        if (burger) burger.classList.remove('hidden'); // показываем бургер
    }

    function toggleSidebar() {
        if (sidebar && sidebar.classList.contains('open')) {
            closeSidebar();
        } else {
            openSidebar();
        }
    }

    if (burger) {
        burger.addEventListener('click', toggleSidebar);
    }

    if (overlay) {
        overlay.addEventListener('click', closeSidebar);
    }

    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') {
            closeSidebar();
        }
    });

    window.addEventListener('resize', function () {
        if (window.innerWidth >= 1024) {
            closeSidebar(); 
        }
    });
});