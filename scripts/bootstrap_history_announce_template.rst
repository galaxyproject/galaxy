===========================================================
TODO Galaxy Release (v %s)
===========================================================

.. include:: _header.rst

Highlights
===========================================================

**Feature1**
  Feature description.

**Feature2**
  Feature description.

**Feature3**
  Feature description.

`Github <https://github.com/galaxyproject/galaxy>`__
===========================================================

New
  .. code-block:: shell
  
      % git clone -b master https://github.com/galaxyproject/galaxy.git

Update to latest stable release
  .. code-block:: shell
  
      % git checkout master && pull --ff-only origin master

Update to exact version
  .. code-block:: shell
  
      % git checkout v%s


`BitBucket <https://bitbucket.org/galaxy/galaxy-dist>`__
===========================================================

Upgrade
  .. code-block:: shell
  
      % hg pull
      % hg update latest_%s


See `our wiki <https://wiki.galaxyproject.org/Develop/SourceCode>`__ for additional details regarding the source code locations.

Release Notes
===========================================================

.. include:: %s.rst
   :start-after: enhancements

.. include:: _thanks.rst
