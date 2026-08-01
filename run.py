import sys
import webbrowser
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    """Запуск приложения"""
    print("=" * 60)
    print("  MediaTracker - Умное хранилище видеоколлекции")
    print("=" * 60)
    print("\nЗапуск сервера...")
    print("Открывается браузер: http://localhost:5000")
    print("\nНажмите Ctrl+C для остановки\n")
    
    webbrowser.open('http://localhost:5000')
    
    from web.app import app
    app.run(debug=True, host='0.0.0.0', port=5000)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nСервер остановлен. До свидания!")
        sys.exit(0)
    except Exception as e:
        print(f"\nОшибка запуска: {e}")
        sys.exit(1)