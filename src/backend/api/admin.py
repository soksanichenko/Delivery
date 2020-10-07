# coding=utf-8
from api.utils.http_response_helpers import error_result
from api.utils.jwt_token_helpers import jwt_required
from db.models import (
    StockType,
    SpeedBonus,
    TransportType,
    DelayPenalty,
)
from db.utils import session_scope
from flask import Flask
from flask_admin import (
    Admin,
    AdminIndexView,
    expose,
)
from flask_admin.contrib.sqla import ModelView


class CustomAdminIndexView(AdminIndexView):

    @expose()
    @jwt_required
    @error_result
    def index(self):
        return super().index()


def create_flask_admin(flask_app: Flask) -> None:
    admin = Admin(
        flask_app, template_mode='bootstrap3',
        index_view=CustomAdminIndexView(),
    )
    with session_scope() as session:
        admin.add_view(ModelView(StockType, session))
        admin.add_view(ModelView(SpeedBonus, session))
        admin.add_view(ModelView(TransportType, session))
        admin.add_view(ModelView(DelayPenalty, session))
