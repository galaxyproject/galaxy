History
-------

.. to_doc

-----------
24.2.4.dev0
-----------



-------------------
24.2.3 (2025-03-16)
-------------------


============
Enhancements
============

* Add rDock prm datatype by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19783 <https://github.com/galaxyproject/galaxy/pull/19783>`_

-------------------
24.2.2 (2025-03-08)
-------------------


=========
Bug fixes
=========

* Fix conditional dependency path resolution by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19723 <https://github.com/galaxyproject/galaxy/pull/19723>`_

============
Enhancements
============

* Add bwa_mem2_index directory datatype, framework enhancements for testing directories by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19694 <https://github.com/galaxyproject/galaxy/pull/19694>`_

-------------------
24.2.1 (2025-02-28)
-------------------


=========
Bug fixes
=========

* Updated registration warning message by `@dannon <https://github.com/dannon>`_ in `#19598 <https://github.com/galaxyproject/galaxy/pull/19598>`_

============
Enhancements
============

* Add fastk_ktab_tar datatype required for fastk tool by `@SaimMomin12 <https://github.com/SaimMomin12>`_ in `#19615 <https://github.com/galaxyproject/galaxy/pull/19615>`_

-------------------
24.2.0 (2025-02-11)
-------------------


=========
Bug fixes
=========

* Fix loading error for built in tool `sift` by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#18357 <https://github.com/galaxyproject/galaxy/pull/18357>`_
* Add gtf to auto_compressed_types by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19175 <https://github.com/galaxyproject/galaxy/pull/19175>`_
* Partial backport of #19331 by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19342 <https://github.com/galaxyproject/galaxy/pull/19342>`_
* Fix to only show ChatGXY when available. by `@dannon <https://github.com/dannon>`_ in `#19389 <https://github.com/galaxyproject/galaxy/pull/19389>`_

============
Enhancements
============

* Experimental galactic wizard by `@dannon <https://github.com/dannon>`_ in `#15860 <https://github.com/galaxyproject/galaxy/pull/15860>`_
* Improve usability of Directory datatype by `@wm75 <https://github.com/wm75>`_ in `#17614 <https://github.com/galaxyproject/galaxy/pull/17614>`_
* Add pod5 datatype by `@TomHarrop <https://github.com/TomHarrop>`_ in `#18419 <https://github.com/galaxyproject/galaxy/pull/18419>`_
* Add onedata templates by `@bwalkowi <https://github.com/bwalkowi>`_ in `#18457 <https://github.com/galaxyproject/galaxy/pull/18457>`_
* Support high-availability setups for the interactive tools proxy by `@kysrpex <https://github.com/kysrpex>`_ in `#18481 <https://github.com/galaxyproject/galaxy/pull/18481>`_
* Minor config documentation enhancements by `@bgruening <https://github.com/bgruening>`_ in `#18499 <https://github.com/galaxyproject/galaxy/pull/18499>`_
* Add Tool-Centric APIs to the Tool Shed 2.0 by `@jmchilton <https://github.com/jmchilton>`_ in `#18524 <https://github.com/galaxyproject/galaxy/pull/18524>`_
* Bring your own file sources: Add the WebDAV template and configuration by `@sanjaysrikakulam <https://github.com/sanjaysrikakulam>`_ in `#18598 <https://github.com/galaxyproject/galaxy/pull/18598>`_
* Add BlobToolkit to the list of interactive tools by `@Delphine-L <https://github.com/Delphine-L>`_ in `#18630 <https://github.com/galaxyproject/galaxy/pull/18630>`_
* Remove `defaults` channel for conda usage by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#18757 <https://github.com/galaxyproject/galaxy/pull/18757>`_
* Workflow Landing Requests by `@jmchilton <https://github.com/jmchilton>`_ in `#18807 <https://github.com/galaxyproject/galaxy/pull/18807>`_
* Jupyter Interactive Tool 1.0.1/24.07 by `@natefoo <https://github.com/natefoo>`_ in `#18861 <https://github.com/galaxyproject/galaxy/pull/18861>`_
* Allow setting a few global defaults for file source plugin types. by `@jmchilton <https://github.com/jmchilton>`_ in `#18909 <https://github.com/galaxyproject/galaxy/pull/18909>`_
* Add filter null collection operation tool by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18928 <https://github.com/galaxyproject/galaxy/pull/18928>`_
* Add hint to the tool schema about runtime conditional changes by `@martenson <https://github.com/martenson>`_ in `#18996 <https://github.com/galaxyproject/galaxy/pull/18996>`_
* Irods ssl connection by `@pauldg <https://github.com/pauldg>`_ in `#19014 <https://github.com/galaxyproject/galaxy/pull/19014>`_
* Add some Zarr-based datatypes by `@davelopez <https://github.com/davelopez>`_ in `#19040 <https://github.com/galaxyproject/galaxy/pull/19040>`_
* Run installed Galaxy with no config and a simplified entry point by `@natefoo <https://github.com/natefoo>`_ in `#19050 <https://github.com/galaxyproject/galaxy/pull/19050>`_
* Add XML based `vtk` datatype by `@tStehling <https://github.com/tStehling>`_ in `#19104 <https://github.com/galaxyproject/galaxy/pull/19104>`_
* Allow a posix file source to prefer linking. by `@jmchilton <https://github.com/jmchilton>`_ in `#19132 <https://github.com/galaxyproject/galaxy/pull/19132>`_
* Add bcsp datatype by `@SantaMcCloud <https://github.com/SantaMcCloud>`_ in `#19365 <https://github.com/galaxyproject/galaxy/pull/19365>`_
* add MuData as subclass of H5 by `@pavanvidem <https://github.com/pavanvidem>`_ in `#19416 <https://github.com/galaxyproject/galaxy/pull/19416>`_

