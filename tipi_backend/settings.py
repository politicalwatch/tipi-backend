from os import environ as env


class Config:
    # Flask settings
    SERVER_NAME = env.get('SERVER_NAME', 'localhost:5000')
    FLASK_DEBUG = env.get('FLASK_DEBUG', True)  # Do not use debug mode in production)
    IP = env.get('IP', '0.0.0.0')
    PORT = env.get('PORT', 5000)

    # Flask-Restplus settings
    SWAGGER_UI_DOC_EXPANSION = env.get('SWAGGER_UI_DOC_EXPANSION', 'list')
    RESTPLUS_VALIDATE = env.get('RESTPLUS_VALIDATE', True)
    RESTPLUS_MASK_SWAGGER = env.get('RESTPLUS_MASK_SWAGGER', False)
    ERROR_404_HELP = env.get('ERROR_404_HELP', False)

    # Mongo settings
    MONGODB_SETTINGS = {
        'host': env.get('MONGO_HOST', '0.0.0.0'),
        'port': env.get('MONGO_PORT', 32817),
        'db': env.get('MONGO_DBNAME', 'tipidb'),
        'username': env.get('MONGO_USERNAME', 'tipi'),
        'password': env.get('MONGO_PASSWORD', 'tipi')
    }
