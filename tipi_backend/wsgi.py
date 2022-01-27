from werkzeug.middleware.proxy_fix import ProxyFix

from flask import render_template

from tipi_backend.app import create_app
from tipi_backend.settings import Config

app = create_app(config=Config)

@app.route('/')
def swagger_fix():
    '''Render a SwaggerUI for a given API'''
    return render_template('swagger-ui.html', title='QHLD API Documentation',
            specs_url='https://api.quehacenlosdiputados.es/swagger.json')

app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)


if __name__ == "__main__":
    app.run()