-------------------
24.1.4 (2024-12-11)
-------------------


=========
Bug fixes
=========

* Replace busybox:ubuntu-14.04 image with busybox:1.36.1-glibc by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18428 <https://github.com/galaxyproject/galaxy/pull/18428>`_
* Strip whitespace when listifying admin users by `@jdavcs <https://github.com/jdavcs>`_ in `#18656 <https://github.com/galaxyproject/galaxy/pull/18656>`_
* Remove defaults channel for conda usage by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#18859 <https://github.com/galaxyproject/galaxy/pull/18859>`_

============
Enhancements
============

* Make `default_panel_view` a `_by_host` option by `@natefoo <https://github.com/natefoo>`_ in `#18471 <https://github.com/galaxyproject/galaxy/pull/18471>`_
* More datatype deprecation warnings by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18612 <https://github.com/galaxyproject/galaxy/pull/18612>`_
* Implemented the generic OIDC backend from python-social-auth into Gal… by `@Edmontosaurus <https://github.com/Edmontosaurus>`_ in `#18670 <https://github.com/galaxyproject/galaxy/pull/18670>`_

=============
Other changes
=============

* Backport pod5 datatype by `@TomHarrop <https://github.com/TomHarrop>`_ in `#18507 <https://github.com/galaxyproject/galaxy/pull/18507>`_
* Backport PR 18630 "Add BlobToolkit to the list of interactive tools" to release_24.1 by `@cat-bro <https://github.com/cat-bro>`_ in `#18784 <https://github.com/galaxyproject/galaxy/pull/18784>`_

-------------------
24.1.3 (2024-10-25)
-------------------


=========
Bug fixes
=========

* Replace busybox:ubuntu-14.04 image with busybox:1.36.1-glibc by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18428 <https://github.com/galaxyproject/galaxy/pull/18428>`_
* Strip whitespace when listifying admin users by `@jdavcs <https://github.com/jdavcs>`_ in `#18656 <https://github.com/galaxyproject/galaxy/pull/18656>`_
* Remove defaults channel for conda usage by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#18859 <https://github.com/galaxyproject/galaxy/pull/18859>`_

