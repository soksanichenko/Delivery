# coding=utf-8
from datetime import datetime
from typing import (
    Dict,
    Any,
    Union,
    Optional, Tuple, )

from sqlalchemy import (
    Column,
    Integer,
    Float,
    Table,
    Time,
    ForeignKey,
    Boolean,
    String,
    Enum,
    DateTime,
    PickleType,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()
obj_types = ('stock', 'courier', 'order')
generated_actions = ('initial', 'insert', 'improvement')


class Break(Base):
    __tablename__ = 'breaks'

    id = Column(Integer, nullable=False, primary_key=True)
    start = Column(Time, nullable=False)
    end = Column(Time, nullable=False)

    def to_dict(self) -> Dict[str, str]:
        return {
            'start': self.start.strftime('%H:%M'),
            'end': self.end.strftime('%H:%M'),
        }


class Hours(Base):
    __tablename__ = 'hours'

    id = Column(Integer, nullable=False, primary_key=True)
    start = Column(Time, nullable=False)
    end = Column(Time, nullable=False)

    def to_dict(self) -> Dict[str, str]:
        return {
            'start': self.start.strftime('%H:%M'),
            'end': self.end.strftime('%H:%M'),
        }


class Location(Base):
    __tablename__ = 'locations'

    id = Column(Integer, nullable=False, primary_key=True)
    latitude = Column(Float, nullable=True)
    longtitude = Column(Float, nullable=True)

    def to_dict(self) -> Dict[str, float]:
        return {
            'lat': self.latitude,
            'lon': self.longtitude,
        }


stocks_breaks = Table(
    'stocks_breaks',
    Base.metadata,
    Column('stock_id', Integer, ForeignKey('stocks.id', ondelete='CASCADE')),
    Column('break_id', Integer, ForeignKey('breaks.id', ondelete='CASCADE'))
)


class StockType(Base):
    __tablename__ = 'stock_types'

    id = Column(Integer, nullable=False, primary_key=True)
    type = Column(String, nullable=False)

    def to_dict(self) -> Dict[str, str]:
        return {
            'type': self.type
        }


class Stock(Base):
    __tablename__ = 'stocks'

    id = Column(Integer, nullable=False, primary_key=True)
    geozone_id = Column(Integer, nullable=False)
    assembly_time = Column(Integer, nullable=False)
    type_id = Column(Integer, ForeignKey('stock_types.id'))
    type = relationship('StockType')
    hours_id = Column(
        Integer,
        ForeignKey(
            'hours.id',
            ondelete='CASCADE',
        ),
    )
    hours = relationship('Hours')
    location_id = Column(
        Integer,
        ForeignKey(
            'locations.id',
            ondelete='CASCADE',
        ),
    )
    location = relationship('Location')
    breaks = relationship(
        'Break',
        secondary=stocks_breaks,
        passive_deletes=True,
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'geozone_id': self.geozone_id,
            'assembly_time': self.assembly_time,
            'type': self.type.to_dict()['type'],
            'hours': self.hours.to_dict(),
            'location': self.location.to_dict(),
            'breaks': [_break.to_dict() for _break in self.breaks],
        }


class SpeedBonus(Base):
    __tablename__ = 'speed_bonuses'

    id = Column(Integer, nullable=False, primary_key=True)
    type = Column(String, nullable=False)
    value = Column(Integer, nullable=False)

    def to_dict(self) -> Dict[str, int]:
        return {
            'type': self.type,
            'value': self.value,
        }


class DelayPenalty(Base):
    __tablename__ = 'delay_penalties'

    id = Column(Integer, nullable=False, primary_key=True)
    type = Column(String, nullable=False)
    value = Column(Integer, nullable=False)

    def to_dict(self) -> Dict[str, int]:
        return {
            'type': self.type,
            'value': self.value,
        }


class Order(Base):
    __tablename__ = 'orders'

    id = Column(Integer, nullable=False, primary_key=True)
    location_id = Column(
        Integer,
        ForeignKey(
            'locations.id',
            ondelete='CASCADE',
        ),
    )
    location = relationship('Location')
    weight = Column(Integer, nullable=False)
    price = Column(Integer, nullable=False)
    geozone_id = Column(Integer, nullable=False)
    delivery_time_id = Column(
        Integer,
        ForeignKey(
            'hours.id',
            ondelete='CASCADE'
        ),
        nullable=True,
    )
    delivery_time = relationship('Hours')
    speed_bonus_id = Column(
        Integer,
        ForeignKey('speed_bonuses.id'),
        nullable=True
    )
    speed_bonus = relationship('SpeedBonus')
    speed_bonus_value = Column(Integer, nullable=True)
    delay_penalty_id = Column(Integer, ForeignKey('delay_penalties.id'))
    delay_penalty = relationship('DelayPenalty')
    delay_penalty_value = Column(Integer, nullable=True)
    is_urgent = Column(Boolean, nullable=True)
    issue_time = Column(Integer, nullable=False)
    outsource_price = Column(Integer, nullable=True)
    courier_id = Column(Integer, ForeignKey('couriers.id'), nullable=True)
    courier = relationship('Courier', back_populates='order')
    is_done = Column(Boolean, nullable=False, default=False)

    def _get_speed_bonus(self) -> Union[int, str]:
        if self.speed_bonus_value is None:
            return self.speed_bonus.to_dict()['type']
        else:
            return self.speed_bonus_value

    def _get_delay_penalty(self) -> Union[int, str]:
        if self.delay_penalty_value is None:
            return self.delay_penalty.to_dict()['type']
        else:
            return self.delay_penalty_value

    def _get_delivery_time(self) -> Optional[Dict[str, str]]:
        if self.delivery_time is not None:
            return self.delivery_time.to_dict()

    def to_dict(self) -> Dict[str, Any]:

        return {
            'id': self.id,
            'location': self.location.to_dict(),
            'weight': self.weight,
            'price': self.price,
            'geozone_id': self.geozone_id,
            'delivery_time': self._get_delivery_time(),
            'speed_bonus': self._get_speed_bonus(),
            'delay_penalty': self._get_delay_penalty(),
            'is_urgent': self.is_urgent,
            'issue_time': self.issue_time,
            'outsource_price': self.outsource_price,
            'courier_id': self.courier_id,
        }


class TransportType(Base):
    __tablename__ = 'transport_types'

    id = Column(Integer, nullable=False, primary_key=True)
    type = Column(String, nullable=False)

    def to_dict(self) -> Dict[str, str]:
        return {
            'type': self.type
        }


couriers_breaks = Table(
    'couriers_breaks',
    Base.metadata,
    Column(
        'courier_id',
        Integer,
        ForeignKey(
            'couriers.id',
            ondelete='CASCADE',
        )
    ),
    Column('break_id', Integer, ForeignKey('breaks.id', ondelete='CASCADE'))
)


class Courier(Base):
    __tablename__ = 'couriers'

    id = Column(Integer, nullable=False, primary_key=True)
    location_id = Column(
        Integer,
        ForeignKey(
            'locations.id',
            ondelete='CASCADE',
        ),
        nullable=True,
    )
    location = relationship('Location')
    transport_type_id = Column(Integer, ForeignKey('transport_types.id'))
    transport_type = relationship('TransportType')
    max_capacity = Column(Integer, nullable=False)
    max_price = Column(Integer, nullable=False)
    avg_speed = Column(Integer, nullable=False)
    hours_id = Column(
        Integer,
        ForeignKey(
            'hours.id',
            ondelete='CASCADE',
        ),
    )
    hours = relationship('Hours')
    breaks = relationship(
        'Break',
        secondary=couriers_breaks,
        passive_deletes=True,
    )
    geozone_id = Column(Integer, nullable=False)
    hour_price = Column(Integer, nullable=False)
    km_price = Column(Integer, nullable=False)
    start_price = Column(Integer, nullable=False)
    order = relationship('Order', back_populates='courier', uselist=False)
    # TODO: this field only for mock state, when we don't have routes resolver
    # for a courier and can't get a previous order of a courier.
    # Remove it from model and db then you will have the resolver
    previous_order_id = Column(Integer, nullable=True)

    def _get_location(self) -> Optional[Dict[str, float]]:
        if self.location is not None:
            return self.location.to_dict()

    def get_order_id(self) -> Optional[int]:
        if self.order is not None:
            return self.order.id

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'location': self._get_location(),
            'transport_type': self.transport_type.to_dict()['type'],
            'max_capacity': self.max_capacity,
            'max_price': self.max_price,
            'avg_speed': self.avg_speed,
            'hours': self.hours.to_dict(),
            'breaks': [_break.to_dict() for _break in self.breaks],
            'geozone_id': self.geozone_id,
            'hour_price': self.hour_price,
            'km_price': self.km_price,
            'start_price': self.start_price,
            'current_order': self.get_order_id(),
        }


class Distance(Base):
    __tablename__ = 'distances'

    id = Column(Integer, nullable=False, primary_key=True)
    obj_id_1 = Column(Integer, nullable=False)
    obj_id_2 = Column(Integer, nullable=False)
    obj_type_1 = Column(Enum(*obj_types, name='obj_type_1'), nullable=False)
    obj_type_2 = Column(Enum(*obj_types, name='obj_type_2'), nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    distance = Column(Float, nullable=False)


class Solution(Base):
    __tablename__ = 'solutions'

    id = Column(Integer, nullable=False, primary_key=True)
    solution = Column(PickleType, nullable=False)
    resolver_name = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    generated_action = Column(Enum(
        *generated_actions, name='generated_action',
    ), nullable=False)


class Queue(Base):
    __tablename__ = 'queue'

    id = Column(Integer, nullable=False, primary_key=True)
    obj_id = Column(Integer, nullable=False)
    obj_type = Column(Enum(*obj_types, name='object_type'), nullable=False)

    def to_tuple(self) -> Tuple[int, str]:
        return self.obj_id, self.obj_type
