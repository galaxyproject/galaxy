"""Utilities for dealing with the Galaxy 'handler' process pattern.

A 'handler' is a named Python process running the Galaxy application responsible
for some activity such as queuing up jobs or scheduling workflows.
"""

import logging
import os
import random

log = logging.getLogger(__name__)


class ConfiguresHandlers:

    def _init_handlers(self, config_element):
        # Parse handlers
        if config_element is not None:
            for handler in self._findall_with_required(config_element, 'handler'):
                handler_id = handler.get('id')
                if handler_id in self.handlers:
                    log.error("Handler '%s' overlaps handler with the same name, ignoring" % handler_id)
                else:
                    log.debug("Read definition for handler '%s'" % handler_id)
                    self.handlers[handler_id] = (handler_id,)
                    self._parse_handler(handler_id, handler)
                    if handler.get('tags', None) is not None:
                        for tag in [x.strip() for x in handler.get('tags').split(',')]:
                            if tag in self.handlers:
                                self.handlers[tag].append(handler_id)
                            else:
                                self.handlers[tag] = [handler_id]

    def _parse_handler(self, handler_id, handler_def):
        pass

    def _get_default(self, config, parent, names):
        """
        Returns the default attribute set in a parent tag like <handlers> or
        <destinations>, or return the ID of the child, if there is no explicit
        default and only one child.

        :param parent: Object representing a tag that may or may not have a 'default' attribute.
        :type parent: ``xml.etree.ElementTree.Element``
        :param names: The list of destination or handler IDs or tags that were loaded.
        :type names: list of str

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
            if rval not in names:
                raise Exception("<%s> default attribute '%s' does not match a defined id or tag in a child element" % (parent.tag, rval))
            log.debug("<%s> default set to child with id or tag '%s'" % (parent.tag, rval))
        elif len(names) == 1:
            log.info("Setting <%s> default to child with id '%s'" % (parent.tag, names[0]))
            rval = names[0]
        else:
            raise Exception("No <%s> default specified, please specify a valid id or tag with the 'default' attribute" % parent.tag)
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

    def is_handler(self, server_name):
        """Given a server name, indicate whether the server is a handler.

        :param server_name: The name to check
        :type server_name: str

        :return: bool
        """
        for collection in self.handlers.values():
            if server_name in collection:
                return True
        return False

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

    # This is called by Tool.get_job_handler()
    def get_handler(self, id_or_tag, index=None):
        """Given a handler ID or tag, return a handler matching it.

        :param id_or_tag: A handler ID or tag.
        :type id_or_tag: str
        :param index: Generate "consistent" "random" handlers with this index if specified.
        :type index: int

        :returns: str -- A valid job handler ID.
        """
        if id_or_tag is None:
            id_or_tag = self.default_handler_id
        return self._get_single_item(self.handlers[id_or_tag], index=index)
