"""This module defines Galaxy's custom exceptions.

A Galaxy exception is an exception that extends :class:`MessageException` which
defines an HTTP status code (represented by the `status_code` attribute) and a
default error message.

New exceptions should be defined by adding an entry to `error_codes.json` in this
directory to define a default error message and a Galaxy "error code". A concrete
Python class should be added in this file defining an HTTP status code (as
`status_code`) and error code (`error_code`) object loaded dynamically from
`error_codes.json`.

Reflecting Galaxy's origins as a web application, these exceptions tend to be a
bit web-oriented. However this module is a dependency of modules and tools that
have nothing to do with the web - keep this in mind when defining exception names
and messages.
"""

from typing import Optional

from .error_codes import (
    error_codes_by_name,
    ErrorCode,
)


class MessageException(Exception):
    """Most generic Galaxy exception - indicates merely that some exceptional condition happened."""

    # status code to be set when used with API.
    status_code: int = 400
    # Error code information embedded into API json responses.
    err_code: ErrorCode = error_codes_by_name["UNKNOWN"]

    def __init__(self, err_msg: Optional[str] = None, type="info", **extra_error_info):
        self.err_msg = err_msg or self.err_code.default_error_message
        self.type = type
        self.extra_error_info = extra_error_info

    @staticmethod
    def from_code(status_code, message):
        exception_class = MessageException
        if status_code == 404:
            exception_class = ObjectNotFound
        elif status_code / 100 == 5:
            exception_class = InternalServerError
        return exception_class(message)

    def __str__(self):
        return self.err_msg


class ItemDeletionException(MessageException):
    pass


class ObjectInvalid(Exception):
    """Accessed object store ID is invalid"""


# Please keep the exceptions ordered by status code


class AcceptedRetryLater(MessageException):
    status_code = 202
    err_code = error_codes_by_name["ACCEPTED_RETRY_LATER"]
    retry_after: int

    def __init__(self, msg: Optional[str] = None, retry_after=60):
        super().__init__(msg)
        self.retry_after = retry_after


class NoContentException(MessageException):
    status_code = 204
    err_code = error_codes_by_name["NO_CONTENT_GENERIC"]


class ActionInputError(MessageException):
    status_code = 400
    err_code = error_codes_by_name["USER_REQUEST_INVALID_PARAMETER"]

    def __init__(self, err_msg, type="error"):
        super().__init__(err_msg, type)


class DuplicatedSlugException(MessageException):
    status_code = 400
    err_code = error_codes_by_name["USER_SLUG_DUPLICATE"]


class DuplicatedIdentifierException(MessageException):
    status_code = 400
    err_code = error_codes_by_name["USER_IDENTIFIER_DUPLICATE"]


class ObjectAttributeInvalidException(MessageException):
    status_code = 400
    err_code = error_codes_by_name["USER_OBJECT_ATTRIBUTE_INVALID"]


class ObjectAttributeMissingException(MessageException):
    status_code = 400
    err_code = error_codes_by_name["USER_OBJECT_ATTRIBUTE_MISSING"]


class MalformedId(MessageException):
    status_code = 400
    err_code = error_codes_by_name["MALFORMED_ID"]


class UserInvalidRunAsException(MessageException):
    status_code = 400
    err_code = error_codes_by_name["USER_INVALID_RUN_AS"]


class MalformedContents(MessageException):
    status_code = 400
    err_code = error_codes_by_name["MALFORMED_CONTENTS"]


class UnknownContentsType(MessageException):
    status_code = 400
    err_code = error_codes_by_name["UNKNOWN_CONTENTS_TYPE"]


class RequestParameterMissingException(MessageException):
    status_code = 400
    err_code = error_codes_by_name["USER_REQUEST_MISSING_PARAMETER"]


class ToolMetaParameterException(MessageException):
    status_code = 400
    err_code = error_codes_by_name["USER_TOOL_META_PARAMETER_PROBLEM"]


class ToolMissingException(MessageException):
    status_code = 400
    err_code = error_codes_by_name["USER_TOOL_MISSING_PROBLEM"]

    def __init__(self, err_msg: Optional[str] = None, type="info", tool_id=None, **extra_error_info):
        super().__init__(err_msg, type, **extra_error_info)
        self.tool_id = tool_id


class RequestParameterInvalidException(MessageException):
    status_code = 400
    err_code = error_codes_by_name["USER_REQUEST_INVALID_PARAMETER"]


class ToolInputsNotReadyException(MessageException):
    status_code = 400
    error_code = error_codes_by_name["TOOL_INPUTS_NOT_READY"]


