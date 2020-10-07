# coding=utf-8
import fcntl
import os
import pickle
import threading
from time import sleep
from typing import (
    Tuple,
    List,
    Dict,
    Any,
)

from api.api_handlers.distance_handlers import validate_obj_type
from db.models import (
    Solution,
    Queue,
    Stock,
    Order,
    Courier,
)
from db.utils import session_scope
from resolver.resolvers import (
    BaseResolver,
    MockedResolved,
)
from sqlalchemy.orm import Session

RESOLVERS = [
    MockedResolved(),
]


def _get_points(
        objects: List[Tuple[int, str]],
        session: Session,
) -> List[Dict[str, Any]]:
    output_objects = []
    for obj_id, obj_type in objects:
        if obj_type == 'stock':
            stock = session.query(Stock).filter(
                Stock.id == obj_id
            ).first()
            output_objects.append(stock.to_dict())
        elif obj_type == 'order':
            order = session.query(Order).filter(
                Order.id == obj_id
            ).first()
            output_objects.append(order.to_dict())
        elif obj_type == 'courier':
            courier = session.query(Courier).filter(
                Courier.id == obj_id
            ).first()
            output_objects.append(courier.to_dict())
    return output_objects


@validate_obj_type
def insert_to_queue(obj_type: str, obj_id: int, session: Session) -> None:
    """
    Insert an object to queue for a resolver
    :param obj_type: type of object (a stock, an order or a courier)
    :param obj_id: ID of object
    :param session: object of current db session
    :return: None
    """

    queue_to_create = Queue(
        obj_id=obj_id,
        obj_type=obj_type,
    )
    session.add(queue_to_create)
    session.flush()


def _run_resolver(resolver, lock_file, last_solution, points, session):
    with open(lock_file, 'a+') as fd:
        fcntl.flock(fd.fileno(), fcntl.LOCK_EX)
        inserted_solution = resolver.insert_points(
            last_solution,
            points,
        )
        solution_to_create = Solution(
            solution=pickle.dumps(inserted_solution),
            resolver_name=resolver.name,
            generated_action='insert',
        )
        session.add(solution_to_create)
        improved_solution = resolver.improve_solution(last_solution)
        solution_to_create = Solution(
            solution=pickle.dumps(improved_solution),
            resolver_name=resolver.name,
            generated_action='improvement',
        )
        session.add(solution_to_create)


def do_resolve_cycle():
    with session_scope() as session:
        queue_all = session.query(Queue).all()
        queue = [queue.to_tuple() for queue in queue_all]
        if not queue:
            # do nothing if queue is empty
            return
        points = _get_points(queue, session)
        last_solution = session.query(Solution).order_by(
            Solution.timestamp.desc()
        ).first()  # type: Solution
        if last_solution is None:
            first_resolver = RESOLVERS[0]  # type: BaseResolver
            last_solution = first_resolver.initial_solution(points)
            solution_to_create = Solution(
                solution=pickle.dumps(last_solution),
                resolver_name=first_resolver.name,
                generated_action='initial',
            )
            session.add(solution_to_create)
        else:
            last_solution = pickle.loads(last_solution.solution)
        for resolver in RESOLVERS:
            lock_file = os.path.join('/tmp', f'{resolver.name}.lock')
            solver_thread = threading.Thread(
                target=_run_resolver,
                name=resolver.name,
                args=(resolver, lock_file, last_solution, points, session)
            )
            solver_thread.start()
        else:
            for q in queue_all:
                session.delete(q)
            session.flush()


if __name__ == '__main__':
    while True:
        do_resolve_cycle()
        sleep(1)
