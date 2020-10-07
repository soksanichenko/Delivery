# coding=utf-8
from typing import Optional, Dict

from api.data_models import CourierId
from api.exceptions import BadRequestFormatExceptioin
from db.db_requests import get_courier_by_id
from db.models import Order, Courier
from db.utils import session_scope
from sqlalchemy import null
from sqlalchemy.orm import Session


def _get_next_free_order(session: Session) -> Optional[Order]:
    """
    Mock function!
    """

    free_order = session.query(Order).filter(
        Order.courier_id == null()
    ).first()
    return free_order


def _get_previous_order_of_courier(
        courier: Courier,
        session: Session,
) -> Optional[Order]:
    """
    Mock function!
    """

    previous_order = session.query(Order).filter(
        Order.id == courier.previous_order_id,
    ).first()

    return previous_order


def action_on_point(courier_data: Dict[str, int], action: str):
    if not isinstance(courier_data, dict):
        raise BadRequestFormatExceptioin(
            message=f'Type of request for updating a courier should be "dict",'
                    f'but received "{type(courier_data)}"'
        )
    courier = CourierId(**courier_data)
    with session_scope() as session:
        courier_db = get_courier_by_id(courier.id, session)
        if action in ('next', 'go',):
            next_order = _get_next_free_order(session)
            old_order_id = courier_db.get_order_id()
            if next_order is not None and action == 'go':
                courier_db.previous_order_id = old_order_id
                courier_db.order = next_order
                session.flush()

            return {
                'old_id': old_order_id,
                'new_id': None if next_order is None else next_order.id,
            }
        elif action == 'ungo':
            cancelled_order_id = courier_db.get_order_id()
            previous_order = _get_previous_order_of_courier(
                courier_db,
                session,
            )
            courier_db.previous_order_id = null()
            courier_db.order = previous_order
            session.flush()
            return {
                'cancelled_id': cancelled_order_id,
                'current_id': courier_db.get_order_id(),
            }