class ToolInputsNotOKException(MessageException):
    def __init__(self, err_msg: Optional[str] = None, type="info", *, src: str, id: int, **extra_error_info):
        super().__init__(err_msg, type, **extra_error_info)
        self.src = src
        self.id = id

    status_code = 400
    error_code = error_codes_by_name["TOOL_INPUTS_NOT_OK"]


class RealUserRequiredException(MessageException):
    status_code = 400
    error_code = error_codes_by_name["REAL_USER_REQUIRED"]


class AuthenticationFailed(MessageException):
    status_code = 401
    err_code = error_codes_by_name["USER_AUTHENTICATION_FAILED"]


class AuthenticationRequired(MessageException):
    status_code = 403
    # TODO: as 401 and send WWW-Authenticate: ???
    err_code = error_codes_by_name["USER_NO_API_KEY"]


class ItemAccessibilityException(MessageException):
    status_code = 403
    err_code = error_codes_by_name["USER_CANNOT_ACCESS_ITEM"]


class ItemOwnershipException(MessageException):
    status_code = 403
    err_code = error_codes_by_name["USER_DOES_NOT_OWN_ITEM"]


class ItemImmutableException(MessageException):
    status_code = 403
    err_code = error_codes_by_name["ITEM_IS_IMMUTABLE"]


class ConfigDoesNotAllowException(MessageException):
    status_code = 403
    err_code = error_codes_by_name["CONFIG_DOES_NOT_ALLOW"]


class InsufficientPermissionsException(MessageException):
    status_code = 403
    err_code = error_codes_by_name["INSUFFICIENT_PERMISSIONS"]


class UserCannotRunAsException(MessageException):
    status_code = 403
    err_code = error_codes_by_name["USER_CANNOT_RUN_AS"]


class UserRequiredException(MessageException):
    status_code = 403
    err_code = error_codes_by_name["USER_REQUIRED"]


class AdminRequiredException(MessageException):
    status_code = 403
    err_code = error_codes_by_name["ADMIN_REQUIRED"]


class UserActivationRequiredException(MessageException):
    status_code = 403
    err_code = error_codes_by_name["USER_ACTIVATION_REQUIRED"]


class ItemAlreadyClaimedException(MessageException):
    status_code = 403
    err_code = error_codes_by_name["ITEM_IS_CLAIMED"]


class ObjectNotFound(MessageException):
    """Accessed object was not found"""

    status_code = 404
    err_code = error_codes_by_name["USER_OBJECT_NOT_FOUND"]


class Conflict(MessageException):
    status_code = 409
    err_code = error_codes_by_name["CONFLICT"]


class ItemMustBeClaimed(Conflict):
    err_code = error_codes_by_name["MUST_CLAIM"]


class DeprecatedMethod(MessageException):
    """
    Method (or a particular form/arg signature) has been removed and won't be available later
    """

    status_code = 410
    err_code = error_codes_by_name["DEPRECATED_API_CALL"]


class ConfigurationError(Exception):
    status_code = 500
    err_code = error_codes_by_name["CONFIG_ERROR"]


class InconsistentDatabase(MessageException):
    status_code = 500
    err_code = error_codes_by_name["INCONSISTENT_DATABASE"]


class InconsistentApplicationState(MessageException):
    status_code = 500
    err_code = error_codes_by_name["INCONSISTENT_APPLICATION_STATE"]


class InternalServerError(MessageException):
    status_code = 500
    err_code = error_codes_by_name["INTERNAL_SERVER_ERROR"]


class ToolExecutionError(MessageException):
    status_code = 500
    err_code = error_codes_by_name["TOOL_EXECUTION_ERROR"]

    def __init__(self, err_msg, type="error", job=None):
        super().__init__(err_msg, type)
        self.job = job


class NotImplemented(MessageException):
    status_code = 501
    err_code = error_codes_by_name["NOT_IMPLEMENTED"]


class InvalidFileFormatError(MessageException):
    status_code = 500
    err_code = error_codes_by_name["INVALID_FILE_FORMAT"]


class ReferenceDataError(MessageException):
    status_code = 500
    err_code = error_codes_by_name["REFERENCE_DATA_ERROR"]


class ServerNotConfiguredForRequest(MessageException):
    # A bit like ConfigDoesNotAllowException but it has nothing to do with the user of the
    # request being "forbidden". It just isn't configured.
    status_code = 501
    err_code = error_codes_by_name["SERVER_NOT_CONFIGURED_FOR_REQUEST"]


class HandlerAssignmentError(Exception):
    def __init__(self, msg=None, obj=None, **kwargs):
        super().__init__(msg)
        self.obj = obj
