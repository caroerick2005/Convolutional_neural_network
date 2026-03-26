__all__ = ["model"]

try:
    from flask import Flask

    app = Flask(__name__)
    app.config.from_object('config')

    from app import views
except Exception:
    # Silently skip Flask init when imported outside the CNN app context
    # (e.g. when Streamlit Cloud scans the project directory)
    pass