============
Enhancements
============

* Make `default_panel_view` a `_by_host` option by `@natefoo <https://github.com/natefoo>`_ in `#18471 <https://github.com/galaxyproject/galaxy/pull/18471>`_
* More datatype deprecation warnings by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18612 <https://github.com/galaxyproject/galaxy/pull/18612>`_
* Implemented the generic OIDC backend from python-social-auth into Gal… by `@Edmontosaurus <https://github.com/Edmontosaurus>`_ in `#18670 <https://github.com/galaxyproject/galaxy/pull/18670>`_

=============
Other changes
=============

* Backport pod5 datatype by `@TomHarrop <https://github.com/TomHarrop>`_ in `#18507 <https://github.com/galaxyproject/galaxy/pull/18507>`_
* Backport PR 18630 "Add BlobToolkit to the list of interactive tools" to release_24.1 by `@cat-bro <https://github.com/cat-bro>`_ in `#18784 <https://github.com/galaxyproject/galaxy/pull/18784>`_

-------------------
24.1.2 (2024-09-25)
-------------------


=========
Bug fixes
=========

* Strip whitespace when listifying admin users by `@jdavcs <https://github.com/jdavcs>`_ in `#18656 <https://github.com/galaxyproject/galaxy/pull/18656>`_

============
Enhancements
============

* Make `default_panel_view` a `_by_host` option by `@natefoo <https://github.com/natefoo>`_ in `#18471 <https://github.com/galaxyproject/galaxy/pull/18471>`_
* More datatype deprecation warnings by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18612 <https://github.com/galaxyproject/galaxy/pull/18612>`_
* Implemented the generic OIDC backend from python-social-auth into Gal… by `@Edmontosaurus <https://github.com/Edmontosaurus>`_ in `#18670 <https://github.com/galaxyproject/galaxy/pull/18670>`_

=============
Other changes
=============

* Backport pod5 datatype by `@TomHarrop <https://github.com/TomHarrop>`_ in `#18507 <https://github.com/galaxyproject/galaxy/pull/18507>`_
* Backport PR 18630 "Add BlobToolkit to the list of interactive tools" to release_24.1 by `@cat-bro <https://github.com/cat-bro>`_ in `#18784 <https://github.com/galaxyproject/galaxy/pull/18784>`_

-------------------
24.1.1 (2024-07-02)
-------------------


=========
Bug fixes
=========

* Replace sample Celery result_backend in config by `@davelopez <https://github.com/davelopez>`_ in `#17949 <https://github.com/galaxyproject/galaxy/pull/17949>`_
* Fix for unexpected OIDC XML validation error by `@Edmontosaurus <https://github.com/Edmontosaurus>`_ in `#18106 <https://github.com/galaxyproject/galaxy/pull/18106>`_
* Fix various packages' issues by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18301 <https://github.com/galaxyproject/galaxy/pull/18301>`_
* Rebuild Galaxy config by `@bgruening <https://github.com/bgruening>`_ in `#18325 <https://github.com/galaxyproject/galaxy/pull/18325>`_

============
Enhancements
============

