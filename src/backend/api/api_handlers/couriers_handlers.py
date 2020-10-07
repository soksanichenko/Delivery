# coding=utf-8
from typing import (
    List,
    Dict,
)

from api.api_handlers.distance_handlers import calculate_distance
from api.data_models import (
    CourierId,
    Courier,
    Location as LocationDataModel,
)
from api.exceptions import (
    BadRequestFormatExceptioin,
    OrderNotFoundException,
)
from common.sentry import get_logger
from db.db_requests import (
    get_courier_by_id,
    get_transport_type,
    get_order_by_id,
)
from db.models import (
    Courier as CourierDB,
    Break,
    Location,
    Hours,
)
from db.utils import session_scope
from resolver.main import insert_to_queue
from sqlalchemy import null
from sqlalchemy.orm import Session

logger = get_logger(__name__)


def get_couriers():
    with session_scope() as session:
        couriers = session.query(CourierDB).all()  # type: List[CourierDB]

        return [courier.to_dict() for courier in couriers]


def _update_courier(courier: Courier, session: Session) -> bool:
    """
    Update an existing courier in DB
    """
    courier_db = get_courier_by_id(courier.id, session)
    if courier_db is None:
        logger.info('Courier with ID "%s" not found for updating', courier.id)
        return False
    courier_db_dict = courier_db.to_dict()
    logger.debug('Courier is taken from DB "%s"', courier_db_dict)
    courier_dict = courier.dict()
    logger.debug('Courier is taken from data model "%s"', courier_dict)
    if courier_db_dict == courier_dict:
        logger.info(
            'Courier "%s" is equal to order "%s". Nothing to update',
            courier_db_dict,
            courier_dict,
        )
        return True
    is_location_changed = False
    if courier.location is not None and courier_db.location is not None:
        courier_db.location.longtitude = courier.location.lon
        courier_db.location.lat = courier.location.lat
        is_location_changed = True
    elif courier.location is not None and courier_db.location is None:
        location_to_create = Location(
            latitude=courier.location.lat,
            longtitude=courier.location.lon,
        )
        session.add(location_to_create)
        courier_db.location = location_to_create
        courier_db.location.id = location_to_create.id
        is_location_changed = True
    elif courier.location is None and courier_db.location is not None:
        session.delete(courier_db.location)
    transport_type = get_transport_type(courier.transport_type, session)
    courier_db.transport_type_id = transport_type.id
    courier_db.max_capacity = courier.max_capacity
    courier_db.max_price = courier.max_price
    courier_db.avg_speed = courier.avg_speed
    courier_db.hours.end = courier.hours.end
    courier_db.hours.start = courier.hours.start
    for courier_break in courier_db.breaks:
        logger.info('Remove old courier break "%s"', courier_break.to_dict())
        session.delete(courier_break)
    breaks_to_create = [
        Break(
            start=courier_break.start,
            end=courier_break.end,
        ) for courier_break in courier.breaks
    ]
    session.add(*breaks_to_create)
    courier_db.geozone_id = courier.geozone_id
    courier_db.hour_price = courier.hour_price
    courier_db.km_price = courier.km_price
    courier_db.start_price = courier.start_price
    if courier.order_id is not None:
        order = get_order_by_id(courier.order_id, session)
        if order is None:
            raise OrderNotFoundException(
                message=f'Order with ID {courier.order_id} '
                        'doesn\'t exist'
            )
        courier_db.order = order
    elif courier_db.order is not None:
        courier_db.order.courier_id = null()
    session.flush()
    if is_location_changed:
        calculate_distance(
            'courier',
            courier_db.id,
            LocationDataModel(**courier_db.location.to_dict()),
            session,
        )
        insert_to_queue(
            'courier',
            courier_db.id,
            session,
        )
    return True


def save_couriers(couriers_data):
    if not isinstance(couriers_data, list):
        raise BadRequestFormatExceptioin(
            message=f'Type of request for adding/updating couriers should be '
                    f'"list", but received "{type(couriers_data)}"'
        )
    couriers = [Courier(**courier_data) for courier_data in couriers_data]
    with session_scope() as session:
        for courier in couriers:
            if _update_courier(courier, session):
                continue
            transport_type = get_transport_type(
                courier.transport_type,
                session,
            )
            courier_hours_to_create = Hours(
                start=courier.hours.start,
                end=courier.hours.end,
            )
            session.add(courier_hours_to_create)
            breaks_to_create = [
                Break(
                    start=stock_break.start,
                    end=stock_break.end,
                ) for stock_break in courier.breaks
            ]
            session.add(*breaks_to_create)
            courier_to_create = CourierDB(
                id=courier.id,
                transport_type=transport_type,
                transport_type_id=transport_type.id,
                max_capacity=courier.max_capacity,
                max_price=courier.max_price,
                avg_speed=courier.avg_speed,
                hours_id=courier_hours_to_create.id,
                hours=courier_hours_to_create,
                breaks=breaks_to_create,
                geozone_id=courier.geozone_id,
                hour_price=courier.hour_price,
                km_price=courier.km_price,
                start_price=courier.start_price,
            )
            if courier.location is not None:
                location_to_create = Location(
                    latitude=courier.location.lat,
                    longtitude=courier.location.lon,
                )
                session.add(location_to_create)
                courier_to_create.location = location_to_create
                courier_to_create.location.id = location_to_create.id
            if courier.order_id is not None:
                order = get_order_by_id(courier.order_id, session)
                if order is None:
                    raise OrderNotFoundException(
                        message=f'Order with ID {courier.order_id} '
                                'doesn\'t exist'
                    )
                courier_to_create.order = order
            session.add(courier_to_create)
            session.flush()
            calculate_distance(
                'courier',
                courier_to_create.id,
                LocationDataModel(**courier_to_create.location.to_dict()),
                session,
            )
            insert_to_queue(
                'courier',
                courier_to_create.id,
                session,
            )
    return [courier.dict() for courier in couriers]


def remove_couriers(couriers_data: List[Dict[str, int]]):
    if not isinstance(couriers_data, list):
        raise BadRequestFormatExceptioin(
            message=f'Type of request for deleting couriers should be "list",'
                    f'but received "{type(couriers_data)}"'
        )
    couriers = [CourierId(**order_data) for order_data in couriers_data]
    result = []
    with session_scope() as session:
        for courier in couriers:
            courier_db = get_courier_by_id(courier.id, session)
            if courier_db is None:
                result.append({
                    'id': courier.id,
                    'result': 'error',
                })
                logger.info(
                    'Courier with ID "%s" not found for deleting',
                    courier.id,
                )
            else:
                session.delete(courier_db)
                result.append({
                    'id': courier.id,
                    'result': 'ok',
                })
                logger.info(
                    'Courier with ID "%s" is removed',
                    courier.id,
                )
    return result
