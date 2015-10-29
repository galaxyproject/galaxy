import abc
from collections import namedtuple

from galaxy.tools.deps.commands import which

try:
    from lxml import etree
except ImportError:
    etree = None


class XsdValidator(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def validate(self, schema_path, target_path):
        """ Validate ``target_path`` against ``schema_path``.

        :return type: ValidationResult
        """

    @abc.abstractmethod
    def enabled(self):
        """ Return True iff system has dependencies for this validator.

        :return type: bool
        """

ValidationResult = namedtuple("ValidationResult", ["passed", "output"])


class LxmlValidator(XsdValidator):
    """ Validate XSD files using lxml library. """

    def validate(self, schema_path, target_path):
        pass

    def enabled(self):
        return etree is not None


class XmllintValidator(XsdValidator):
    """ Validate XSD files with the external tool xmllint. """

    def validate(self, schema_path, target_path):
        pass

    def enabled(self):
        return bool(which("xmllint"))


VALIDATORS = [LxmlValidator(), XmllintValidator()]


def get_validator():
    for validator in VALIDATORS:
        if validator.enabled():
            return validator
