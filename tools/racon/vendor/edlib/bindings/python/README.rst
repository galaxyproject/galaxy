=====
Edlib
=====

Lightweight, super fast library for sequence alignment using edit (Levenshtein) distance.

.. code:: python

    edlib.align("hello", "world")

Edlib is actually a C/C++ library, and this package is it's wrapper for Python.
Python Edlib has mostly the same API as C/C++ Edlib, so make sure to check out `C/C++ Edlib docs <http://github.com/Martinsos/edlib>`_ for more code examples, details on API and how Edlib works.

--------
Features
--------

* Calculates **edit distance**.
* It can find **optimal alignment path** (instructions how to transform first sequence into the second sequence).
* It can find just the **start and/or end locations of alignment path** - can be useful when speed is more important than having exact alignment path.
* Supports **multiple alignment methods**: global(**NW**), prefix(**SHW**) and infix(**HW**), each of them useful for different scenarios.
* You can **extend character equality definition**, enabling you to e.g. have wildcard characters, to have case insensitive alignment or to work with degenerate nucleotides.
* It can easily handle small or **very large** sequences, even when finding alignment path.
* **Super fast** thanks to Myers's bit-vector algorithm.

------------
Installation
------------
::

    pip install edlib

---
API
---

Edlib has only one function:

.. code:: python

    align(query, target, [mode], [task], [k])

To learn more about it, type :code:`help(edlib.align)` in your python interpreter.

-----
Usage
-----
.. code:: python

    import edlib

    result = edlib.align("elephant", "telephone")
    print(result["editDistance"])  # 3
    print(result["alphabetLength"])  # 8
    print(result["locations"])  # [(None, 8)]
    print(result["cigar"])  # None

    result = edlib.align("ACTG", "CACTRT", mode="HW", task="path", additionalEqualities=[("R", "A"), ("R", "G")])
    print(result["editDistance"])  # 0
    print(result["alphabetLength"])  # 5
    print(result["locations"])  # [(1, 4)]
    print(result["cigar"])  # "4="

---------
Benchmark
---------

I run a simple benchmark on 7 Feb 2017 (using timeit, on Python3) to get a feeling of how Edlib compares to other Python libraries: `editdistance <https://pypi.python.org/pypi/editdistance>`_ and `python-Levenshtein <https://pypi.python.org/pypi/python-Levenshtein>`_.

As input data I used pairs of DNA sequences of different lengths, where each pair has about 90% similarity.

::

   #1: query length: 30, target length: 30
   edlib.align(query, target): 1.88µs
   editdistance.eval(query, target): 1.26µs
   Levenshtein.distance(query, target): 0.43µs

   #2: query length: 100, target length: 100
   edlib.align(query, target): 3.64µs
   editdistance.eval(query, target): 3.86µs
   Levenshtein.distance(query, target): 14.1µs

   #3: query length: 1000, target length: 1000
   edlib.align(query, target): 0.047ms
   editdistance.eval(query, target): 5.4ms
   Levenshtein.distance(query, target): 1.9ms

   #4: query length: 10000, target length: 10000
   edlib.align(query, target): 0.0021s
   editdistance.eval(query, target): 0.56s
   Levenshtein.distance(query, target): 0.2s

   #5: query length: 50000, target length: 50000
   edlib.align(query, target): 0.031s
   editdistance.eval(query, target): 13.8s
   Levenshtein.distance(query, target): 5.0s

----
More
----

Check out `C/C++ Edlib docs <http://github.com/Martinsos/edlib>`_ for more information about Edlib!

-----------
Development
-----------

Run :code:`make build` to generate an extension module as .so file. You can test it then by importing it from python interpreter :code:`import edlib` and running :code:`edlib.align(...)` (you have to be positioned in the directory where .so was built). This is useful for testing while developing.

Run :code:`make sdist` to create a source distribution, but not publish it - it is a tarball in dist/ that will be uploaded to pip on `publish`. Use this to check that tarball is well structured and contains all needed files, before you publish.
Good way to test it is to run :code:`sudo pip install dist/edlib-*.tar.gz`, which will try to install edlib from it, same way as pip will do it when it is published.

Run :code:`make publish` to create a source distribution and publish it to the PyPI. Use this to publish new version of package.
Make sure to bump the version in `setup.py` before publishing, if needed.

:code:`make clean` removes all generated files.
