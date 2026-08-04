const ThemeManager = {
    STORAGE_KEY: 'mediatracker_theme',

    _darkMode: true,

    init() {
        const saved = localStorage.getItem(this.STORAGE_KEY);
        if (saved !== null) {
            this._darkMode = saved === 'true';
        } else {
            this._darkMode = window.matchMedia('(prefers-color-scheme: dark)').matches;
        }

        this.applyTheme();
        console.log('Theme initialized:', this._darkMode ? 'dark' : 'light');
        return this._darkMode;
    },

    isDark() {
        return this._darkMode;
    },

    toggle() {
        this._darkMode = !this._darkMode;
        this.saveTheme();
        this.applyTheme();
        return this._darkMode;
    },

    setTheme(darkMode) {
        this._darkMode = darkMode;
        this.saveTheme();
        this.applyTheme();
    },

    saveTheme() {
        localStorage.setItem(this.STORAGE_KEY, String(this._darkMode));
    },

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

        document.querySelectorAll('[data-theme-aware]').forEach(el => {
            const event = new CustomEvent('themeChanged', {
                detail: { darkMode: this._darkMode }
            });
            el.dispatchEvent(event);
        });
    },

    getThemeIcon() {
        return this._darkMode ? '🌙' : '☀️';
    },

    getThemeLabel() {
        return this._darkMode ? 'Light' : 'Dark';
    }
};

document.addEventListener('DOMContentLoaded', () => {
    ThemeManager.init();
});

window.addEventListener('storage', (e) => {
    if (e.key === ThemeManager.STORAGE_KEY) {
        const darkMode = e.newValue === 'true';
        ThemeManager.setTheme(darkMode);
    }
});