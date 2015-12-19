==================
Release Checklist
==================

This page describes the process of releasing new versions of galaxy-lib.

This release checklist is based on the `Pocoo Release Management Workflow
<http://www.pocoo.org/internal/release-management/>`_.

This assumes ``~/.pypirc`` file exists with the following fields (variations)
are fine.

::

    [distutils]
    index-servers =
        pypi
        test
    
    [pypi]
    username:<username>
    password:<password>
    
    [test]
    repository:https://testpypi.python.org/pypi
    username:<username>
    password:<password>


* Review ``git status`` for missing files.
* Verify the latest Travis CI builds pass.
* ``make open-docs`` and review changelog.
* Ensure the target release is set correctly in ``galaxy/__init__.py`` (
  ``version`` will be a ``devN`` variant of target release).
* ``make clean && make lint && make test``
* ``make release``

  This process will push packages to test PyPI, allow review, publish
  to production PyPI, tag the git repository, push the tag upstream,
  and modify the Homebrew recipe. If changes are needed, such as manual
  changes to the homebrew recipe, this can be broken down into steps 
  such as:

  * ``make release-local``
  * ``make push-release``
  * ``make release-brew``