* Enable all-vs-all collection analysis patterns. by `@jmchilton <https://github.com/jmchilton>`_ in `#17366 <https://github.com/galaxyproject/galaxy/pull/17366>`_
* Add onedata objectstore by `@bwalkowi <https://github.com/bwalkowi>`_ in `#17540 <https://github.com/galaxyproject/galaxy/pull/17540>`_
* Add colabfold tar file datatype by `@astrovsky01 <https://github.com/astrovsky01>`_ in `#17567 <https://github.com/galaxyproject/galaxy/pull/17567>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#17653 <https://github.com/galaxyproject/galaxy/pull/17653>`_
* SQLAlchemy 2.0 by `@jdavcs <https://github.com/jdavcs>`_ in `#17778 <https://github.com/galaxyproject/galaxy/pull/17778>`_
* Add `email` notifications channel by `@davelopez <https://github.com/davelopez>`_ in `#17914 <https://github.com/galaxyproject/galaxy/pull/17914>`_
* Update config docs about Celery by `@davelopez <https://github.com/davelopez>`_ in `#17918 <https://github.com/galaxyproject/galaxy/pull/17918>`_
* Make urgent notifications mandatory by `@davelopez <https://github.com/davelopez>`_ in `#17975 <https://github.com/galaxyproject/galaxy/pull/17975>`_
* Enable ``warn_unused_ignores`` mypy option by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17991 <https://github.com/galaxyproject/galaxy/pull/17991>`_
* Add Zenodo integration by `@davelopez <https://github.com/davelopez>`_ in `#18022 <https://github.com/galaxyproject/galaxy/pull/18022>`_
* Add support for additional media types by `@arash77 <https://github.com/arash77>`_ in `#18054 <https://github.com/galaxyproject/galaxy/pull/18054>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#18063 <https://github.com/galaxyproject/galaxy/pull/18063>`_
* Add Net datatype by `@martenson <https://github.com/martenson>`_ in `#18080 <https://github.com/galaxyproject/galaxy/pull/18080>`_
* Empower users to bring their own storage and file sources by `@jmchilton <https://github.com/jmchilton>`_ in `#18127 <https://github.com/galaxyproject/galaxy/pull/18127>`_
* More unit testing for object store stuff. by `@jmchilton <https://github.com/jmchilton>`_ in `#18136 <https://github.com/galaxyproject/galaxy/pull/18136>`_
* Tighten axt sniffer by `@martenson <https://github.com/martenson>`_ in `#18204 <https://github.com/galaxyproject/galaxy/pull/18204>`_
* More structured indexing for user data objects. by `@jmchilton <https://github.com/jmchilton>`_ in `#18291 <https://github.com/galaxyproject/galaxy/pull/18291>`_
* Onedada object store and files source stability fixes by `@bwalkowi <https://github.com/bwalkowi>`_ in `#18372 <https://github.com/galaxyproject/galaxy/pull/18372>`_

=============
Other changes
=============

* Chore: remove repetitive words by `@tianzedavid <https://github.com/tianzedavid>`_ in `#18076 <https://github.com/galaxyproject/galaxy/pull/18076>`_
* Fix the link to the carbon config by `@bgruening <https://github.com/bgruening>`_ in `#18314 <https://github.com/galaxyproject/galaxy/pull/18314>`_

-------------------
24.0.3 (2024-06-28)
-------------------


=========
Bug fixes
=========

* Backport OIDC schema fix by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18111 <https://github.com/galaxyproject/galaxy/pull/18111>`_
* Minor fix to enable external hgweb process by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18256 <https://github.com/galaxyproject/galaxy/pull/18256>`_

=============
Other changes
=============

* Replace busybox:ubuntu-14.04 image with busybox:1.36.1-glibc by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18428 <https://github.com/galaxyproject/galaxy/pull/18428>`_

-------------------
24.0.2 (2024-05-07)
-------------------

No recorded changes since last release

-------------------
24.0.1 (2024-05-02)
-------------------


=========
Bug fixes
=========

* Invenio plugin fixes by `@davelopez <https://github.com/davelopez>`_ in `#17997 <https://github.com/galaxyproject/galaxy/pull/17997>`_
* clarify the object store relocate functionality by `@martenson <https://github.com/martenson>`_ in `#18033 <https://github.com/galaxyproject/galaxy/pull/18033>`_
* Updated the datatypes name for FASTK tool by `@SaimMomin12 <https://github.com/SaimMomin12>`_ in `#18053 <https://github.com/galaxyproject/galaxy/pull/18053>`_

============
Enhancements
============

* Added 4dn_pairs and 4dn_pairsam datatypes by `@SaimMomin12 <https://github.com/SaimMomin12>`_ in `#17875 <https://github.com/galaxyproject/galaxy/pull/17875>`_
* Add middleware for logging start and end of request by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18046 <https://github.com/galaxyproject/galaxy/pull/18046>`_

