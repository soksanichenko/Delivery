# coding=utf-8
from typing import (
    List,
    Dict,
)

from api.api_handlers.distance_handlers import calculate_distance
from api.data_models import (
    OrderId,
    Order,
    Location as LocationDataModel,
)
from api.exceptions import (
    BadRequestFormatExceptioin,
    CourierNotFoundException,
)
from common.sentry import get_logger
from db.db_requests import (
    get_speed_bonus_type,
    get_delay_penalty_type,
    get_order_by_id,
    get_courier_by_id,
)
from db.models import (
    Order as OrderDB,
    Location,
    Hours,
)
from db.utils import session_scope
from resolver.main import insert_to_queue
from sqlalchemy import null
from sqlalchemy.orm import Session

logger = get_logger(__name__)


def get_orders():
    with session_scope() as session:
        orders = session.query(OrderDB).all()  # type: List[OrderDB]

        return [order.to_dict() for order in orders]


def _update_order(order: Order, session: Session) -> bool:
    """
    Update an existing order in DB
    """
    order_db = get_order_by_id(order.id, session)
    if order_db is None:
        logger.info('Order with ID "%s" not found for updating', order.id)
        return False
    order_db_dict = order_db.to_dict()
    logger.debug('Order is taken from DB "%s"', order_db_dict)
    order_dict = order.dict()
    logger.debug('Order is taken from data model "%s"', order_dict)
    if order_db_dict == order_dict:
        logger.info(
            'Order "%s" is equal to order "%s". Nothing to update',
            order_db_dict,
            order_dict,
        )
        return True
    order_db.id = order.id
    order_db.geozone_id = order.geozone_id
    order_db.weight = order.weight
    order_db.price = order.price
    order_db.is_urgent = order.is_urgent
    order_db.issue_time = order.issue_time
    order_db.outsource_price = order.outsource_price
    is_location_changed = False
    if order_db.location.latitude != order.location.lat or \
            order_db.location.longtitude != order.location.lon:
        order_db.location.latitude = order.location.lat
        order_db.location.longtitude = order.location.lon
        is_location_changed = True
    if isinstance(order.speed_bonus, str):
        speed_bonus_type = get_speed_bonus_type(
            order.speed_bonus,
            session,
        )
        order_db.speed_bonus = speed_bonus_type
        order_db.speed_bonus_id = speed_bonus_type.id
        order_db.speed_bonus_value = null()
    else:
        order_db.speed_bonus_value = order.speed_bonus
        order_db.speed_bonus_id = null()
    if isinstance(order.delay_penalty, str):
        delay_penalty_type = get_delay_penalty_type(
            order.delay_penalty,
            session,
        )
        order_db.delay_penalty = delay_penalty_type
        order_db.delay_penalty_id = delay_penalty_type.id
        order_db.delay_penalty_value = null()
    else:
        order_db.delay_penalty_value = order.delay_penalty
        order_db.delay_penalty_id = null()
    if order_db.delivery_time is not None and order.delivery_time is not None:
        order_db.delivery_time.end = order.delivery_time.end
        order_db.delivery_time.start = order.delivery_time.start
    elif order_db.delivery_time is None and order.delivery_time is not None:
        delivery_time_to_create = Hours(
            start=order.delivery_time.start,
            end=order.delivery_time.end,
        )
        session.add(delivery_time_to_create)
        order_db.delivery_time = delivery_time_to_create
        order_db.delivery_time_id = delivery_time_to_create.id
    elif order_db.delivery_time is not None and order.delivery_time is None:
        session.delete(order_db.delivery_time)
        order_db.delivery_time_id = null()
    order_db.is_urgent = order.is_urgent
    if order.courier_id is not None:
        courier = get_courier_by_id(order.courier_id, session)
        if courier is None:
            raise CourierNotFoundException(
                message=f'Courier with ID {order.courier_id} '
                        'doesn\'t exist'
            )
        order_db.courier = courier
        order_db.courier_id = courier.id
    elif order_db.courier is not None:
        order_db.courier_id = null()

    session.flush()
    if is_location_changed:
        calculate_distance(
            'order',
            order_db.id,
            LocationDataModel(**order_db.location.to_dict()),
            session,
        )
        insert_to_queue(
            'order',
            order_db.id,
            session,
        )
    return True


def save_orders(orders_data):
    if not isinstance(orders_data, list):
        raise BadRequestFormatExceptioin(
            message=f'Type of request for adding/updating orders should be '
                    f'"list", but received "{type(orders_data)}"'
        )
    orders = [Order(**order_data) for order_data in orders_data]
    with session_scope() as session:
        for order in orders:
            if _update_order(order, session):
                continue
            location_to_create = Location(
                latitude=order.location.lat,
                longtitude=order.location.lon,
            )
            session.add(location_to_create)
            order_to_create = OrderDB(
                id=order.id,
                location_id=location_to_create.id,
                location=location_to_create,
                weight=order.weight,
                price=order.price,
                geozone_id=order.geozone_id,
                is_urgent=order.is_urgent,
                issue_time=order.issue_time,
                outsource_price=order.outsource_price,
            )
            if isinstance(order.speed_bonus, str):
                speed_bonus_type = get_speed_bonus_type(
                    order.speed_bonus,
                    session,
                )
                order_to_create.speed_bonus = speed_bonus_type
                order_to_create.speed_bonus_id = speed_bonus_type.id
            else:
                order_to_create.speed_bonus_value = order.speed_bonus
            if isinstance(order.delay_penalty, str):
                delay_penalty_type = get_delay_penalty_type(
                    order.delay_penalty,
                    session,
                )
                order_to_create.delay_penalty = delay_penalty_type
                order_to_create.delay_penalty_id = delay_penalty_type.id
            else:
                order_to_create.delay_penalty_value = order.delay_penalty
            if order.delivery_time is not None:
                delivery_time_to_create = Hours(
                    start=order.delivery_time.start,
                    end=order.delivery_time.end,
                )
                session.add(delivery_time_to_create)
                order_to_create.delivery_time = delivery_time_to_create
                order_to_create.delivery_time_id = delivery_time_to_create.id
            if order.courier_id is not None:
                courier = get_courier_by_id(order.courier_id, session)
                if courier is None:
                    raise CourierNotFoundException(
                        message=f'Courier with ID {order.courier_id} '
                                'doesn\'t exist'
                    )
                order_to_create.courier = courier
                order_to_create.courier_id = courier.id
            session.add(order_to_create)
            session.flush()
            calculate_distance(
                'order',
                order_to_create.id,
                LocationDataModel(**order_to_create.location.to_dict()),
                session,
            )
            insert_to_queue(
                'order',
                order_to_create.id,
                session,
            )
    return [order.dict() for order in orders]


def remove_orders(orders_data: List[Dict[str, int]]):
    if not isinstance(orders_data, list):
        raise BadRequestFormatExceptioin(
            message=f'Type of request for deleting orders should be "list",'
                    f'but received "{type(orders_data)}"'
        )
    orders = [OrderId(**order_data) for order_data in orders_data]
    result = []
    with session_scope() as session:
        for order in orders:
            order_db = get_order_by_id(order.id, session)
            if order_db is None:
                result.append({
                    'id': order.id,
                    'result': 'error',
                })
                logger.info(
                    'Order with ID "%s" not found for deleting',
                    order.id,
                )
            else:
                session.delete(order_db)
                result.append({
                    'id': order.id,
                    'result': 'ok',
                })
                logger.info(
                    'Order with ID "%s" is removed',
                    order.id,
                )
    return result
