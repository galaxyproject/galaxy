from abc import (
    ABC,
    abstractmethod,
)
from uuid import uuid4

import pytest
from sqlalchemy import UniqueConstraint


class AbstractBaseTest(ABC):
    @pytest.fixture
    def cls_(self):
        """
        Return class under test.
        Assumptions: if the class under test is Foo, then the class grouping
        the tests should be a subclass of BaseTest, named TestFoo.
        """
        prefix = len("Test")
        class_name = self.__class__.__name__[prefix:]
        return getattr(self.get_model(), class_name)

    @abstractmethod
    def get_model(self):
        pass


def has_unique_constraint(table, fields):
    for constraint in table.constraints:
        if isinstance(constraint, UniqueConstraint):
            col_names = {c.name for c in constraint.columns}
            if set(fields) == col_names:
                return True


def has_index(table, fields):
    for index in table.indexes:
        col_names = {c.name for c in index.columns}
        if set(fields) == col_names:
            return True


def collection_consists_of_objects(collection, *objects):
    """
    Returns True iff list(collection) == list(objects), where object equality is determined
    by primary key equality: object1.id == object2.id.
    """
    if len(collection) != len(objects):  # False if lengths are different
        return False
    if not collection:  # True if both are empty
        return True

    # Sort, then compare each member by its 'id' attribute, which must be its primary key.
    collection.sort(key=lambda item: item.id)
    objects_l = list(objects)
    objects_l.sort(key=lambda item: item.id)

    for item1, item2 in zip(collection, objects_l):
        if item1.id is None or item2.id is None or item1.id != item2.id:
            return False
    return True


def get_unique_value():
    """Generate unique values to accommodate unique constraints."""
    return uuid4().hex
