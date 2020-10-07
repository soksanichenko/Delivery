# coding=utf-8

from datetime import time
from typing import List, Union, Optional, Any, Dict

from common.sentry import get_logger
from db.db_requests import (
    stock_types,
    speed_bonuses,
    delay_penalties,
    transport_types,
)
from pydantic import (
    BaseModel,
    validator,
    conint,
    root_validator,
)

MAX_C_SIGNED_INT = 32767
logger = get_logger(__name__)


class Location(BaseModel):
    lat: float
    lon: float

    @classmethod
    @validator('lat')
    def validate_lat(cls, value: float):
        assert -90 <= value <= 90, \
            f'Value of latitude should be between "-90" and "90"'
        return value

    @classmethod
    @validator('lon')
    def validate_lon(cls, value: float):
        assert -180 <= value <= 180, \
            f'Value of longitude should be between "-180" and "180"'
        return value


class Hours(BaseModel):
    start: time
    end: time

    @root_validator
    def validate_hours(cls, values: Dict[str, Any]):
        start_time = values['start']
        end_time = values['end']
        start = time.strftime(start_time, '%H:%M')
        end = time.strftime(end_time, '%H:%M')

        assert start_time < end_time, \
            f'Start time "{start}" should be lesser than end time "{end}"'
        return values

    def dict(self, **kwargs):
        return {
            'start': time.strftime(self.start, '%H:%M'),
            'end': time.strftime(self.end, '%H:%M'),
        }


class Break(Hours):
    pass


class StockId(BaseModel):
    id: conint(ge=1, le=MAX_C_SIGNED_INT)


class Stock(StockId):
    location: Location
    geozone_id: conint(ge=1, le=MAX_C_SIGNED_INT)
    hours: Hours
    breaks: List[Break]
    assembly_time: conint(ge=1, le=MAX_C_SIGNED_INT)
    type: str

    @validator('type')
    def validate_stock_type(cls, value: str):
        existing_stock_types = stock_types()
        assert value in existing_stock_types, \
            f'Stock type "{value}" doesn\'t belong to ' \
            f'existing types {", ".join(existing_stock_types)}'
        return value


class OrderId(BaseModel):
    id: conint(ge=1, le=MAX_C_SIGNED_INT)


class Order(OrderId):
    location: Location
    geozone_id: conint(ge=1, le=MAX_C_SIGNED_INT)
    weight: conint(ge=1, le=MAX_C_SIGNED_INT)
    price: conint(ge=1, le=MAX_C_SIGNED_INT)
    delivery_time: Optional[Hours]
    speed_bonus: Union[
        conint(ge=1, le=MAX_C_SIGNED_INT),
        str,
    ]
    delay_penalty: Union[
        conint(ge=1, le=MAX_C_SIGNED_INT),
        str,
    ]
    is_urgent: Optional[bool]
    issue_time: conint(ge=1, le=MAX_C_SIGNED_INT)
    outsource_price: Optional[conint(ge=1, le=MAX_C_SIGNED_INT)]
    courier_id: Optional[conint(ge=1, le=MAX_C_SIGNED_INT)]

    @validator('speed_bonus')
    def validate_speed_bonus(cls, value: Union[str, int]):
        if isinstance(value, str):
            existing_speed_bonuses = list(speed_bonuses().keys())
            assert value in existing_speed_bonuses, \
                f'Speed bonus type "{value}" doesn\'t belong to ' \
                f'existing types {", ".join(existing_speed_bonuses)}'
        return value

    @validator('delay_penalty')
    def validate_delay_penalty(cls, value: Union[str, int]):
        if isinstance(value, str):
            existing_delay_penalties = list(delay_penalties().keys())
            assert value in existing_delay_penalties, \
                f'Delay penalty type "{value}" doesn\'t belong to ' \
                f'existing types {", ".join(existing_delay_penalties)}'
        return value

    @root_validator
    def validate_delivery_time(cls, values: Dict[str, Any]):
        logger.debug('Validated values: "%s"', values)
        assert not (
                (values['is_urgent'] is not None) ^
                (values['delivery_time'] is None)
        ), 'You can pass just one parameter out of two: ' \
           '"is_urgent" and "delivery_time"'

        return values


class CourierId(BaseModel):
    id: conint(ge=1, le=MAX_C_SIGNED_INT)


class Courier(CourierId):
    location: Optional[Location]
    transport_type: str
    max_capacity: conint(ge=1, le=MAX_C_SIGNED_INT)
    max_price: conint(ge=1, le=MAX_C_SIGNED_INT)
    avg_speed: conint(ge=0, le=MAX_C_SIGNED_INT)
    hours: Hours
    breaks: List[Break]
    geozone_id: conint(ge=1, le=MAX_C_SIGNED_INT)
    hour_price: conint(ge=1, le=MAX_C_SIGNED_INT)
    km_price: conint(ge=1, le=MAX_C_SIGNED_INT)
    start_price: conint(ge=1, le=MAX_C_SIGNED_INT)
    order_id: Optional[conint(ge=1, le=MAX_C_SIGNED_INT)]

    @validator('transport_type')
    def validate_transport_type(cls, value: str):
        existing_transport_types = transport_types()
        assert value in existing_transport_types, \
            f'Transport type "{value}" doesn\'t belong to ' \
            f'existing types {", ".join(existing_transport_types)}'
        return value
