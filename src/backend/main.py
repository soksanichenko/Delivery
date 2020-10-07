# coding=utf-8

import os
from random import choice
from string import (
    ascii_uppercase,
    digits,
)

from api.admin import create_flask_admin
from api.api_handlers.couriers_handlers import (
    get_couriers,
    save_couriers,
    remove_couriers,
)
from api.api_handlers.deliveries_handlers import make_delivery_action
from api.api_handlers.orders_handlers import (
    get_orders,
    save_orders,
    remove_orders,
)
from api.api_handlers.points_handlers import action_on_point
from api.api_handlers.stocks_handlers import (
    get_stocks,
    save_stocks,
    remove_stocks,
)
from api.exceptions import (
    JWTExpiredException,
    JWTException,
    BaseCustomException,
    BadRequestFormatExceptioin,
)
from api.utils.http_response_helpers import (
    success_result,
    error_result,
    jsonify_response,
)
from api.utils.jwt_token_helpers import jwt_required
from common.sentry import (
    init_sentry_client,
    get_logger,
)
from flask import (
    Flask,
    Response,
    request,
)
from pydantic import ValidationError
from werkzeug.exceptions import InternalServerError

main = Flask(__name__)
init_sentry_client()
# It's needed for sessions mechanism of flask-admin
main.secret_key = ''.join(choice(ascii_uppercase + digits) for _ in range(20))
create_flask_admin(main)
logger = get_logger(__name__)


@main.route('/stocks', methods=('GET', 'POST', 'DELETE'))
@success_result
@error_result
@jwt_required
def stocks():
    if request.method == 'GET':
        return get_stocks()
    elif request.method == 'POST':
        return save_stocks(request.json)
    elif request.method == 'DELETE':
        return remove_stocks(request.json)


@main.route('/orders', methods=('GET', 'POST', 'DELETE'))
@success_result
@error_result
@jwt_required
def orders():
    if request.method == 'GET':
        return get_orders()
    elif request.method == 'POST':
        return save_orders(request.json)
    elif request.method == 'DELETE':
        return remove_orders(request.json)


@main.route('/delivered', methods=('POST',))
@success_result
@error_result
@jwt_required
def delivers():
    return make_delivery_action(request.json, action='done')


@main.route('/undeliver', methods=('POST',))
@success_result
@error_result
@jwt_required
def undeliver():
    return make_delivery_action(request.json, action='cancel')


@main.route('/couriers', methods=('GET', 'POST', 'DELETE'))
@success_result
@error_result
@jwt_required
def couriers():
    if request.method == 'GET':
        return get_couriers()
    elif request.method == 'POST':
        return save_couriers(request.json)
    elif request.method == 'DELETE':
        return remove_couriers(request.json)


@main.route('/next', methods=('POST',))
@success_result
@error_result
@jwt_required
def next_point():
    return action_on_point(request.json, action='next')


@main.route('/go', methods=('POST',))
@success_result
@error_result
@jwt_required
def go_to_point():
    return action_on_point(request.json, action='go')


@main.route('/ungo', methods=('POST',))
@success_result
@error_result
@jwt_required
def undo_go_to_point():
    return action_on_point(request.json, action='ungo')


@main.route('/debug/<result>', methods=('GET',))
@success_result
@error_result
@jwt_required
def debug_success(result: str):
    if os.getenv('DEBUG_ENDPOINTS') == 'true':
        if result == 'success':
            return 'Test debug success'
        elif result == 'error':
            raise SyntaxError('Test debug error')


@main.errorhandler(JWTExpiredException)
@main.errorhandler(JWTException)
def handle_jwt_exception(error: BaseCustomException) -> Response:
    logger.exception(error.message)
    return jsonify_response(
        status='error',
        result={
            'message': error.message,
        },
        status_code=error.response_code,
    )


@main.errorhandler(BadRequestFormatExceptioin)
def handle_bad_request_format(error: BadRequestFormatExceptioin) -> Response:
    logger.exception(error.message)
    return jsonify_response(
        status='error',
        result={
            'message': error.message,
        },
        status_code=error.response_code,
    )


@main.errorhandler(ValidationError)
def handle_validation_error(error: ValidationError) -> Response:
    logger.exception(str(error))
    return jsonify_response(
        status='error',
        result={
            'message': str(error),
        },
        status_code=400,
    )


@main.errorhandler(InternalServerError)
def handle_internal_server_error(error: InternalServerError) -> Response:
    logger.exception(str(error))
    return jsonify_response(
        status='error',
        result={
            'message': 'Internal server error',
        },
        status_code=error.code,
    )
