# coding=utf-8
from typing import (
    List,
    Dict,
    Optional,
)

from common.sentry import get_logger
from db.models import (
    StockType,
    SpeedBonus,
    TransportType,
    DelayPenalty,
    Order,
    Courier,
)
from db.utils import session_scope
from sqlalchemy.orm import Session

logger = get_logger(__name__)


def stock_types() -> List[str]:
    """
    Get all of existing stock types
    """

    with session_scope() as session:
        all_stock_types = session.query(StockType). \
            with_entities(StockType.type). \
            all()
    return [stock_type for stock_type, in all_stock_types]


def get_stock_type(stock_type: str, session: Session) -> StockType:
    """
    Get stock type by name of its type
    """
    stock_type = session.query(StockType). \
        filter(StockType.type == stock_type).one()
    return stock_type


def transport_types() -> List[str]:
    """
    Get all of existing transport types
    """

    with session_scope() as session:
        all_transport_types = session.query(TransportType). \
            with_entities(TransportType.type). \
            all()
    return [transport_type for transport_type, in all_transport_types]


def get_transport_type(transport_type: str, session: Session) -> TransportType:
    """
    Get transport type by name of its type
    """
    transport_type = session.query(TransportType). \
        filter(TransportType.type == transport_type).one()
    return transport_type


def speed_bonuses() -> Dict[str, int]:
    """
    Get all of existing speed bonuses
    """

    with session_scope() as session:
        all_speed_bonuses = session.query(SpeedBonus). \
            with_entities(
            SpeedBonus.type,
            SpeedBonus.value,
        ).all()
    return {speed_bonus_type: speed_bonus_value for
            (speed_bonus_type, speed_bonus_value,) in all_speed_bonuses}


def get_speed_bonus_type(speed_bonus: str, session: Session) -> SpeedBonus:
    """
    Get speed bonus type by name of its type
    """
    speed_bonus = session.query(SpeedBonus). \
        filter(SpeedBonus.type == speed_bonus).one()
    return speed_bonus


def delay_penalties() -> Dict[str, int]:
    """
    Get all of existing delay penalties
    """

    with session_scope() as session:
        all_delay_penalties = session.query(DelayPenalty). \
            with_entities(
            DelayPenalty.type,
            DelayPenalty.value,
        ).all()
    return {delay_penalty_type: delay_penalty_value for
            (delay_penalty_type, delay_penalty_value,) in all_delay_penalties}


def get_delay_penalty_type(
        delay_penalty: str,
        session: Session,
) -> DelayPenalty:
    """
    Get delay penalty type by name of its type
    """
    delay_penalty = session.query(DelayPenalty). \
        filter(DelayPenalty.type == delay_penalty).one()
    return delay_penalty


def get_order_by_id(order_id: int, session: Session) -> Optional[Order]:
    """
    Get a order by its ID
    """
    logger.debug('Get order with ID "%s"', order_id)
    order = session.query(Order). \
        filter(Order.id == order_id).one_or_none()
    if order is not None:
        logger.debug('Received order "%s"', order.to_dict())
    return order


def get_courier_by_id(courier_id: int, session: Session) -> Optional[Courier]:
    """
    Get a courier by its ID
    """
    logger.debug('Get courier with ID "%s"', courier_id)
    courier = session.query(Courier). \
        filter(Courier.id == courier_id).one_or_none()
    if courier is not None:
        logger.debug('Received courier "%s"', courier.to_dict())
    return courier
