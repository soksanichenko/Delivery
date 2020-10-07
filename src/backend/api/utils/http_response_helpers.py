# coding=utf-8

import time
from functools import wraps
from typing import (
    Dict,
    Any,
)

from api.exceptions import (
    BaseCustomException,
    BaseNotFoundException,
)
from flask import (
    Response,
    jsonify,
    make_response,
)
from flask_api.status import HTTP_200_OK
from pydantic import ValidationError
from werkzeug.exceptions import InternalServerError


def jsonify_response(
        status: str,
        result: Dict[str, Any],
        status_code: int,
) -> Response:
    return make_response(
        jsonify(
            status=status,
            result=result,
            timestamp=int(time.time())
        ),
        status_code,
    )


def success_result(f):
    """
    Decorator: wrap success result
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        result = f(*args, **kwargs)
        return jsonify_response(
            status='success',
            result=result,
            status_code=HTTP_200_OK,
        )

    decorated_function.__name__ = f.__name__
    return decorated_function


def error_result(f):
    """
    Decorator: catch unknown exceptions and raise InternalServerError
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except BaseNotFoundException:
            raise
        except BaseCustomException:
            raise
        except ValidationError:
            raise
        except Exception as err:
            raise InternalServerError(
                description=str(err),
                original_exception=err,
            )

    decorated_function.__name__ = f.__name__
    return decorated_function