=============
Other changes
=============

* Rebuild config samples by `@davelopez <https://github.com/davelopez>`_ in `#17911 <https://github.com/galaxyproject/galaxy/pull/17911>`_
* Backport colabfold tar file datatype by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18029 <https://github.com/galaxyproject/galaxy/pull/18029>`_

-------------------
24.0.0 (2024-04-02)
-------------------


=========
Bug fixes
=========

* Follow-up on #17274 and #17262 by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17302 <https://github.com/galaxyproject/galaxy/pull/17302>`_
* Fix minor oidc_backends_config comment bug by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#17385 <https://github.com/galaxyproject/galaxy/pull/17385>`_

============
Enhancements
============

* Add harmonize collections tool (or whatever other name) by `@lldelisle <https://github.com/lldelisle>`_ in `#16662 <https://github.com/galaxyproject/galaxy/pull/16662>`_
* Python 3.8 as minimum by `@mr-c <https://github.com/mr-c>`_ in `#16954 <https://github.com/galaxyproject/galaxy/pull/16954>`_
* Support for OIDC API Auth and OIDC integration tests by `@nuwang <https://github.com/nuwang>`_ in `#16977 <https://github.com/galaxyproject/galaxy/pull/16977>`_
* Add support for (fast5.tar).xz binary compressed files by `@tuncK <https://github.com/tuncK>`_ in `#17106 <https://github.com/galaxyproject/galaxy/pull/17106>`_
* Add a3m datatype by `@astrovsky01 <https://github.com/astrovsky01>`_ in `#17217 <https://github.com/galaxyproject/galaxy/pull/17217>`_
* Convert sample object store configuration to YAML and support configuring inline by `@natefoo <https://github.com/natefoo>`_ in `#17222 <https://github.com/galaxyproject/galaxy/pull/17222>`_
* Allow job files to consume TUS uploads by `@jmchilton <https://github.com/jmchilton>`_ in `#17242 <https://github.com/galaxyproject/galaxy/pull/17242>`_
* Add OIDC backend configuration schema and validation by `@uwwint <https://github.com/uwwint>`_ in `#17274 <https://github.com/galaxyproject/galaxy/pull/17274>`_
* Update to black 2024 stable style by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17391 <https://github.com/galaxyproject/galaxy/pull/17391>`_
* Allow using tool data bundles as inputs to reference data select parameters by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17435 <https://github.com/galaxyproject/galaxy/pull/17435>`_
* Use short link for TPV shared database by `@nuwang <https://github.com/nuwang>`_ in `#17467 <https://github.com/galaxyproject/galaxy/pull/17467>`_
* Feature SBOL datatypes by `@guillaume-gricourt <https://github.com/guillaume-gricourt>`_ in `#17482 <https://github.com/galaxyproject/galaxy/pull/17482>`_
* Add documentation on how to use vault keys in file sources by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#17498 <https://github.com/galaxyproject/galaxy/pull/17498>`_
* add npy datatype by `@astrovsky01 <https://github.com/astrovsky01>`_ in `#17517 <https://github.com/galaxyproject/galaxy/pull/17517>`_
* Enhance Avivator display app to support regular Tiffs by `@davelopez <https://github.com/davelopez>`_ in `#17554 <https://github.com/galaxyproject/galaxy/pull/17554>`_
* Allow admin to sharpen language about selected object stores. by `@jmchilton <https://github.com/jmchilton>`_ in `#17806 <https://github.com/galaxyproject/galaxy/pull/17806>`_

-------------------
23.2.1 (2024-02-21)
-------------------


=========
Bug fixes
=========

