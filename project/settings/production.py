from base import *

DATABASE_ENGINE = 'postgresql_psycopg2'
DATABASE_HOST = ''
DATABASE_NAME = 'zoo_prod'
DATABASE_USER = 'zoo'
DATABASE_PASSWORD = ''
DATABASE_OPTIONS = {}

BASE_DOMAIN = ''
MEDIA_URL = '/media/'

SSL_ENABLED = True
SEND_BROKEN_LINK_EMAILS = True
SESSION_COOKIE_DOMAIN = '.%s' % BASE_DOMAIN


# Local Cache Settings
# CACHE_BACKEND = 'memcached://172.20.0.56:11211/'
# CACHE_MIDDLEWARE_SECONDS = 300
