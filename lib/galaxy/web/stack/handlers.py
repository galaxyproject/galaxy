"""Utilities for dealing with the Galaxy 'handler' process pattern.

A 'handler' is a named Python process running the Galaxy application responsible
for some activity such as queuing up jobs or scheduling workflows.
"""
from __future__ import absolute_import

import logging
import os
import random
from collections import namedtuple

from sqlalchemy.orm import object_session

from galaxy.exceptions import HandlerAssignmentError
from galaxy.util import (
    ExecutionTimer,
    listify
)

log = logging.getLogger(__name__)

_handler_assignment_methods = (
    'MEM_SELF', 'DB_SELF', 'DB_PREASSIGN', 'DB_TRANSACTION_ISOLATION', 'DB_SKIP_LOCKED', 'UWSGI_MULE_MESSAGE'
)
HANDLER_ASSIGNMENT_METHODS = namedtuple('JOB_HANDLER_ASSIGNMENT_METHODS', _handler_assignment_methods)(
    *[x.lower().replace('_', '-') for x in _handler_assignment_methods]
)


class HandlerAssignmentSkip(Exception):
    """Exception for handler assignment methods to raise if the next method should be tried.
    """
    pass


class ConfiguresHandlers(object):
    DEFAULT_HANDLER_TAG = '_default_'
    DEFAULT_BASE_HANDLER_POOLS = ()
    UNSUPPORTED_HANDLER_ASSIGNMENT_METHODS = ()

    def add_handler(self, handler_id, tags):
        if handler_id not in self.handlers:
            self.handlers[handler_id] = (handler_id,)
        for tag in tags:
            if tag in self.handlers and handler_id not in self.handlers[tag]:
                self.handlers[tag].append(handler_id)
            else:
                self.handlers[tag] = [handler_id]

    def _init_handlers(self, config_element):
        # Parse handlers
        if config_element is not None:
            for handler in self._findall_with_required(config_element, 'handler'):
                handler_id = handler.get('id')
                if handler_id in self.handlers:
                    log.error("Handler '%s' overlaps handler with the same name, ignoring", handler_id)
                else:
                    log.debug("Read definition for handler '%s'", handler_id)
                    self.add_handler(
                        handler_id,
                        [x.strip() for x in handler.get('tags', self.DEFAULT_HANDLER_TAG).split(',')]
                    )
            self.default_handler_id = self._get_default(self.app.config, config_element, list(self.handlers.keys()))

    def _init_handler_assignment_methods(self, config_element=None):
        self.__is_handler = None
        # This is set by the stack job handler init code
        self.pool_for_tag = {}
        self._handler_assignment_method_methods = {
            HANDLER_ASSIGNMENT_METHODS.MEM_SELF: self._assign_mem_self_handler,
            HANDLER_ASSIGNMENT_METHODS.DB_SELF: self._assign_db_self_handler,
            HANDLER_ASSIGNMENT_METHODS.DB_PREASSIGN: self._assign_db_preassign_handler,
            HANDLER_ASSIGNMENT_METHODS.DB_TRANSACTION_ISOLATION: self._assign_db_tag,
            HANDLER_ASSIGNMENT_METHODS.DB_SKIP_LOCKED: self._assign_db_tag,
            HANDLER_ASSIGNMENT_METHODS.UWSGI_MULE_MESSAGE: self._assign_uwsgi_mule_message_handler,
        }
        if config_element is not None:
            for method in listify(config_element.attrib.get('assign_with', []), do_strip=True):
                method = method.lower()
                assert method in HANDLER_ASSIGNMENT_METHODS, \
                    "Invalid job handler assignment method '%s', must be one of: %s" % (
                        method, ', '.join(HANDLER_ASSIGNMENT_METHODS))
                try:
                    self.handler_assignment_methods.append(method)
                except AttributeError:
                    self.handler_assignment_methods_configured = True
                    self.handler_assignment_methods = [method]
            if self.handler_assignment_methods == [HANDLER_ASSIGNMENT_METHODS.MEM_SELF]:
                self.app.config.track_jobs_in_database = False
            self.handler_max_grab = int(config_element.attrib.get('max_grab', self.handler_max_grab))

    def _set_default_handler_assignment_methods(self):
        if not self.handler_assignment_methods_configured:
            if not self.app.config.track_jobs_in_database and \
                    HANDLER_ASSIGNMENT_METHODS.MEM_SELF not in self.UNSUPPORTED_HANDLER_ASSIGNMENT_METHODS:
                # DEPRECATED: You should just set mem_self as the only method if you want this
                log.warning("The `track_jobs_in_database` option is deprecated, please set `%s` as the job"
                            " handler assignment method in the job handler configuration",
                            HANDLER_ASSIGNMENT_METHODS.MEM_SELF)
                self.handler_assignment_methods = [HANDLER_ASSIGNMENT_METHODS.MEM_SELF]
            elif not self.handlers:
                # No handlers defined, default is for processes to handle the jobs they create
                self.handler_assignment_methods = [HANDLER_ASSIGNMENT_METHODS.DB_SELF]
            else:
                # Handlers are defined, default is the value if the default attribute, or any untagged handler if
                # default attribute is unset
                self.handler_assignment_methods = [HANDLER_ASSIGNMENT_METHODS.DB_PREASSIGN]
            # If the stack has handler pools it can override these defaults
            self.app.application_stack.init_job_handling(self)
            log.info("%s: No job handler assignment method is set, defaulting to '%s', set the `assign_with` attribute"
                     " on <handlers> to override the default", self.__class__.__name__,
                     self.handler_assignment_methods[0])

    def _parse_handler(self, handler_id, handler_def):
        pass

    def _get_default(self, config, parent, names, auto=False):
        """
        Returns the default attribute set in a parent tag like <handlers> or
        <destinations>, or return the ID of the child, if there is no explicit
        default and only one child.

        :param parent: Object representing a tag that may or may not have a 'default' attribute.
        :type parent: ``xml.etree.ElementTree.Element``
        :param names: The list of destination or handler IDs or tags that were loaded.
        :type names: list of str
        :param auto: Automatically set a default if there is no default in the parent tag and there is only one child.
        :type auto: bool

        :returns: str -- id or tag representing the default.
        """

        rval = parent.get('default')
        if 'default_from_environ' in parent.attrib:
            environ_var = parent.attrib['default_from_environ']
            rval = os.environ.get(environ_var, rval)
        elif 'default_from_config' in parent.attrib:
            config_val = parent.attrib['default_from_config']
            rval = config.config_dict.get(config_val, rval)

        if rval is not None:
            # If the parent element has a 'default' attribute, use the id or tag in that attribute
            if self.deterministic_handler_assignment and rval not in names:
                raise Exception("<%s> default attribute '%s' does not match a defined id or tag in a child element" % (parent.tag, rval))
            log.debug("<%s> default set to child with id or tag '%s'" % (parent.tag, rval))
        elif auto and len(names) == 1:
            log.info("Setting <%s> default to child with id '%s'" % (parent.tag, names[0]))
            rval = names[0]
        return rval

    def _findall_with_required(self, parent, match, attribs=None):
        """Like ``xml.etree.ElementTree.Element.findall()``, except only returns children that have the specified attribs.

        :param parent: Parent element in which to find.
        :type parent: ``xml.etree.ElementTree.Element``
        :param match: Name of child elements to find.
        :type match: str
        :param attribs: List of required attributes in children elements.
        :type attribs: list of str

        :returns: list of ``xml.etree.ElementTree.Element``
        """
        rval = []
        if attribs is None:
            attribs = ('id',)
        for elem in parent.findall(match):
            for attrib in attribs:
                if attrib not in elem.attrib:
                    log.warning("required '%s' attribute is missing from <%s> element" % (attrib, match))
                    break
            else:
                rval.append(elem)
        return rval

    @property
    def use_messaging(self):
        # The job manager uses this to determine whether the messaging job queue should be used
        return HANDLER_ASSIGNMENT_METHODS.UWSGI_MULE_MESSAGE in self.handler_assignment_methods

    @property
    def deterministic_handler_assignment(self):
        return self.handler_assignment_methods and all(
            filter(lambda x: x in (
                HANDLER_ASSIGNMENT_METHODS.UWSGI_MULE_MESSAGE,
                HANDLER_ASSIGNMENT_METHODS.DB_PREASSIGN,
            ), self.handler_assignment_methods))

    def _get_is_handler(self):
        """Indicate whether the current server is configured as a handler.

        :return: bool
        """
        if self.__is_handler is not None:
            return self.__is_handler
        if (HANDLER_ASSIGNMENT_METHODS.DB_SELF in self.handler_assignment_methods
                or HANDLER_ASSIGNMENT_METHODS.MEM_SELF in self.handler_assignment_methods):
            return True
        for collection in self.handlers.values():
            if self.app.config.server_name in collection:
                return True
        return False

    def _set_is_handler(self, value):
        self.__is_handler = value

    is_handler = property(_get_is_handler, _set_is_handler)

    def _get_single_item(self, collection, index=None):
        """Given a collection of handlers or destinations, return one item from the collection at random.
        """
        # Done like this to avoid random under the assumption it's faster to avoid it
        if len(collection) == 1:
            return collection[0]
        elif index is None:
            return random.choice(collection)
        else:
            return collection[index % len(collection)]

    @property
    def handler_tags(self):
        """Get an iteratable of all configured handler tags.
        """
        return filter(lambda k: isinstance(self.handlers[k], list), self.handlers.keys())

    @property
    def self_handler_tags(self):
        """Get an iterable of the current process's configured handler tags.
        """
        return filter(lambda k: self.app.config.server_name in self.handlers[k], self.handler_tags)

    # If these get to be any more complex we should probably modularize them, or at least move to a separate class

    def _assign_handler_direct(self, obj, configured):
        """Directly assign a handler if the object has been preconfigured to a known single static handler.

        :param obj:             Same as :method:`ConfiguresHandlers.assign_handler()`.
        :param configured:      Same as :method:`ConfiguresHandlers.assign_handler()`.

        :returns: str -- A valid handler ID, or False if no handler was assigned.
        """
        if self.app.config.track_jobs_in_database and configured:
            try:
                handlers = self.handlers[configured]
            except KeyError:
                handlers = None
            if handlers == (configured,):
                obj.set_handler(configured)
                _timed_flush_obj(obj)
                return configured
        return False

    def _assign_mem_self_handler(self, obj, method, configured, queue_callback=None, **kwargs):
        """Assign object to this handler using this process's in-memory queue.

        This method ignores all handler configuration.

        :param obj:             Same as :method:`ConfiguresHandlers.assign_handler()`.
        :param method:          Same as :method:`ConfiguresHandlers._assign_db_preassign_handler()`.
        :param configured:      Ignored.
        :param queue_callback:  Callback to be executed when the job should be queued (i.e. a callback to the handler's
                                ``put()`` method). No arguments are passed.
        :type queue_callback:   callable

        :returns: str -- This process's server name (handler ID).
        """
        assert queue_callback is not None, \
            "Cannot perform '%s' handler assignment: `queue_callback` is None" % HANDLER_ASSIGNMENT_METHODS.MEM_SELF
        if configured:
            log.warning("(%s) Ignoring handler assignment to '%s' because configured handler assignment method"
                        " '' overrides per-tool handler assignment", obj.log_str(),
                        HANDLER_ASSIGNMENT_METHODS.MEM_SELF, configured)
        _timed_flush_obj(obj)
        queue_callback()
        return self.app.config.server_name

    def _assign_db_self_handler(self, obj, method, configured, **kwargs):
        """Assign object to this process by setting its ``handler`` column in the database to this process.

        This only occurs if there is not an explicitly configured handler assignment for the object. Otherwise, it is
        passed to the DB_PREASSIGN method for assignment.

        :param obj:             Same as :method:`ConfiguresHandlers.assign_handler()`.
        :param method:          Same as :method:`ConfiguresHandlers._assign_db_preassign_handler()`.
        :param configured:      Same as :method:`ConfiguresHandlers.assign_handler()`.

        :returns: str -- The assigned handler ID.
        """
        if configured:
            return self.handler_assignment_method_methods[HANDLER_ASSIGNMENT_METHODS.DB_PREASSIGN](
                obj, method, configured, **kwargs
            )
        obj.set_handler(self.app.config.server_name)
        _timed_flush_obj(obj)
        return self.app.config.server_name

    def _assign_db_preassign_handler(self, obj, method, configured, index=None, **kwargs):
        """Assign object to a handler by setting its ``handler`` column in the database to a handler selected at random
        from the known handlers in the appropriate tag.

        Given a handler ID or tag, return a handler matching it, of those handlers that are statically configured in
        the job configuration, or known via preconfigured pools.

        :param obj:             Same as :method:`ConfiguresHandlers.assign_handler()`.
        :param method:          Assignment method currently being checked.
        :type method:           Value in :data:`HANDLER_ASSIGNMENT_METHODS`.
        :param configured:      Same as :method:`ConfiguresHandlers.assign_handler()`.
        :param index:           Generate "consistent" "random" handlers with this index if specified.
        :type index:            int

        :raises KeyError: if the configured or default handler is not a known handler ID or tag.
        :returns: str -- A valid job handler ID.
        """
        handler = configured
        if handler is None:
            handler = self.default_handler_id or self.DEFAULT_HANDLER_TAG
        # Get a random handler ID from the possible handlers. If the admin has configured a tool with a handler tag that
        # does not exist, or if there are no default handlers and configured is None, this will raise KeyError to
        # assign_handler, which should log it, try the next method (if any), and if no other methods succeed, raise
        # HandlerAssigmentError.
        handler_id = self._get_single_item(self.handlers[handler], index=index)
        if handler != handler_id:
            log.debug("(%s) Selected handler '%s' by random choice from handler tag '%s'", obj.log_str(),
                      handler_id, handler)
        obj.set_handler(handler_id)
        _timed_flush_obj(obj)
        return handler_id

    def _assign_db_tag(self, obj, method, configured, **kwargs):
        """Assign object to a handler by setting its ``handler`` column in the database to either the configured handler
        ID or tag, or to the default tag (or ``_default_``)

        :param obj:             Same as :method:`ConfiguresHandlers.assign_handler()`.
        :param method:          Same as :method:`ConfiguresHandlers._assign_db_preassign_handler()`.
        :param configured:      Same as :method:`ConfiguresHandlers.assign_handler()`.

        :returns: str -- The assigned handler pool.
        """
        handler = configured
        if handler is None:
            handler = self.default_handler_id or self.DEFAULT_HANDLER_TAG
        obj.set_handler(handler)
        _timed_flush_obj(obj)
        return handler

    def _assign_uwsgi_mule_message_handler(self, obj, method, configured, message_callback=None, **kwargs):
        """Assign object to a handler by sending a setup message to the appropriate handler pool (farm), where a handler
        (mule) will receive the message and assign itself.

        :param obj:             Same as :method:`ConfiguresHandlers.assign_handler()`.
        :param method:          Same as :method:`ConfiguresHandlers._assign_db_preassign_handler()`.
        :param configured:      Same as :method:`ConfiguresHandlers.assign_handler()`.
        :param queue_callback:  Callback returning a setup message to be sent via the stack messaging interface's
                                ``send_message()`` method. No arguments are passed.
        :type queue_callback:   callable

        :raises HandlerAssignmentSkip: if the configured or default handler is not a known handler pool (farm)
        :returns: str -- The assigned handler pool.
        """
        assert message_callback is not None, \
            "Cannot perform '%s' handler assignment: `message_callback` is None" \
            % HANDLER_ASSIGNMENT_METHODS.UWSGI_MULE_MESSAGE
        tag = configured or self.DEFAULT_HANDLER_TAG
        pool = self.pool_for_tag.get(tag)
        if pool is None:
            log.debug("(%s) No handler pool (uWSGI farm) for '%s' found", obj.log_str(), tag)
            raise HandlerAssignmentSkip()
        else:
            _timed_flush_obj(obj)
            message = message_callback()
            self.app.application_stack.send_message(pool, message)
        return pool

    def assign_handler(self, obj, configured=None, **kwargs):
        """Set a job handler, flush obj

        Called assignment methods should raise :exception:`HandlerAssignmentSkip` to indicate that the next method
        should be tried.

        :param obj:         Object to assign a handler to (must be a model object with ``handler`` attribute and
                            ``log_str`` callable).
        :type obj:          instance of :class:`galaxy.model.Job` or other model object with a ``set_handler()`` method.
        :param configured:  Preconfigured handler (ID, tag, or None) for the given object.
        :type configured:   str or None.

        :returns: bool -- True on successful assignment, False otherwise.
        """
        # It's a bit awkward that the method that actually hands off job execution is in the JobConfiguration, but
        # that's currently the best place for it. It's worth noting that this method is also part of the
        # WorkflowSchedulingManager, which acts like a combined JobConfiguration and JobManager. Combining those two
        # classes would probably be reasonable (and would remove the need for the queue callback).
        if self._assign_handler_direct(obj, configured):
            log.info("(%s) Skipped handler assignment logic due to explicit configuration to a single handler: %s",
                     obj.log_str(), configured)
            return True
        for method in self.handler_assignment_methods:
            try:
                handler = self._handler_assignment_method_methods[method](
                    obj, method, configured=configured, **kwargs)
                log.info("(%s) Handler '%s' assigned using '%s' assignment method", obj.log_str(), handler, method)
                return handler
            except HandlerAssignmentSkip:
                log.debug("(%s) Handler assignment method '%s' did not assign a handler, trying next method",
                          obj.log_str(), method)
            except Exception:
                log.exception("Caught exception in handler assignment method: %s", method)
        else:
            # Ideally we could just expunge the object from the SA session here, but in most cases, some of its related
            # objects have already been created, so instead we'll just have to fail it.
            log.error("(%s) Failed to select handler", obj.log_str())
            raise HandlerAssignmentError("Job handler assignment failed.", obj=obj)


def _timed_flush_obj(obj):
    obj_flush_timer = ExecutionTimer()
    sa_session = object_session(obj)
    sa_session.flush()
    log.info("Flushed transaction for %s %s" % (obj.log_str(), obj_flush_timer))
