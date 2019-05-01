"""Entry point for the usage of Cheetah templating within Galaxy."""
from __future__ import absolute_import

import subprocess
import sys
import tempfile
import traceback

from Cheetah.Compiler import Compiler
from Cheetah.NameMapper import NotFound
from Cheetah.Template import Template

from . import unicodify


class FixedModuleCodeCompiler(Compiler):

    module_code = None

    def getModuleCode(self):
        self._moduleDef = self.module_code
        return self._moduleDef


def create_compiler_class(module_code):

    class CustomCompilerClass(FixedModuleCodeCompiler):
        pass

    setattr(CustomCompilerClass, 'module_code', module_code)

    return CustomCompilerClass


def fill_template(template_text,
                  context=None,
                  retry=10,
                  compiler_class=Compiler,
                  first_exception=None,
                  futurized=False,
                  **kwargs):
    """Fill a cheetah template out for specified context.

    If template_text is None, an exception will be thrown, if context
    is None (the default) - keyword arguments to this function will be used
    as the context.
    """
    if template_text is None:
        raise TypeError("Template text specified as None to fill_template.")
    if not context:
        context = kwargs
    klass = Template.compile(source=template_text, compilerClass=compiler_class)
    t = klass(searchList=[context])
    try:
        return unicodify(t)
    except NotFound as e:
        if first_exception is None:
            first_exception = e
        if retry > 0 and sys.version_info.major > 2:
            tb = e.__traceback__
            last_stack = traceback.extract_tb(tb)[-1]
            if last_stack.name in ('<listcomp>', '<dictcomp>', '<setcomp>', '<genexpr>'):
                # On python 3 list,dict and set comprehensions as well as generator expressions
                # have their own local scope, which prevents accessing frame variables in cheetah.
                # We can work around this by replacing `$var` with `var`
                var_not_found = e.args[0].split("'")[1]
                replace_str = 'VFFSL(SL,"%s",True)' % var_not_found
                lineno = last_stack.lineno - 1
                module_code = t._CHEETAH_generatedModuleCode.splitlines()
                module_code[lineno] = module_code[lineno].replace(replace_str, var_not_found)
                module_code = "\n".join(module_code)
                compiler_class = create_compiler_class(module_code)
                return fill_template(template_text=template_text,
                                     context=context,
                                     retry=retry - 1,
                                     compiler_class=compiler_class,
                                     first_exception=first_exception
                                     )
        raise first_exception or e
    except Exception as e:
        if first_exception is None:
            first_exception = e
        if retry > 0 and sys.version_info.major > 2 and not futurized:
            # Possibly an error caused by attempting to run python 2
            # template code on python 3. Run the generated module code
            # through futurize and hope for the best.
            module_code = t._CHEETAH_generatedModuleCode
            module_code = futurize_preprocessor(module_code)
            compiler_class = create_compiler_class(module_code)
            return fill_template(template_text=template_text,
                                 context=context,
                                 retry=retry - 1,
                                 compiler_class=compiler_class,
                                 first_exception=first_exception,
                                 futurized=True
                                 )
        raise first_exception or e


def futurize_preprocessor(source):
    with tempfile.NamedTemporaryFile(mode='w') as module_out:
        module_out.write(source)
        module_out.flush()
        subprocess.check_call(['futurize', '-w', module_out.name])
        with open(module_out.name) as fixed_module:
            source = fixed_module.read()
            source = source.replace('from Cheetah.compat import str', 'from Cheetah.compat import unicode')
    return source
