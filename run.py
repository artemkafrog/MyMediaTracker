import sys
import webbrowser
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    """Launch the MediaTracker application."""
    print("=" * 60)
    print("  MediaTracker - Smart Media Collection Storage")
    print("=" * 60)
    print("\nStarting server...")
    print("Opening browser: http://localhost:5000")
    print("\nPress Ctrl+C to stop\n")

    webbrowser.open('http://localhost:5000')

    from web.app import app
    app.run(debug=True, host='0.0.0.0', port=5000)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nServer stopped. Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\nStartup error: {e}")
        sys.exit(1)