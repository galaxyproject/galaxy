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

from ..exceptions import error_codes


class MessageException(Exception):
    """Most generic Galaxy exception - indicates merely that some exceptional condition happened."""
    # status code to be set when used with API.
    status_code = 400
    # Error code information embedded into API json responses.
    err_code = error_codes.UNKNOWN

    def __init__(self, err_msg=None, type="info", **extra_error_info):
        self.err_msg = err_msg or self.err_code.default_error_message
        self.type = type
        self.extra_error_info = extra_error_info

    def __str__(self):
        return self.err_msg


class ItemDeletionException(MessageException):
    pass


class ObjectInvalid(Exception):
    """ Accessed object store ID is invalid """
    pass

# Please keep the exceptions ordered by status code


class ActionInputError(MessageException):
    status_code = 400
    err_code = error_codes.USER_REQUEST_INVALID_PARAMETER

    def __init__(self, err_msg, type="error"):
        super(ActionInputError, self).__init__(err_msg, type)


class DuplicatedSlugException(MessageException):
    status_code = 400
    err_code = error_codes.USER_SLUG_DUPLICATE


class DuplicatedIdentifierException(MessageException):
    status_code = 400
    err_code = error_codes.USER_IDENTIFIER_DUPLICATE


class ObjectAttributeInvalidException(MessageException):
    status_code = 400
    err_code = error_codes.USER_OBJECT_ATTRIBUTE_INVALID


class ObjectAttributeMissingException(MessageException):
    status_code = 400
    err_code = error_codes.USER_OBJECT_ATTRIBUTE_MISSING


class MalformedId(MessageException):
    status_code = 400
    err_code = error_codes.MALFORMED_ID


class MalformedContents(MessageException):
    status_code = 400
    err_code = error_codes.MALFORMED_CONTENTS


class UnknownContentsType(MessageException):
    status_code = 400
    err_code = error_codes.UNKNOWN_CONTENTS_TYPE


class RequestParameterMissingException(MessageException):
    status_code = 400
    err_code = error_codes.USER_REQUEST_MISSING_PARAMETER


class ToolMetaParameterException(MessageException):
    status_code = 400
    err_code = error_codes.USER_TOOL_META_PARAMETER_PROBLEM


class ToolMissingException(MessageException):
    status_code = 400
    err_code = error_codes.USER_TOOL_MISSING_PROBLEM

    def __init__(self, err_msg=None, type="info", tool_id=None, **extra_error_info):
        super(ToolMissingException, self).__init__(err_msg, type, **extra_error_info)
        self.tool_id = tool_id


class RequestParameterInvalidException(MessageException):
    status_code = 400
    err_code = error_codes.USER_REQUEST_INVALID_PARAMETER


class AuthenticationFailed(MessageException):
    status_code = 401
    err_code = error_codes.USER_AUTHENTICATION_FAILED


class AuthenticationRequired(MessageException):
    status_code = 403
    # TODO: as 401 and send WWW-Authenticate: ???
    err_code = error_codes.USER_NO_API_KEY


class ItemAccessibilityException(MessageException):
    status_code = 403
    err_code = error_codes.USER_CANNOT_ACCESS_ITEM


class ItemOwnershipException(MessageException):
    status_code = 403
    err_code = error_codes.USER_DOES_NOT_OWN_ITEM


class ConfigDoesNotAllowException(MessageException):
    status_code = 403
    err_code = error_codes.CONFIG_DOES_NOT_ALLOW


class InsufficientPermissionsException(MessageException):
    status_code = 403
    err_code = error_codes.INSUFFICIENT_PERMISSIONS


class AdminRequiredException(MessageException):
    status_code = 403
    err_code = error_codes.ADMIN_REQUIRED


class UserActivationRequiredException(MessageException):
    status_code = 403
    err_code = error_codes.USER_ACTIVATION_REQUIRED


class ObjectNotFound(MessageException):
    """ Accessed object was not found """
    status_code = 404
    err_code = error_codes.USER_OBJECT_NOT_FOUND


class DeprecatedMethod(MessageException):
    """
    Method (or a particular form/arg signature) has been removed and won't be available later
    """
    status_code = 404
    # TODO:?? 410 Gone?
    err_code = error_codes.DEPRECATED_API_CALL


class Conflict(MessageException):
    status_code = 409
    err_code = error_codes.CONFLICT


class ConfigurationError(Exception):
    status_code = 500
    err_code = error_codes.CONFIG_ERROR


class InconsistentDatabase(MessageException):
    status_code = 500
    err_code = error_codes.INCONSISTENT_DATABASE


class InternalServerError(MessageException):
    status_code = 500
    err_code = error_codes.INTERNAL_SERVER_ERROR


class ToolExecutionError(MessageException):
    status_code = 500
    err_code = error_codes.TOOL_EXECUTION_ERROR

    def __init__(self, err_msg, type="error", job=None):
        super(ToolExecutionError, self).__init__(err_msg, type)
        self.job = job


class NotImplemented(MessageException):
    status_code = 501
    err_code = error_codes.NOT_IMPLEMENTED


# non-web exceptions


class ContainerCLIError(Exception):
    def __init__(self, msg=None, stdout=None, stderr=None, returncode=None,
                 command=None, subprocess_command=None, **kwargs):
        super(ContainerCLIError, self).__init__(msg, **kwargs)
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode
        self.command = command
        self.subprocess_command = subprocess_command


class ContainerNotFound(Exception):
    def __init__(self, msg=None, container_id=None, **kwargs):
        super(ContainerNotFound, self).__init__(msg, **kwargs)
        self.container_id = container_id


class ContainerImageNotFound(Exception):
    def __init__(self, msg=None, image=None, **kwargs):
        super(ContainerImageNotFound, self).__init__(msg, **kwargs)
        self.image = image


class ContainerRunError(Exception):
    def __init__(self, msg=None, image=None, command=None, **kwargs):
        super(ContainerRunError, self).__init__(msg, **kwargs)
        self.image = image
        self.command = command


class HandlerAssignmentError(Exception):
    def __init__(self, msg=None, obj=None, **kwargs):
        super(HandlerAssignmentError, self).__init__(msg, **kwargs)
        self.obj = obj
