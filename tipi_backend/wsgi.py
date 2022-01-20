from tipi_backend.app import create_app
from tipi_backend.settings import Config


app = create_app(config=Config)


if __name__ == "__main__":
    app.run()
