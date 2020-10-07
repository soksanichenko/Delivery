# coding=utf-8
from abc import ABC, abstractmethod


class BaseResolver(ABC):
    name = 'abstract_base_resolver'

    def __init__(self):
        if not hasattr(self, 'name'):
            raise AttributeError(
                'Class of resolver should have the attribute "name"'
            )

    @abstractmethod
    def initial_solution(self, points):
        pass

    @abstractmethod
    def insert_points(self, solution, points):
        pass

    @abstractmethod
    def improve_solution(self, solution):
        pass


class MockedResolved(BaseResolver):
    name = 'mocked_resolver'

    def initial_solution(self, points):
        return 'InitialedSolution'

    def insert_points(self, solution, points):
        return 'InsertedSolution'

    def improve_solution(self, solution):
        return 'ImprovedSolution'
