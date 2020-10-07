# coding=utf-8
from typing import List, Dict

from api.data_models import OrderId
from api.exceptions import BadRequestFormatExceptioin
from common.sentry import get_logger
from db.db_requests import get_order_by_id
from db.utils import session_scope
from sqlalchemy import null

logger = get_logger(__name__)


def make_delivery_action(orders_data: List[Dict[str, int]], action: str):
    if not isinstance(orders_data, list):
        raise BadRequestFormatExceptioin(
            message=f'Type of request for updating orders should be "list",'
                    f'but received "{type(orders_data)}"'
        )
    orders = [OrderId(**order_data) for order_data in orders_data]
    result = []
    with session_scope() as session:
        for order in orders:
            order_db = get_order_by_id(order.id, session)
            if order_db is None:
                order_result = 'Not found'
                logger.warning('Order "%s" not found for updating', order.id)
            elif order_db.courier_id is None:
                if action == 'done':
                    order_result = 'Order is free'
                    logger.warning(
                        'Order "%s" is not selected by any courier',
                        order.id,
                    )
                elif action == 'cancel':
                    order_db.is_done = False
                    order_result = 'ok'
            elif order_db.courier_id is not None:
                if action == 'done':
                    order_result = 'ok'
                    order_db.courier_id = null()
                    order_db.is_done = True
                elif action == 'cancel':
                    order_result = 'Order is busy'
                    logger.warning(
                        'Order "%s" is already selected by courier "%s"',
                        order.id,
                        order_db.courier_id,
                    )
            result.append({
                'id': order.id,
                'result': order_result,
            })
            session.flush()
    return result
