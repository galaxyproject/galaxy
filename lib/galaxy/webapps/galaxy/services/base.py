from typing import (
    cast,
    List,
    Optional,
)

from celery.result import AsyncResult

from galaxy.exceptions import (
    AuthenticationRequired,
    ConfigDoesNotAllowException,
)
from galaxy.managers.base import (
    decode_with_security,
    encode_with_security,
    get_class,
    get_object,
    SortableManager,
)
from galaxy.managers.context import ProvidesUserContext
from galaxy.model import User
from galaxy.schema.fields import EncodedDatabaseIdField
from galaxy.schema.schema import AsyncTaskResultSummary
from galaxy.security.idencoding import IdEncodingHelper


def ensure_celery_tasks_enabled(config):
    if not config.enable_celery_tasks:
        raise ConfigDoesNotAllowException(
            "This operation requires asynchronous tasks to be enabled on the Galaxy server and they are not, please contact the server admin."
        )


class ServiceBase:
    """Base class with common logic and utils reused by other services.

    A service class:
     - Provides top level operations (`Index`, `Show`, `Delete`...) that are usually
       consumed directly by the API controllers or other services.
     - Uses a combination of managers to perform the operations and
       avoids accessing the database layer directly.
     - Can speak 'pydantic' and has rich type annotations to be explicit about
       the required parameters and outputs of each operation.
    """

    def __init__(self, security: IdEncodingHelper):
        self.security = security

    def decode_id(self, id: EncodedDatabaseIdField) -> int:
        """Decodes a previously encoded database ID."""
        return decode_with_security(self.security, id)

    def encode_id(self, id: int) -> EncodedDatabaseIdField:
        """Encodes a raw database ID."""
        return encode_with_security(self.security, id)

    def decode_ids(self, ids: List[EncodedDatabaseIdField]) -> List[int]:
        """
        Decodes all encoded IDs in the given list.
        """
        return [self.decode_id(id) for id in ids]

    def encode_all_ids(self, rval, recursive: bool = False):
        """
        Encodes all integer values in the dict rval whose keys are 'id' or end with '_id'

        It might be useful to turn this in to a decorator
        """
        return self.security.encode_all_ids(rval, recursive=recursive)

    def build_order_by(self, manager: SortableManager, order_by_query: Optional[str] = None):
        """Returns an ORM compatible order_by clause using the order attribute and the given manager.

        The manager has to implement the `parse_order_by` function to support all the sortable model attributes."""
        ORDER_BY_SEP_CHAR = ","
        if order_by_query and ORDER_BY_SEP_CHAR in order_by_query:
            return [manager.parse_order_by(o) for o in order_by_query.split(ORDER_BY_SEP_CHAR)]
        return manager.parse_order_by(order_by_query)

    def get_class(self, class_name):
        """
        Returns the class object that a string denotes. Without this method, we'd have to do eval(<class_name>).
        """
        return get_class(class_name)

    def get_object(self, trans, id, class_name, check_ownership=False, check_accessible=False, deleted=None):
        """
        Convenience method to get a model object with the specified checks.
        """
        return get_object(
            trans, id, class_name, check_ownership=check_ownership, check_accessible=check_accessible, deleted=deleted
        )

    def check_user_is_authenticated(self, trans: ProvidesUserContext):
        """Raises an exception if the request is anonymous."""
        if trans.anonymous:
            raise AuthenticationRequired("API authentication required for this request")

    def get_authenticated_user(self, trans: ProvidesUserContext) -> User:
        """Gets the authenticated user and prevents access from anonymous users."""
        self.check_user_is_authenticated(trans)
        return cast(User, trans.user)


def async_task_summary(async_result: AsyncResult) -> AsyncTaskResultSummary:
    name = None
    try:
        name = async_result.name
    except AttributeError:
        # if backend is disabled, we won't have this
        pass
    queue = None
    try:
        queue = async_result.queue
    except AttributeError:
        # if backend is disabled, we won't have this
        pass

    return AsyncTaskResultSummary(
        id=async_result.id,
        ignored=async_result.ignored,
        name=name,
        queue=queue,
    )