* pin fs.dropboxfs to >=1 by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#16451 <https://github.com/galaxyproject/galaxy/pull/16451>`_
* MINERVA display application: enable cors, add for tabular by `@hexylena <https://github.com/hexylena>`_ in `#16737 <https://github.com/galaxyproject/galaxy/pull/16737>`_
* chore: fix typos by `@afuetterer <https://github.com/afuetterer>`_ in `#16851 <https://github.com/galaxyproject/galaxy/pull/16851>`_
* Add back 1.1.0 version of Filtering1 tool by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16883 <https://github.com/galaxyproject/galaxy/pull/16883>`_
* Set webdav file source to use temp files by default by `@davelopez <https://github.com/davelopez>`_ in `#17388 <https://github.com/galaxyproject/galaxy/pull/17388>`_

============
Enhancements
============

* Update cellxgene interactive tool to 1.1.1 by `@pcm32 <https://github.com/pcm32>`_ in `#15313 <https://github.com/galaxyproject/galaxy/pull/15313>`_
* Tool Shed 2.0 by `@jmchilton <https://github.com/jmchilton>`_ in `#15639 <https://github.com/galaxyproject/galaxy/pull/15639>`_
* Limit number of celery task executions per second per user by `@claudiofr <https://github.com/claudiofr>`_ in `#16232 <https://github.com/galaxyproject/galaxy/pull/16232>`_
* Add carbon emissions admin configuration options by `@Renni771 <https://github.com/Renni771>`_ in `#16307 <https://github.com/galaxyproject/galaxy/pull/16307>`_
* Add Invenio RDM repository integration by `@davelopez <https://github.com/davelopez>`_ in `#16381 <https://github.com/galaxyproject/galaxy/pull/16381>`_
* Add new datatype: STL by `@TanguyGen <https://github.com/TanguyGen>`_ in `#16478 <https://github.com/galaxyproject/galaxy/pull/16478>`_
* add new tabular file formats cns,cnr and cnn to datatypes_conf.xml.sample file as they are neaded for cnvkit galaxy tools by `@khaled196 <https://github.com/khaled196>`_ in `#16503 <https://github.com/galaxyproject/galaxy/pull/16503>`_
* Tweak tool memory use and optimize shared memory when using preload by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16536 <https://github.com/galaxyproject/galaxy/pull/16536>`_
* Implement datatype upload warnings by `@jmchilton <https://github.com/jmchilton>`_ in `#16564 <https://github.com/galaxyproject/galaxy/pull/16564>`_
* Support new genome browser chain file format by `@claudiofr <https://github.com/claudiofr>`_ in `#16576 <https://github.com/galaxyproject/galaxy/pull/16576>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#16577 <https://github.com/galaxyproject/galaxy/pull/16577>`_
* Implement instance URLs in Galaxy markdown. by `@jmchilton <https://github.com/jmchilton>`_ in `#16675 <https://github.com/galaxyproject/galaxy/pull/16675>`_
* Use fs.onedatarestfs for Onedata files source plugin implementation by `@lopiola <https://github.com/lopiola>`_ in `#16690 <https://github.com/galaxyproject/galaxy/pull/16690>`_
* Update datatypes_conf.xml.sample with docx type by `@yvanlebras <https://github.com/yvanlebras>`_ in `#16713 <https://github.com/galaxyproject/galaxy/pull/16713>`_
* Replace ELIXIR AAI button with Life Science login by `@sebastian-schaaf <https://github.com/sebastian-schaaf>`_ in `#16762 <https://github.com/galaxyproject/galaxy/pull/16762>`_
* Add EGI Check-in as OIDC authentication option by `@enolfc <https://github.com/enolfc>`_ in `#16782 <https://github.com/galaxyproject/galaxy/pull/16782>`_
* Updated path-based interactive tools with entry point path injection, support for ITs with relative links, shortened URLs, doc and config updates including Podman job_conf by `@sveinugu <https://github.com/sveinugu>`_ in `#16795 <https://github.com/galaxyproject/galaxy/pull/16795>`_
* Galaxy help forum integration by `@ElectronicBlueberry <https://github.com/ElectronicBlueberry>`_ in `#16798 <https://github.com/galaxyproject/galaxy/pull/16798>`_
* Remove record access handling for Invenio RDM plugin by `@davelopez <https://github.com/davelopez>`_ in `#16900 <https://github.com/galaxyproject/galaxy/pull/16900>`_
* optimize object store cache operations by `@SergeyYakubov <https://github.com/SergeyYakubov>`_ in `#17025 <https://github.com/galaxyproject/galaxy/pull/17025>`_
* Support configuring job metrics inline, update documentation by `@natefoo <https://github.com/natefoo>`_ in `#17178 <https://github.com/galaxyproject/galaxy/pull/17178>`_
* Add binary datatypes for intermediate output of fastk tools by `@astrovsky01 <https://github.com/astrovsky01>`_ in `#17265 <https://github.com/galaxyproject/galaxy/pull/17265>`_
* Add magres datatype by `@martenson <https://github.com/martenson>`_ in `#17499 <https://github.com/galaxyproject/galaxy/pull/17499>`_

