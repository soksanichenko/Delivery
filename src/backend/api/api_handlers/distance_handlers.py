# coding=utf-8
from functools import wraps
from math import sqrt
from typing import (
    Dict,
    List,
    Tuple,
)

from api.data_models import (
    Location,
)
from db.models import (
    Order as OrderDb,
    Courier as CourierDb,
    Stock as StockDb,
    Distance, obj_types,
)
from sqlalchemy import null
from sqlalchemy.orm import Session


def _calc_distance(location1: Location, location2: Location) -> float:
    """
    Mock function!
    Calculate the distance between two objects
    :param location1: coordinates of 1st object
    :param location2: coordinates of 2nd object
    :return: distance between 1st and 2nd objects
    """

    lon_diff = location1.lon - location2.lon
    lat_diff = location1.lat - location2.lat

    return sqrt(lon_diff ** 2 + lat_diff ** 2)


def validate_obj_type(f):
    """
    Decorator: validate type of a target object (a stock, an order, a courier)
    """

    @wraps(f)
    def decorated_function(obj_type, *args, **kwargs):
        if obj_type not in obj_types:
            raise ValueError(
                f'Passed wrong type of a target object "{obj_type}". '
                f'It doesn\'t belong to allowed types "{obj_types}"'
            )
        return f(obj_type, *args, **kwargs)

    decorated_function.__name__ = f.__name__
    return decorated_function


@validate_obj_type
def _calc_distances(
        obj_type: str,
        obj_id: int,
        obj_location: Location,
        session: Session,
        stocks: List[StockDb],
        orders: List[OrderDb],
        couriers: List[CourierDb],
) -> None:
    """
    Calculate and save distance from an object to all of existing objects in DB
    :param obj_id: ID of a target object (a stock, a courier, an order)
    :param obj_type: type of a target object
    :param obj_location: coordinates of a target object
    :param stocks: existing stocks
    :param orders: existing orders
    :param couriers: existing couriers
    :return: None
    """

    for courier in couriers:
        location2 = courier.location.to_dict()  # type: Dict[str, float]
        distance = _calc_distance(obj_location, Location(**location2))
        distance_to_create = Distance(
            obj_id_1=obj_id,
            obj_id_2=courier.id,
            obj_type_1=obj_type,
            obj_type_2='courier',
            distance=distance,
        )
        session.add(distance_to_create)
        session.flush()
    for order in orders:
        location2 = order.location.to_dict()  # type: Dict[str, float]
        distance = _calc_distance(obj_location, Location(**location2))
        distance_to_create = Distance(
            obj_id_1=obj_id,
            obj_id_2=order.id,
            obj_type_1=obj_type,
            obj_type_2='order',
            distance=distance,
        )
        session.add(distance_to_create)
        session.flush()
    for stock in stocks:
        location2 = stock.location.to_dict()  # type: Dict[str, float]
        distance = _calc_distance(obj_location, Location(**location2))
        distance_to_create = Distance(
            obj_id_1=obj_id,
            obj_id_2=stock.id,
            obj_type_1=obj_type,
            obj_type_2='stock',
            distance=distance,
        )
        session.add(distance_to_create)
        session.flush()


@validate_obj_type
def _select_objs_for_calculation(
        obj_type: str,
        obj_id: int,
        session: Session,
) -> Tuple[List[StockDb], List[OrderDb], List[CourierDb]]:
    """
    Select existing objects from DB for calculating distances
    :param obj_id: ID of a target object (a stock, a courier, an order)
    :param obj_type: type of a target object
    """
    stocks = session.query(StockDb)
    orders = session.query(OrderDb).filter(
        OrderDb.is_done == False,
    )
    couriers = session.query(CourierDb).filter(
        CourierDb.location != null(),
    )
    if obj_type == 'stock':
        couriers = couriers.all()
        stocks = stocks.filter(
            StockDb.id != obj_id,
        ).all()
        orders = orders.all()
    elif obj_type == 'order':
        couriers = couriers.all()
        stocks = stocks.all()
        orders = orders.filter(
            OrderDb.id != obj_id
        ).all()
    elif obj_type == 'courier':
        couriers = couriers.filter(
            CourierDb.id != obj_id
        ).all()
        stocks = stocks.all()
        orders = orders.all()

    return stocks, orders, couriers


@validate_obj_type
def calculate_distance(
        obj_type: str,
        obj_id: int,
        obj_location: Location,
        session: Session,
) -> None:
    """
    Calculate and save distance from an object to all of existing objects in DB
    :param obj_id: ID of a target object (a stock, a courier, an order)
    :param obj_type: type of a target object
    :param obj_location: coordinates of a target object
    :param session: object of current db session
    :return: None
    """

    stocks, orders, couriers = _select_objs_for_calculation(
        obj_type=obj_type,
        obj_id=obj_id,
        session=session,
    )
    _calc_distances(
        obj_type=obj_type,
        obj_id=obj_id,
        obj_location=obj_location,
        session=session,
        stocks=stocks,
        orders=orders,
        couriers=couriers,
    )
