// theme.js - единое хранилище темы для всего сайта

const ThemeManager = {
    // Ключ для localStorage
    STORAGE_KEY: 'mediatracker_theme',
    
    // Текущее состояние темы
    _darkMode: true,
    
    // Инициализация темы
    init() {
        // Загружаем сохраненную тему
        const saved = localStorage.getItem(this.STORAGE_KEY);
        if (saved !== null) {
            this._darkMode = saved === 'true';
        } else {
            // Если нет сохраненной темы, используем системные настройки
            this._darkMode = window.matchMedia('(prefers-color-scheme: dark)').matches;
        }
        
        this.applyTheme();
        console.log('Theme initialized:', this._darkMode ? 'dark' : 'light');
        return this._darkMode;
    },
    
    // Получить текущую тему
    isDark() {
        return this._darkMode;
    },
    
    // Переключить тему
    toggle() {
        this._darkMode = !this._darkMode;
        this.saveTheme();
        this.applyTheme();
        return this._darkMode;
    },
    
    // Установить тему
    setTheme(darkMode) {
        this._darkMode = darkMode;
        this.saveTheme();
        this.applyTheme();
    },
    
    // Сохранить тему в localStorage
    saveTheme() {
        localStorage.setItem(this.STORAGE_KEY, String(this._darkMode));
    },
    
    // Применить тему к DOM
    applyTheme() {
        if (this._darkMode) {
            document.body.classList.remove('light-theme');
            document.body.style.background = '#0B0B0B';
            const app = document.getElementById('app');
            if (app) app.classList.remove('light-theme');
        } else {
            document.body.classList.add('light-theme');
            document.body.style.background = '#F7F7F7';
            const app = document.getElementById('app');
            if (app) app.classList.add('light-theme');
        }
        
        // Обновляем все Vue-приложения
        document.querySelectorAll('[data-theme-aware]').forEach(el => {
            // Сигнализируем о смене темы
            const event = new CustomEvent('themeChanged', {
                detail: { darkMode: this._darkMode }
            });
            el.dispatchEvent(event);
        });
    },
    
    // Получить иконку темы
    getThemeIcon() {
        return this._darkMode ? '🌙' : '☀️';
    },
    
    // Получить текст кнопки темы
    getThemeLabel() {
        return this._darkMode ? 'Light' : 'Dark';
    }
};

// Инициализируем тему при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    ThemeManager.init();
});

// Синхронизация между вкладками
window.addEventListener('storage', (e) => {
    if (e.key === ThemeManager.STORAGE_KEY) {
        const darkMode = e.newValue === 'true';
        ThemeManager.setTheme(darkMode);
    }
});