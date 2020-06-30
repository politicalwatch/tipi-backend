from os import environ as env


class Config:
    # Flask settings
    SERVER_NAME = env.get('SERVER_NAME', 'localhost:5000')
    FLASK_DEBUG = env.get('FLASK_DEBUG', 'True') == 'True'  # Do not use debug mode in production)
    IP = env.get('IP', '0.0.0.0')
    PORT = env.get('PORT', 5000)

    # Flask-Restplus settings
    SWAGGER_UI_DOC_EXPANSION = env.get('SWAGGER_UI_DOC_EXPANSION', 'list')
    RESTPLUS_VALIDATE = env.get('RESTPLUS_VALIDATE', "True") == "True"
    RESTPLUS_MASK_SWAGGER = env.get('RESTPLUS_MASK_SWAGGER', "False") == "True"
    ERROR_404_HELP = env.get('ERROR_404_HELP', "False") == "True"
    USE_ALERTS = env.get('USE_ALERTS', 'False') == 'True'
    COUNTRY = env.get('COUNTRY', 'spain')

    # Mongo settings
    MONGODB_SETTINGS = {
        'host': env.get('MONGO_HOST', '0.0.0.0'),
        'port': int(env.get('MONGO_PORT', '27017')),
        'db': env.get('MONGO_DB_NAME', 'tipidb'),
        'username': env.get('MONGO_USER', 'tipi'),
        'password': env.get('MONGO_PASSWORD', 'tipi')
    }

    # Redis caching
    CACHE = {
        'CACHE_TYPE': env.get('CACHE_TYPE', 'redis'),
        'CACHE_DEFAULT_TIMEOUT': int(env.get('CACHE_DEFAULT_TIMEOUT', '600')),
        'CACHE_KEY_PREFIX': env.get('CACHE_KEY_PREFIX', ''),
        'CACHE_REDIS_HOST': env.get('CACHE_REDIS_HOST', 'redis'),
        'CACHE_REDIS_PORT': int(env.get('CACHE_REDIS_PORT', '6379')),
        'CACHE_REDIS_PASSWORD': env.get('CACHE_REDIS_PASSWORD', ''),
        'CACHE_REDIS_DB': int(env.get('CACHE_REDIS_DB', '8')),
    }

    # App
    MAX_CONTENT_LENGTH = eval(env.get('MAX_CONTENT_LENGTH', '20*1024*1024'))
    CACHE_TAGS = env.get('CACHE_TAGS', 'tagging-tags')
    TAGGER_MAX_WORDS = int(env.get('TAGGER_MAX_WORDS', '2500'))
