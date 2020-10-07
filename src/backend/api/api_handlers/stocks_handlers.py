# coding=utf-8
from typing import (
    List,
    Dict,
    Optional,
)

from api.api_handlers.distance_handlers import calculate_distance
from api.data_models import (
    Stock,
    StockId,
    Location as LocationDataModel,
)
from api.exceptions import BadRequestFormatExceptioin
from common.sentry import get_logger
from db.db_requests import get_stock_type
from db.models import (
    Location,
    Break,
    Stock as StockDB,
    Hours,
)
from db.utils import session_scope
from resolver.main import insert_to_queue
from sqlalchemy.orm import Session

logger = get_logger(__name__)


def get_stocks():
    with session_scope() as session:
        stocks = session.query(StockDB).all()  # type: List[StockDB]

        return [stock.to_dict() for stock in stocks]


def _get_stock_by_id(stock_id: int, session: Session) -> Optional[StockDB]:
    """
    Get a stock by its ID
    """
    logger.debug('Get stock with ID "%s"', stock_id)
    stock = session.query(StockDB). \
        filter(StockDB.id == stock_id).one_or_none()
    if stock is not None:
        logger.debug('Received stock "%s"', stock.to_dict())
    return stock


def _update_stock(stock: Stock, session: Session) -> bool:
    """
    Update an existing stock in DB
    """
    stock_db = _get_stock_by_id(stock.id, session)
    if stock_db is None:
        logger.info('Stock with ID "%s" not found for updating', stock.id)
        return False
    stock_db_dict = stock_db.to_dict()
    logger.debug('Stock is taken from DB "%s"', stock_db_dict)
    stock_dict = stock.dict()
    logger.debug('Stock is taken from data model "%s"', stock_dict)
    if stock_db_dict == stock_dict:
        logger.info(
            'Stock "%s" is equal to stock "%s". Nothing to update',
            stock_db_dict,
            stock_dict,
        )
        return True
    stock_db.id = stock.id
    stock_db.geozone_id = stock.geozone_id
    stock_db.assembly_time = stock.assembly_time
    stock_type = get_stock_type(stock.type, session)
    stock_db.type_id = stock_type.id
    stock_db.hours.start = stock.hours.start
    stock_db.hours.end = stock.hours.end
    is_location_changed = False
    if stock_db.location.latitude != stock.location.lat or \
            stock_db.location.longtitude != stock.location.lon:
        stock_db.location.latitude = stock.location.lat
        stock_db.location.longtitude = stock.location.lon
        is_location_changed = True
    for stock_break in stock_db.breaks:
        logger.info('Remove old stock break "%s"', stock_break.to_dict())
        session.delete(stock_break)
    breaks_to_create = [
        Break(
            start=stock_break.start,
            end=stock_break.end,
        ) for stock_break in stock.breaks
    ]
    session.add(*breaks_to_create)
    stock_db.breaks = breaks_to_create
    session.flush()
    if is_location_changed:
        calculate_distance(
            'stock',
            stock_db.id,
            LocationDataModel(**stock_db.location.to_dict()),
            session,
        )
        insert_to_queue(
            'stock',
            stock_db.id,
            session,
        )
    return True


def save_stocks(stocks_data):
    if not isinstance(stocks_data, list):
        raise BadRequestFormatExceptioin(
            message=f'Type of request for adding/updating stocks should be '
                    f'"list", but received "{type(stocks_data)}"'
        )
    stocks = [Stock(**stock_data) for stock_data in stocks_data]
    with session_scope() as session:
        for stock in stocks:
            if _update_stock(stock, session):
                continue
            location_to_create = Location(
                latitude=stock.location.lat,
                longtitude=stock.location.lon,
            )
            session.add(location_to_create)
            breaks_to_create = [
                Break(
                    start=stock_break.start,
                    end=stock_break.end,
                ) for stock_break in stock.breaks
            ]
            session.add(*breaks_to_create)
            stock_type = get_stock_type(stock.type, session)
            stock_hours_to_create = Hours(
                start=stock.hours.start,
                end=stock.hours.end,
            )
            session.add(stock_hours_to_create)
            stock_to_create = StockDB(
                id=stock.id,
                geozone_id=stock.geozone_id,
                assembly_time=stock.assembly_time,
                type=stock_type,
                hours_id=stock_hours_to_create.id,
                hours=stock_hours_to_create,
                location_id=location_to_create.id,
                location=location_to_create,
                breaks=breaks_to_create,
            )
            session.add(stock_to_create)
            session.flush()
            calculate_distance(
                'stock',
                stock_to_create.id,
                LocationDataModel(**stock_to_create.location.to_dict()),
                session,
            )
            insert_to_queue(
                'stock',
                stock_to_create.id,
                session,
            )
    return [stock.dict() for stock in stocks]


def remove_stocks(stocks_data: List[Dict[str, int]]):
    if not isinstance(stocks_data, list):
        raise BadRequestFormatExceptioin(
            message=f'Type of request for deleting stocks should be "list",'
                    f'but received "{type(stocks_data)}"'
        )
    stocks = [StockId(**stock_data) for stock_data in stocks_data]
    result = []
    with session_scope() as session:
        for stock in stocks:
            stock_db = _get_stock_by_id(stock.id, session)
            if stock_db is None:
                result.append({
                    'id': stock.id,
                    'result': 'error',
                })
                logger.info(
                    'Stock with ID "%s" not found for deleting',
                    stock.id,
                )
            else:
                session.delete(stock_db)
                result.append({
                    'id': stock.id,
                    'result': 'ok',
                })
                logger.info(
                    'Stock with ID "%s" is removed',
                    stock.id,
                )
    return result