=============
Other changes
=============

* Merge 23.1 into dev by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16534 <https://github.com/galaxyproject/galaxy/pull/16534>`_
* Remove xml remnant in sample yml job conf by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#16609 <https://github.com/galaxyproject/galaxy/pull/16609>`_

-------------------
23.1.4 (2024-01-04)
-------------------

No recorded changes since last release

-------------------
23.1.3 (2023-12-01)
-------------------

No recorded changes since last release

-------------------
23.1.2 (2023-11-29)
-------------------


=========
Bug fixes
=========

* Prevent Singular external auth users from disconnecting identity by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#16961 <https://github.com/galaxyproject/galaxy/pull/16961>`_
* Set correct tool_path for packaged galaxy by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17102 <https://github.com/galaxyproject/galaxy/pull/17102>`_

============
Enhancements
============

* Add support for larch datatypes by `@patrick-austin <https://github.com/patrick-austin>`_ in `#17080 <https://github.com/galaxyproject/galaxy/pull/17080>`_

-------------------
23.1.1 (2023-10-23)
-------------------


=========
Bug fixes
=========

* Fix some drs handling issues by `@nuwang <https://github.com/nuwang>`_ in `#15777 <https://github.com/galaxyproject/galaxy/pull/15777>`_
* Improve container resolver documentation by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16280 <https://github.com/galaxyproject/galaxy/pull/16280>`_
* Limit tool document cache to tool configs with explicit cache path by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16537 <https://github.com/galaxyproject/galaxy/pull/16537>`_
* Backport tool mem fixes by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16601 <https://github.com/galaxyproject/galaxy/pull/16601>`_
* Fix allowlist deserialization in file sources by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16729 <https://github.com/galaxyproject/galaxy/pull/16729>`_

============
Enhancements
============

