from setuptools import setup, Extension
from codecs import open
import os

cmdclass = {}
long_description = ""

# Build directly from cython source file(s) if user wants so (probably for some experiments).
# Otherwise, pre-generated c source file(s) are used.
# User has to set environment variable EDLIB_USE_CYTHON.
# e.g.: EDLIB_USE_CYTHON=1 python setup.py install
USE_CYTHON = os.getenv('EDLIB_USE_CYTHON', False)
if USE_CYTHON:
    from Cython.Build import build_ext
    edlib_module_src = "edlib.pyx"
    cmdclass['build_ext'] = build_ext
else:
    edlib_module_src = "edlib.bycython.cpp"

# Load README into long description.
here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    # Information
    name = "edlib",
    description = "Lightweight, super fast library for sequence alignment using edit (Levenshtein) distance.",
    long_description = long_description,
    version = "1.2.1",
    url = "https://github.com/Martinsos/edlib",
    author = "Martin Sosic",
    author_email = "sosic.martin@gmail.com",
    license = "MIT",
    keywords = "edit distance levenshtein align sequence bioinformatics",
    # Build instructions
    ext_modules = [Extension("edlib",
                             [edlib_module_src, "edlib/src/edlib.cpp"],
                             include_dirs=["edlib/include"],
                             depends=["edlib/include/edlib.h"],
                             language="c++",
                             extra_compile_args=["-O3", "-std=c++11"])],
    cmdclass = cmdclass
)
