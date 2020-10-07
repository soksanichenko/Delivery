# coding=utf-8

import os
from functools import wraps
from typing import (
    Optional,
    Dict,
    Union,
)

from api.exceptions import (
    JWTException,
    JWTExpiredException,
)
from flask import request
from jwt import decode
from jwt.exceptions import (
    ExpiredSignatureError,
    PyJWTError,
)

JWT_PUBLIC_KEY = os.environ.get('JWT_PUBLIC_KEY')
TOKEN_DECODE_ALGORITHM = 'RS256'


def validate_and_decode_token(
        jwt_token: Optional[str],
) -> Dict[str, Union[str, int]]:
    """
    Validate and decode JWT token and return its body
    :param jwt_token: encoded JWT token
    :return:
    """
    if jwt_token is None:
        raise JWTException('No JWT token received')
    try:
        data = decode(
            jwt_token.encode('utf-8'),
            JWT_PUBLIC_KEY,
            algorithms=[
                TOKEN_DECODE_ALGORITHM,
            ],
            options={
                'require_exp': True,
            }
        )
    except ExpiredSignatureError:
        raise JWTExpiredException('Signature of JWT token expired')
    except PyJWTError:
        raise JWTException('Can\'t decode token data')
    return data


def jwt_required(f):
    """
    Decorator: Check auth JWT token
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        validate_and_decode_token(request.cookies.get('JWT'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function