* External Login Flow: Redirect users if account already exists by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#15019 <https://github.com/galaxyproject/galaxy/pull/15019>`_
* Add slack error reporting plugin by `@hexylena <https://github.com/hexylena>`_ in `#15025 <https://github.com/galaxyproject/galaxy/pull/15025>`_
* Documents use of k8s_extra_job_envs in job_conf sample advanced by `@pcm32 <https://github.com/pcm32>`_ in `#15110 <https://github.com/galaxyproject/galaxy/pull/15110>`_
* Expose additional beaker caching backends  by `@claudiofr <https://github.com/claudiofr>`_ in `#15349 <https://github.com/galaxyproject/galaxy/pull/15349>`_
* Unify url handling with filesources by `@nuwang <https://github.com/nuwang>`_ in `#15497 <https://github.com/galaxyproject/galaxy/pull/15497>`_
* Handle "email_from" config option consistently, as per schema description by `@jdavcs <https://github.com/jdavcs>`_ in `#15557 <https://github.com/galaxyproject/galaxy/pull/15557>`_
* Drop workflow exports to myexperiment.org by `@dannon <https://github.com/dannon>`_ in `#15576 <https://github.com/galaxyproject/galaxy/pull/15576>`_
* Container resolvers: add docs, typing and tests by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#15614 <https://github.com/galaxyproject/galaxy/pull/15614>`_
* Add suggested Training material to Tool Form by `@ElectronicBlueberry <https://github.com/ElectronicBlueberry>`_ in `#15628 <https://github.com/galaxyproject/galaxy/pull/15628>`_
* Deprecate tools/evolution by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#15656 <https://github.com/galaxyproject/galaxy/pull/15656>`_
* Add Galaxy Notification System by `@davelopez <https://github.com/davelopez>`_ in `#15663 <https://github.com/galaxyproject/galaxy/pull/15663>`_
* More object store documentation. by `@jmchilton <https://github.com/jmchilton>`_ in `#15707 <https://github.com/galaxyproject/galaxy/pull/15707>`_
* Drop use_legacy_history from config  by `@dannon <https://github.com/dannon>`_ in `#15861 <https://github.com/galaxyproject/galaxy/pull/15861>`_
* FITS data format by `@volodymyrss <https://github.com/volodymyrss>`_ in `#15905 <https://github.com/galaxyproject/galaxy/pull/15905>`_
* Export tool citations configurable message by `@minh-biocommons <https://github.com/minh-biocommons>`_ in `#15998 <https://github.com/galaxyproject/galaxy/pull/15998>`_
* Rename object stores in config. by `@jmchilton <https://github.com/jmchilton>`_ in `#16029 <https://github.com/galaxyproject/galaxy/pull/16029>`_
* Add hdf4 datatype by `@TheoMathurin <https://github.com/TheoMathurin>`_ in `#16105 <https://github.com/galaxyproject/galaxy/pull/16105>`_
* Improved Cache Monitoring for Object Stores by `@jmchilton <https://github.com/jmchilton>`_ in `#16110 <https://github.com/galaxyproject/galaxy/pull/16110>`_
* Refactor caching object stores ahead of adding task-based store. by `@jmchilton <https://github.com/jmchilton>`_ in `#16144 <https://github.com/galaxyproject/galaxy/pull/16144>`_
* Add zipped mongodb and genenotebook datatypes by `@abretaud <https://github.com/abretaud>`_ in `#16173 <https://github.com/galaxyproject/galaxy/pull/16173>`_
* Add Visium datatype for squidpy and spatialomics tools by `@astrovsky01 <https://github.com/astrovsky01>`_ in `#16255 <https://github.com/galaxyproject/galaxy/pull/16255>`_

=============
Other changes
=============

* Implement some initial object store selection end-to-end tests. by `@jmchilton <https://github.com/jmchilton>`_ in `#15785 <https://github.com/galaxyproject/galaxy/pull/15785>`_

-------------------
23.0.6 (2023-10-23)
-------------------

No recorded changes since last release

-------------------
23.0.5 (2023-07-29)
-------------------


=========
Bug fixes
=========

* Minor bug fix for default mail templates by `@neoformit <https://github.com/neoformit>`_ in `#16362 <https://github.com/galaxyproject/galaxy/pull/16362>`_

-------------------
23.0.4 (2023-06-30)
-------------------

No recorded changes since last release

-------------------
23.0.3 (2023-06-26)
-------------------

No recorded changes since last release

-------------------
23.0.2 (2023-06-13)
-------------------

No recorded changes since last release

-------------------
23.0.1 (2023-06-08)
-------------------


=========
Bug fixes
=========

* Change default watchdog inotify_buffer log level to info by `@mvdbeek <https://github.com/mvdbeek>`_ in `#15967 <https://github.com/galaxyproject/galaxy/pull/15967>`_

============
Enhancements
============

* Add ``ca_certs`` option for sentry client by `@mvdbeek <https://github.com/mvdbeek>`_ in `#15943 <https://github.com/galaxyproject/galaxy/pull/15943>`_

-------------------
22.1.1 (2022-08-22)
-------------------

* Initial release
