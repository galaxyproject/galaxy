"""Entry point for the usage of Cheetah templating within Galaxy."""

import traceback
from lib2to3.refactor import RefactoringTool

import packaging.version
from Cheetah.Compiler import Compiler
from Cheetah.NameMapper import NotFound
from Cheetah.Parser import ParseError
from Cheetah.Template import Template
from past.translation import myfixes

from . import unicodify

# Skip libpasteurize fixers, which make sure code is py2 and py3 compatible.
# This is not needed, we only translate code on py3.
myfixes = [f for f in myfixes if not f.startswith('libpasteurize')]
refactoring_tool = RefactoringTool(myfixes, {'print_function': True})


class FixedModuleCodeCompiler(Compiler):

    module_code = None

    def getModuleCode(self):
        self._moduleDef = self.module_code
        return self._moduleDef


def create_compiler_class(module_code):

    class CustomCompilerClass(FixedModuleCodeCompiler):
        pass

    CustomCompilerClass.module_code = module_code
    return CustomCompilerClass


def fill_template(template_text,
                  context=None,
                  retry=10,
                  compiler_class=Compiler,
                  first_exception=None,
                  futurized=False,
                  python_template_version='3',
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
    if isinstance(python_template_version, str):
        python_template_version = packaging.version.parse(python_template_version)
    try:
        klass = Template.compile(source=template_text, compilerClass=compiler_class)
    except ParseError as e:
        # Might happen on invalid syntax within a cheetah statement, like `#if $smxsize <> 128.0`
        if first_exception is None:
            first_exception = e
        if python_template_version.release[0] < 3 and retry > 0:
            module_code = Template.compile(source=template_text, compilerClass=compiler_class, returnAClass=False).decode('utf-8')
            module_code = futurize_preprocessor(module_code)
            compiler_class = create_compiler_class(module_code)
            return fill_template(
                template_text=template_text,
                context=context,
                retry=retry - 1,
                compiler_class=compiler_class,
                first_exception=first_exception,
                python_template_version=python_template_version,
            )
        raise first_exception or e
    t = klass(searchList=[context])
    try:
        return unicodify(t, log_exception=False)
    except NotFound as e:
        if first_exception is None:
            first_exception = e
        if python_template_version.release[0] < 3 and retry > 0:
            tb = e.__traceback__
            last_stack = traceback.extract_tb(tb)[-1]
            if last_stack.name == '<listcomp>':
                # On python 3 list, dict and set comprehensions as well as generator expressions
                # have their own local scope, which prevents accessing frame variables in cheetah.
                # We can work around this by replacing `$var` with `var`, but we only do this for
                # list comprehensions, as this has never worked for dict or set comprehensions or
                # generator expressions in Cheetah.
                var_not_found = e.args[0].split("'")[1]
                replace_str = f'VFFSL(SL,"{var_not_found}",True)'
                lineno = last_stack.lineno - 1
                module_code = t._CHEETAH_generatedModuleCode.splitlines()
                module_code[lineno] = module_code[lineno].replace(replace_str, var_not_found)
                module_code = "\n".join(module_code)
                compiler_class = create_compiler_class(module_code)
                return fill_template(template_text=template_text,
                                     context=context,
                                     retry=retry - 1,
                                     compiler_class=compiler_class,
                                     first_exception=first_exception,
                                     python_template_version=python_template_version,
                                     )
        raise first_exception or e
    except Exception as e:
        if first_exception is None:
            first_exception = e
        if python_template_version.release[0] < 3 and not futurized:
            # Possibly an error caused by attempting to run python 2
            # template code on python 3. Run the generated module code
            # through futurize and hope for the best.
            module_code = t._CHEETAH_generatedModuleCode
            module_code = futurize_preprocessor(module_code)
            compiler_class = create_compiler_class(module_code)
            return fill_template(template_text=template_text,
                                 context=context,
                                 retry=retry,
                                 compiler_class=compiler_class,
                                 first_exception=first_exception,
                                 futurized=True,
                                 python_template_version=python_template_version,
                                 )
        raise first_exception or e


def futurize_preprocessor(source):
    source = str(refactoring_tool.refactor_string(source, name='auto_translate_cheetah'))
    # libfuturize.fixes.fix_unicode_keep_u' breaks from Cheetah.compat import unicode
    source = source.replace('from Cheetah.compat import str', 'from Cheetah.compat import unicode')
    return source
