"""Entry point for the usage of Cheetah templating within Galaxy."""
from __future__ import absolute_import

import logging
import subprocess
import sys
import tempfile
import traceback

from Cheetah.Compiler import Compiler
from Cheetah.NameMapper import NotFound
from Cheetah.Template import Template

from . import unicodify

log = logging.getLogger(__name__)


class Py3Compiler(Compiler):

    def getModuleCode(self):
        module_code = super(Py3Compiler, self).getModuleCode()
        self._moduleDef = futurize_preprocessor(module_code)
        return self._moduleDef


def fill_template(template_text, context=None, retry=10, **kwargs):
    """Fill a cheetah template out for specified context.

    If template_text is None, an exception will be thrown, if context
    is None (the default) - keyword arguments to this function will be used
    as the context.
    """
    if template_text is None:
        raise TypeError("Template text specified as None to fill_template.")
    if not context:
        context = kwargs
    try:
        return unicodify(Template(source=template_text, searchList=[context]))
    except NotFound as e:
        if retry > 0 and sys.version_info.major > 2:
            tb = e.__traceback__
            if traceback.extract_tb(tb)[-1].name == '<listcomp>':
                arg_to_set_global = e.args[0].split("'")[1]
                log.warning("Replacing variable %s", arg_to_set_global)
                new_template = "#set global $%s = None\n" % arg_to_set_global
                return fill_template(template_text=new_template + template_text, context=context, retry=retry - 1, **kwargs)
        raise
    except AttributeError:
        klass = Template.compile(source=template_text, compilerClass=Py3Compiler)
        t = klass(searchList=[context])
        return unicodify(t)



def futurize_preprocessor(source):
    with tempfile.NamedTemporaryFile(mode='w') as module_out:
        module_out.write(source)
        module_out.flush()
        subprocess.check_call(['futurize', '-w', module_out.name])
        with open(module_out.name) as fixed_module:
            source = fixed_module.read()
            source = source.replace('from Cheetah.compat import str', 'from Cheetah.compat import unicode')
    return source
