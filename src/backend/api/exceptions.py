# coding=utf-8

from flask_api.status import (
    HTTP_403_FORBIDDEN,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
)


class BaseCustomException(Exception):

    response_code = HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(self, message):
        self.message = message
        Exception.__init__(self, message)

    def __str__(self):
        return self.message


class JWTExpiredException(BaseCustomException):
    response_code = HTTP_403_FORBIDDEN


class JWTException(BaseCustomException):
    response_code = HTTP_403_FORBIDDEN


class BadRequestFormatExceptioin(BaseCustomException):
    response_code = HTTP_400_BAD_REQUEST


class BaseNotFoundException(BaseCustomException):
    response_code = HTTP_404_NOT_FOUND


class CourierNotFoundException(BaseNotFoundException):
    pass


class OrderNotFoundException(BaseNotFoundException):
    pass
