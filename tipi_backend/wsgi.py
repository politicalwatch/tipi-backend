from werkzeug.middleware.proxy_fix import ProxyFix

from tipi_backend.app import create_app
from tipi_backend.settings import Config


app = create_app(config=Config)
app.wsgi_app = ProxyFix(app.wsgi_app)


if __name__ == "__main__":
    app.run()
