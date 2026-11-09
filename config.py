from os import environ
from urllib.parse import quote_plus
from dotenv import load_dotenv

load_dotenv()

class Config:
    DB_HOST = environ.get('DB_HOST')
    DB_USER = environ.get('DB_USER')
    DB_PASSWORD = environ.get('DB_PASSWORD')
    DB_NAME = environ.get('DB_NAME')
    DB_PORT = environ.get('DB_PORT', '3306')
    
    if environ.get('TESTING') == 'True':
        SQLALCHEMY_DATABASE_URI = environ.get('SQLALCHEMY_DATABASE_URI', 'sqlite:///:memory:')
    else:
        _password_encoded = quote_plus(DB_PASSWORD) if DB_PASSWORD else ''
        SQLALCHEMY_DATABASE_URI = f'mysql://{DB_USER}:{_password_encoded}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
