# coding=utf-8
import os

from sqlalchemy import create_engine

_POSTGRES_USER = os.environ.get('POSTGRES_USER')
_POSTGRES_DB = os.environ.get('POSTGRES_DB')
_POSTGRES_PASSWORD = os.environ.get('POSTGRES_PASSWORD')
_POSTGRES_HOST = os.environ.get('POSTGRES_HOST')
POSTGRES_CONNECTION_PATH = f'postgresql://{_POSTGRES_USER}:' \
                           f'{_POSTGRES_PASSWORD}@' \
                           f'{_POSTGRES_HOST}/{_POSTGRES_DB}'


class Engine:
    __instance = None

    @classmethod
    def get_instance(cls):
        if not cls.__instance:
            cls.__instance = create_engine(POSTGRES_CONNECTION_PATH)
        return cls.__instance
