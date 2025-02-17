History
-------

.. to_doc

---------
25.0.dev0
---------



-------------------
24.2.0 (2025-02-11)
-------------------


=========
Bug fixes
=========

* Fix some deprecations by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18433 <https://github.com/galaxyproject/galaxy/pull/18433>`_
* Fix handling of v2 hashes by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#18522 <https://github.com/galaxyproject/galaxy/pull/18522>`_
* Fixes for errors reported by mypy 1.11.0 by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18608 <https://github.com/galaxyproject/galaxy/pull/18608>`_
* Handle output parsing when tool is not available for tool-centric API. by `@jmchilton <https://github.com/jmchilton>`_ in `#18643 <https://github.com/galaxyproject/galaxy/pull/18643>`_
* Fix new flake8-bugbear B039 and mypy type-var errors by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18755 <https://github.com/galaxyproject/galaxy/pull/18755>`_
* Fix commas that shouldn't be in biotools_mappings.tsv by `@jmchilton <https://github.com/jmchilton>`_ in `#18919 <https://github.com/galaxyproject/galaxy/pull/18919>`_
* Allow modes `z` and `Z` for docker volumes by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#18998 <https://github.com/galaxyproject/galaxy/pull/18998>`_
* Add requirement/resource to schema docs by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#19172 <https://github.com/galaxyproject/galaxy/pull/19172>`_
* Fix mulled_hash by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#19199 <https://github.com/galaxyproject/galaxy/pull/19199>`_
* Outputs filter linter fixes by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#19208 <https://github.com/galaxyproject/galaxy/pull/19208>`_
* Replace mambaforge Docker image with miniforge3 by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19327 <https://github.com/galaxyproject/galaxy/pull/19327>`_
* Partial backport of #19331 by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19342 <https://github.com/galaxyproject/galaxy/pull/19342>`_
* Backport fix for ``test_singularity_container_test`` test by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19349 <https://github.com/galaxyproject/galaxy/pull/19349>`_
* Remove unnecessary quoting in conda package specification by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19382 <https://github.com/galaxyproject/galaxy/pull/19382>`_
* Fix timeout handling for planemo / galaxy-tool-util by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19384 <https://github.com/galaxyproject/galaxy/pull/19384>`_
* Fix for empty string in regex validator message. by `@jmchilton <https://github.com/jmchilton>`_ in `#19387 <https://github.com/galaxyproject/galaxy/pull/19387>`_
* `mulled-build-tool` fix for packages wo version by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#19450 <https://github.com/galaxyproject/galaxy/pull/19450>`_
* Fix parsing of validators with inf limits by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19459 <https://github.com/galaxyproject/galaxy/pull/19459>`_
* Remove print statement by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#19469 <https://github.com/galaxyproject/galaxy/pull/19469>`_
* Downgrade 'InteractiveTools are not enabled' to warning by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19518 <https://github.com/galaxyproject/galaxy/pull/19518>`_

============
Enhancements
============

* Add linters for datatypes by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#17600 <https://github.com/galaxyproject/galaxy/pull/17600>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#18406 <https://github.com/galaxyproject/galaxy/pull/18406>`_
* Stray small changes from structured_tool_state branch. by `@jmchilton <https://github.com/jmchilton>`_ in `#18453 <https://github.com/galaxyproject/galaxy/pull/18453>`_
* Add Tool-Centric APIs to the Tool Shed 2.0 by `@jmchilton <https://github.com/jmchilton>`_ in `#18524 <https://github.com/galaxyproject/galaxy/pull/18524>`_
* Mixed enhancements from CWL branch by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18539 <https://github.com/galaxyproject/galaxy/pull/18539>`_
* Implement Declarative Testing for Workflow Behaviors by `@jmchilton <https://github.com/jmchilton>`_ in `#18542 <https://github.com/galaxyproject/galaxy/pull/18542>`_
* Improvements to Tool Test Parsing by `@jmchilton <https://github.com/jmchilton>`_ in `#18560 <https://github.com/galaxyproject/galaxy/pull/18560>`_
* More tool test typing. by `@jmchilton <https://github.com/jmchilton>`_ in `#18590 <https://github.com/galaxyproject/galaxy/pull/18590>`_
* Parameter Model Improvements by `@jmchilton <https://github.com/jmchilton>`_ in `#18641 <https://github.com/galaxyproject/galaxy/pull/18641>`_
* Another round of parameter model improvements. by `@jmchilton <https://github.com/jmchilton>`_ in `#18673 <https://github.com/galaxyproject/galaxy/pull/18673>`_
* De-couple XML from tool interface for test collections. by `@jmchilton <https://github.com/jmchilton>`_ in `#18676 <https://github.com/galaxyproject/galaxy/pull/18676>`_
* Another round of parameter model enhancements and tool tests by `@jmchilton <https://github.com/jmchilton>`_ in `#18678 <https://github.com/galaxyproject/galaxy/pull/18678>`_
* Dynamic Models for Tool Test Validation by `@jmchilton <https://github.com/jmchilton>`_ in `#18679 <https://github.com/galaxyproject/galaxy/pull/18679>`_
* Improvements to help terms & tool help. by `@jmchilton <https://github.com/jmchilton>`_ in `#18722 <https://github.com/galaxyproject/galaxy/pull/18722>`_
* Implement tool upgrade assistant. by `@jmchilton <https://github.com/jmchilton>`_ in `#18728 <https://github.com/galaxyproject/galaxy/pull/18728>`_
* Improvements to parameter models for test case inputs by `@jmchilton <https://github.com/jmchilton>`_ in `#18743 <https://github.com/galaxyproject/galaxy/pull/18743>`_
* Remove `defaults` channel for conda usage by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#18757 <https://github.com/galaxyproject/galaxy/pull/18757>`_
* Modelling for Test Assertions by `@jmchilton <https://github.com/jmchilton>`_ in `#18787 <https://github.com/galaxyproject/galaxy/pull/18787>`_
* Workflow Landing Requests by `@jmchilton <https://github.com/jmchilton>`_ in `#18807 <https://github.com/galaxyproject/galaxy/pull/18807>`_
* Add docs on indexing for filter column by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#18844 <https://github.com/galaxyproject/galaxy/pull/18844>`_
* Implement Pydantic model for workflow test format.  by `@jmchilton <https://github.com/jmchilton>`_ in `#18884 <https://github.com/galaxyproject/galaxy/pull/18884>`_
* Improvements to Planemo test format based on feedback/discussions. by `@jmchilton <https://github.com/jmchilton>`_ in `#18889 <https://github.com/galaxyproject/galaxy/pull/18889>`_
* Add support for arbitrarily ordered image axes in image content assertions by `@kostrykin <https://github.com/kostrykin>`_ in `#18891 <https://github.com/galaxyproject/galaxy/pull/18891>`_
* Remove some unused dynamic drill down options. by `@jmchilton <https://github.com/jmchilton>`_ in `#18892 <https://github.com/galaxyproject/galaxy/pull/18892>`_
* Type annotations and fixes by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18911 <https://github.com/galaxyproject/galaxy/pull/18911>`_
* Add filter null collection operation tool by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18928 <https://github.com/galaxyproject/galaxy/pull/18928>`_
* Assert that `data_column` parameters have a valid `data_ref` by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#18949 <https://github.com/galaxyproject/galaxy/pull/18949>`_
* More concise, readable tool execution testing. by `@jmchilton <https://github.com/jmchilton>`_ in `#18977 <https://github.com/galaxyproject/galaxy/pull/18977>`_
* Workflow landing improvements by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18979 <https://github.com/galaxyproject/galaxy/pull/18979>`_
* Add hint to the tool schema about runtime conditional changes by `@martenson <https://github.com/martenson>`_ in `#18996 <https://github.com/galaxyproject/galaxy/pull/18996>`_
* A variety of improvements around tool parameter modeling (second try) by `@jmchilton <https://github.com/jmchilton>`_ in `#19027 <https://github.com/galaxyproject/galaxy/pull/19027>`_
* Better logging around tool loading by `@jmchilton <https://github.com/jmchilton>`_ in `#19029 <https://github.com/galaxyproject/galaxy/pull/19029>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#19031 <https://github.com/galaxyproject/galaxy/pull/19031>`_
* Integrate Tool Parameter Modeling into Linting (for Planemo) by `@jmchilton <https://github.com/jmchilton>`_ in `#19073 <https://github.com/galaxyproject/galaxy/pull/19073>`_
* Allow deferred datasets to behave as URIs by `@davelopez <https://github.com/davelopez>`_ in `#19077 <https://github.com/galaxyproject/galaxy/pull/19077>`_
* Implement workflow parameter validators. by `@jmchilton <https://github.com/jmchilton>`_ in `#19092 <https://github.com/galaxyproject/galaxy/pull/19092>`_
* Enable specifying dataset hash in test jobs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19113 <https://github.com/galaxyproject/galaxy/pull/19113>`_
* Add linter to check validity of output filters by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#19114 <https://github.com/galaxyproject/galaxy/pull/19114>`_
* Also use miniforge docker for container building by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#19128 <https://github.com/galaxyproject/galaxy/pull/19128>`_
* Fix default value handling for parameters connected to required parameters by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19219 <https://github.com/galaxyproject/galaxy/pull/19219>`_

-------------------
24.1.4 (2024-12-11)
-------------------


=========
Bug fixes
=========

* Handle all requests error in ``ApiBiotoolsMetadataSource._raw_get_metadata`` by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18510 <https://github.com/galaxyproject/galaxy/pull/18510>`_
* xsd: allow `change_format` and `actions` also in statically defined collection elements, and break recursion by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#18605 <https://github.com/galaxyproject/galaxy/pull/18605>`_
* Remove defaults channel for conda usage by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#18859 <https://github.com/galaxyproject/galaxy/pull/18859>`_
* Don't check availability of shellescape by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18954 <https://github.com/galaxyproject/galaxy/pull/18954>`_
* Backport 2 CI fixes by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18973 <https://github.com/galaxyproject/galaxy/pull/18973>`_
* Disable locking when opening h5 files, add missing ``with`` by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18976 <https://github.com/galaxyproject/galaxy/pull/18976>`_
* Fix extra call to test_data_path that requires an admin key by `@jmchilton <https://github.com/jmchilton>`_ in `#19011 <https://github.com/galaxyproject/galaxy/pull/19011>`_
* flip default value for use_mamba to false by `@bgruening <https://github.com/bgruening>`_ in `#19295 <https://github.com/galaxyproject/galaxy/pull/19295>`_
* Linter: allow dynamic option definition by from_url by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#19300 <https://github.com/galaxyproject/galaxy/pull/19300>`_

============
Enhancements
============

* Make `default_panel_view` a `_by_host` option by `@natefoo <https://github.com/natefoo>`_ in `#18471 <https://github.com/galaxyproject/galaxy/pull/18471>`_

-------------------
24.1.3 (2024-10-25)
-------------------


=========
Bug fixes
=========

* Handle all requests error in ``ApiBiotoolsMetadataSource._raw_get_metadata`` by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18510 <https://github.com/galaxyproject/galaxy/pull/18510>`_
* xsd: allow `change_format` and `actions` also in statically defined collection elements, and break recursion by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#18605 <https://github.com/galaxyproject/galaxy/pull/18605>`_
* Remove defaults channel for conda usage by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#18859 <https://github.com/galaxyproject/galaxy/pull/18859>`_
* Don't check availability of shellescape by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18954 <https://github.com/galaxyproject/galaxy/pull/18954>`_
* Backport 2 CI fixes by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18973 <https://github.com/galaxyproject/galaxy/pull/18973>`_
* Disable locking when opening h5 files, add missing ``with`` by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18976 <https://github.com/galaxyproject/galaxy/pull/18976>`_
* Fix extra call to test_data_path that requires an admin key by `@jmchilton <https://github.com/jmchilton>`_ in `#19011 <https://github.com/galaxyproject/galaxy/pull/19011>`_

============
Enhancements
============

* Make `default_panel_view` a `_by_host` option by `@natefoo <https://github.com/natefoo>`_ in `#18471 <https://github.com/galaxyproject/galaxy/pull/18471>`_

-------------------
24.1.2 (2024-09-25)
-------------------


=========
Bug fixes
=========

* Handle all requests error in ``ApiBiotoolsMetadataSource._raw_get_metadata`` by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18510 <https://github.com/galaxyproject/galaxy/pull/18510>`_
* xsd: allow `change_format` and `actions` also in statically defined collection elements, and break recursion by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#18605 <https://github.com/galaxyproject/galaxy/pull/18605>`_

============
Enhancements
============

* Make `default_panel_view` a `_by_host` option by `@natefoo <https://github.com/natefoo>`_ in `#18471 <https://github.com/galaxyproject/galaxy/pull/18471>`_

-------------------
24.1.1 (2024-07-02)
-------------------


=========
Bug fixes
=========

* Fix bug in galaxy.xsd by `@kostrykin <https://github.com/kostrykin>`_ in `#17752 <https://github.com/galaxyproject/galaxy/pull/17752>`_
* Fix bug in `assert_has_image_n_labels` by `@kostrykin <https://github.com/kostrykin>`_ in `#17754 <https://github.com/galaxyproject/galaxy/pull/17754>`_
* Remove linter for unstripped text content for tool xml leaves by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#18252 <https://github.com/galaxyproject/galaxy/pull/18252>`_

============
Enhancements
============

* Add test and doc showing how dynamic selects are used by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#16885 <https://github.com/galaxyproject/galaxy/pull/16885>`_
* Add content assertion XML tags for test output verification using images by `@kostrykin <https://github.com/kostrykin>`_ in `#17581 <https://github.com/galaxyproject/galaxy/pull/17581>`_
* Set minimal metadata also for empty bed datasets by `@wm75 <https://github.com/wm75>`_ in `#17586 <https://github.com/galaxyproject/galaxy/pull/17586>`_
* Automatically bind `galaxy_data_manager_data_path` in containers by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#17596 <https://github.com/galaxyproject/galaxy/pull/17596>`_
* Type annotation improvements by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17601 <https://github.com/galaxyproject/galaxy/pull/17601>`_
* Type annotation and CWL-related improvements by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17630 <https://github.com/galaxyproject/galaxy/pull/17630>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#17653 <https://github.com/galaxyproject/galaxy/pull/17653>`_
* Code cleanups from ruff and pyupgrade by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17654 <https://github.com/galaxyproject/galaxy/pull/17654>`_
* Tool linter: check for valid bio.tools entries by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#17655 <https://github.com/galaxyproject/galaxy/pull/17655>`_
* Tool linter: check for leaf nodes with unstripped text content by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#17656 <https://github.com/galaxyproject/galaxy/pull/17656>`_
* Issue #17631: Make it possible to use custom invfile.lua if needed by `@martin-g <https://github.com/martin-g>`_ in `#17693 <https://github.com/galaxyproject/galaxy/pull/17693>`_
* SQLAlchemy 2.0 by `@jdavcs <https://github.com/jdavcs>`_ in `#17778 <https://github.com/galaxyproject/galaxy/pull/17778>`_
* Add support for floating point TIFF files in verification of image-based tool outputs by `@kostrykin <https://github.com/kostrykin>`_ in `#17797 <https://github.com/galaxyproject/galaxy/pull/17797>`_
* Add tool linting for valid EDAM terms by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#17839 <https://github.com/galaxyproject/galaxy/pull/17839>`_
* Add `pin_labels` attribute for `image_diff` comparison method by `@kostrykin <https://github.com/kostrykin>`_ in `#17866 <https://github.com/galaxyproject/galaxy/pull/17866>`_
* Enable ``warn_unused_ignores`` mypy option by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17991 <https://github.com/galaxyproject/galaxy/pull/17991>`_
* Add galaxy to user agent by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18003 <https://github.com/galaxyproject/galaxy/pull/18003>`_
* Document syntax for accessing nested parameters in `change_format` - `when` tags by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#18018 <https://github.com/galaxyproject/galaxy/pull/18018>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#18063 <https://github.com/galaxyproject/galaxy/pull/18063>`_
* Enable flake8-implicit-str-concat ruff rules by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18067 <https://github.com/galaxyproject/galaxy/pull/18067>`_

-------------------
24.0.3 (2024-06-28)
-------------------


=========
Bug fixes
=========

* Allow purge query param, deprecate purge body param by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18105 <https://github.com/galaxyproject/galaxy/pull/18105>`_
* Make sure that all Linter subclasses are imported for listing them by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#18339 <https://github.com/galaxyproject/galaxy/pull/18339>`_
* Assign default ``data`` extension on discovered collection output  by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18389 <https://github.com/galaxyproject/galaxy/pull/18389>`_
* Allow in_range validator for selects by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#18403 <https://github.com/galaxyproject/galaxy/pull/18403>`_

-------------------
24.0.2 (2024-05-07)
-------------------


=========
Bug fixes
=========

* Tool linters: allow to skip by old linter names (by allowing to skip linter modules) by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#18091 <https://github.com/galaxyproject/galaxy/pull/18091>`_
* tool linters: output filters should only consider child filter nodes by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#18096 <https://github.com/galaxyproject/galaxy/pull/18096>`_

-------------------
24.0.1 (2024-05-02)
-------------------


=========
Bug fixes
=========

* Fix conditional Image imports by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17899 <https://github.com/galaxyproject/galaxy/pull/17899>`_

-------------------
24.0.0 (2024-04-02)
-------------------


=========
Bug fixes
=========

* xsd: reorder choices for permissive boolean by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#17187 <https://github.com/galaxyproject/galaxy/pull/17187>`_
* Allow for upper case container tags by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#17254 <https://github.com/galaxyproject/galaxy/pull/17254>`_
* Fixes for flake8-bugbear 24.1.17 by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17340 <https://github.com/galaxyproject/galaxy/pull/17340>`_
* Escape pipe character in tool XSD docs by `@neoformit <https://github.com/neoformit>`_ in `#17359 <https://github.com/galaxyproject/galaxy/pull/17359>`_
* XSD schema doc building: quote pipe characters in attribute tables by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#17364 <https://github.com/galaxyproject/galaxy/pull/17364>`_
* Fix IUC best practices links, mention data_source_async in XSD by `@wm75 <https://github.com/wm75>`_ in `#17409 <https://github.com/galaxyproject/galaxy/pull/17409>`_
* Fix data_source and data_source_async bugs by `@wm75 <https://github.com/wm75>`_ in `#17422 <https://github.com/galaxyproject/galaxy/pull/17422>`_
* Add tool XML schema documention for outputs - collection - data by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#17465 <https://github.com/galaxyproject/galaxy/pull/17465>`_
* has_size assertion: implement size (as synonym for value) by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#17490 <https://github.com/galaxyproject/galaxy/pull/17490>`_
* Yaml nested assertions: fix parsing by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#17641 <https://github.com/galaxyproject/galaxy/pull/17641>`_

============
Enhancements
============

* build_mulled: also use namespace for building singularity images by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#15657 <https://github.com/galaxyproject/galaxy/pull/15657>`_
* Python 3.8 as minimum by `@mr-c <https://github.com/mr-c>`_ in `#16954 <https://github.com/galaxyproject/galaxy/pull/16954>`_
* Extend regex groups in stdio regex matches by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#17016 <https://github.com/galaxyproject/galaxy/pull/17016>`_
* Split linters in separate classes by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#17081 <https://github.com/galaxyproject/galaxy/pull/17081>`_
* Add select parameter with options from remote resources by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17087 <https://github.com/galaxyproject/galaxy/pull/17087>`_
* Replace discouraged Mambaforge with Miniforge3 by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17177 <https://github.com/galaxyproject/galaxy/pull/17177>`_
* Clarify the meaning of lexical sorting of discovered datasets by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#17190 <https://github.com/galaxyproject/galaxy/pull/17190>`_
* Migrate models to pydantic 2 by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17262 <https://github.com/galaxyproject/galaxy/pull/17262>`_
* Add element_identifier and ext to inputs config file export by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#17357 <https://github.com/galaxyproject/galaxy/pull/17357>`_
* Enable ``warn_unreachable`` mypy option by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17365 <https://github.com/galaxyproject/galaxy/pull/17365>`_
* Fix type annotation of code using XML etree by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17367 <https://github.com/galaxyproject/galaxy/pull/17367>`_
* Update to black 2024 stable style by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17391 <https://github.com/galaxyproject/galaxy/pull/17391>`_
* Some additional typing for test interactor stuff. by `@jmchilton <https://github.com/jmchilton>`_ in `#17398 <https://github.com/galaxyproject/galaxy/pull/17398>`_
* Allow using tool data bundles as inputs to reference data select parameters by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17435 <https://github.com/galaxyproject/galaxy/pull/17435>`_
* `data_column` parameter: use `column_names` metadata if present by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#17478 <https://github.com/galaxyproject/galaxy/pull/17478>`_
* Fixing data_source tools and incrementing tool profile by `@wm75 <https://github.com/wm75>`_ in `#17515 <https://github.com/galaxyproject/galaxy/pull/17515>`_
* Add `image_diff` comparison method for test output verification using images by `@kostrykin <https://github.com/kostrykin>`_ in `#17556 <https://github.com/galaxyproject/galaxy/pull/17556>`_
* add shm_size based on ShmSize  by `@richard-burhans <https://github.com/richard-burhans>`_ in `#17565 <https://github.com/galaxyproject/galaxy/pull/17565>`_
* Record missing outputs as test errors by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#17874 <https://github.com/galaxyproject/galaxy/pull/17874>`_

=============
Other changes
=============

* consistently compare profile versions by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#16492 <https://github.com/galaxyproject/galaxy/pull/16492>`_

-------------------
23.2.1 (2024-02-21)
-------------------


=========
Bug fixes
=========

* Never consider `_galaxy_` conda env as unused by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#16460 <https://github.com/galaxyproject/galaxy/pull/16460>`_
* chore: fix typos by `@afuetterer <https://github.com/afuetterer>`_ in `#16851 <https://github.com/galaxyproject/galaxy/pull/16851>`_
* Ruff and flake8 fixes by `@nsoranzo <https://github.com/nsoranzo>`_ in `#16884 <https://github.com/galaxyproject/galaxy/pull/16884>`_
* Quote singularity env parameters by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#17055 <https://github.com/galaxyproject/galaxy/pull/17055>`_
* Remove duplicates when copying sections for tool panel view by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#17117 <https://github.com/galaxyproject/galaxy/pull/17117>`_
* Display application fixes and tests by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17233 <https://github.com/galaxyproject/galaxy/pull/17233>`_

============
Enhancements
============

* Implement default locations for data and collection parameters. by `@jmchilton <https://github.com/jmchilton>`_ in `#14955 <https://github.com/galaxyproject/galaxy/pull/14955>`_
* Add framework test for profile behavior of `format="input"` by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#15482 <https://github.com/galaxyproject/galaxy/pull/15482>`_
* Tool Shed 2.0 by `@jmchilton <https://github.com/jmchilton>`_ in `#15639 <https://github.com/galaxyproject/galaxy/pull/15639>`_
* Add ability to assert metadata properties on input dataset parameters by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#15825 <https://github.com/galaxyproject/galaxy/pull/15825>`_
* Migrate a part of the users API to Fast API by `@heisner-tillman <https://github.com/heisner-tillman>`_ in `#16341 <https://github.com/galaxyproject/galaxy/pull/16341>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#16436 <https://github.com/galaxyproject/galaxy/pull/16436>`_
* Tweak tool memory use and optimize shared memory when using preload by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16536 <https://github.com/galaxyproject/galaxy/pull/16536>`_
* Document that required text parameters need a validator by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#16538 <https://github.com/galaxyproject/galaxy/pull/16538>`_
* Include `regex` when linting validators by `@davelopez <https://github.com/davelopez>`_ in `#16684 <https://github.com/galaxyproject/galaxy/pull/16684>`_
* Refactor Tool Panel views structures and combine ToolBox and ToolBoxWorkflow into one component by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#16739 <https://github.com/galaxyproject/galaxy/pull/16739>`_
* Replace file_name property with get_file_name function by `@SergeyYakubov <https://github.com/SergeyYakubov>`_ in `#16783 <https://github.com/galaxyproject/galaxy/pull/16783>`_
* Updated path-based interactive tools with entry point path injection, support for ITs with relative links, shortened URLs, doc and config updates including Podman job_conf by `@sveinugu <https://github.com/sveinugu>`_ in `#16795 <https://github.com/galaxyproject/galaxy/pull/16795>`_
* Remove remaining legacy backbone form input elements by `@guerler <https://github.com/guerler>`_ in `#16834 <https://github.com/galaxyproject/galaxy/pull/16834>`_
* Change `api/tool_panel` to `api/tool_panels/...` by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#16928 <https://github.com/galaxyproject/galaxy/pull/16928>`_
* optimize object store cache operations by `@SergeyYakubov <https://github.com/SergeyYakubov>`_ in `#17025 <https://github.com/galaxyproject/galaxy/pull/17025>`_
* Enhance xsd schema and allow simpler assertion lists by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17134 <https://github.com/galaxyproject/galaxy/pull/17134>`_

=============
Other changes
=============

* Merge 23.1 into dev by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16534 <https://github.com/galaxyproject/galaxy/pull/16534>`_
* Explicitly document default of multiple by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#16625 <https://github.com/galaxyproject/galaxy/pull/16625>`_

-------------------
23.1.4 (2024-01-04)
-------------------


=========
Bug fixes
=========

* Separate collection and non-collection data element by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17236 <https://github.com/galaxyproject/galaxy/pull/17236>`_

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

* Change log level for duplicate data table entries to warning by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16988 <https://github.com/galaxyproject/galaxy/pull/16988>`_
* Upgrade minimum conda to be compatible with latest conda-build by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#17013 <https://github.com/galaxyproject/galaxy/pull/17013>`_
* Fix duplicated tools in tool panel view section copying by `@jmchilton <https://github.com/jmchilton>`_ in `#17036 <https://github.com/galaxyproject/galaxy/pull/17036>`_

============
Enhancements
============

* Adds `biii` as supported xref reference type by `@kostrykin <https://github.com/kostrykin>`_ in `#16952 <https://github.com/galaxyproject/galaxy/pull/16952>`_

-------------------
23.1.1 (2023-10-23)
-------------------


=========
Bug fixes
=========

* Fixes for two framework test tools by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#15483 <https://github.com/galaxyproject/galaxy/pull/15483>`_
* add missing f for f-string by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#15584 <https://github.com/galaxyproject/galaxy/pull/15584>`_
* Fix call to `docker_cached_container_description` by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#15598 <https://github.com/galaxyproject/galaxy/pull/15598>`_
* Fix log message by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#15838 <https://github.com/galaxyproject/galaxy/pull/15838>`_
* add required_files to the tag list for linting by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#16129 <https://github.com/galaxyproject/galaxy/pull/16129>`_
* Handle appending to a results file that does not exists. by `@ksuderman <https://github.com/ksuderman>`_ in `#16233 <https://github.com/galaxyproject/galaxy/pull/16233>`_
* Improve container resolver documentation by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16280 <https://github.com/galaxyproject/galaxy/pull/16280>`_
* Add missing singularity_no_mount prop parsing by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16367 <https://github.com/galaxyproject/galaxy/pull/16367>`_
* Restore resolution of Conda environments generated from non-lowercase package names by `@nsoranzo <https://github.com/nsoranzo>`_ in `#16474 <https://github.com/galaxyproject/galaxy/pull/16474>`_
* Fix up unit tests for local use by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16483 <https://github.com/galaxyproject/galaxy/pull/16483>`_
* Fix `multiple` remote test data by `@davelopez <https://github.com/davelopez>`_ in `#16542 <https://github.com/galaxyproject/galaxy/pull/16542>`_
* Don't use ``docker run`` --user flag on OSX by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16573 <https://github.com/galaxyproject/galaxy/pull/16573>`_
* Backport tool mem fixes by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16601 <https://github.com/galaxyproject/galaxy/pull/16601>`_
* xsd: allow name attribute of test collections by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#16663 <https://github.com/galaxyproject/galaxy/pull/16663>`_
* Fix short ids in tool panel views.  by `@jmchilton <https://github.com/jmchilton>`_ in `#16800 <https://github.com/galaxyproject/galaxy/pull/16800>`_
* Fix tool panel views for versionless tool ids by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16809 <https://github.com/galaxyproject/galaxy/pull/16809>`_

============
Enhancements
============

* Decompress history data for testing assertions by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#15085 <https://github.com/galaxyproject/galaxy/pull/15085>`_
* OIDC tokens by `@SergeyYakubov <https://github.com/SergeyYakubov>`_ in `#15300 <https://github.com/galaxyproject/galaxy/pull/15300>`_
* Fix for new style conda packages by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#15446 <https://github.com/galaxyproject/galaxy/pull/15446>`_
* Move database access code out of tool_util by `@jdavcs <https://github.com/jdavcs>`_ in `#15467 <https://github.com/galaxyproject/galaxy/pull/15467>`_
* Protection against problematic boolean parameters. by `@jmchilton <https://github.com/jmchilton>`_ in `#15493 <https://github.com/galaxyproject/galaxy/pull/15493>`_
* Implement initial tool/wf test assertions module for JSON data. by `@jmchilton <https://github.com/jmchilton>`_ in `#15494 <https://github.com/galaxyproject/galaxy/pull/15494>`_
* Explore tool remote test data by `@davelopez <https://github.com/davelopez>`_ in `#15510 <https://github.com/galaxyproject/galaxy/pull/15510>`_
* xsd: add multiple to the list of attributes for all parameter types deriving from select by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#15534 <https://github.com/galaxyproject/galaxy/pull/15534>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#15564 <https://github.com/galaxyproject/galaxy/pull/15564>`_
* Container resolvers: add docs, typing and tests by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#15614 <https://github.com/galaxyproject/galaxy/pull/15614>`_
* Migrate to MyST-Parser for Markdown docs by `@nsoranzo <https://github.com/nsoranzo>`_ in `#15844 <https://github.com/galaxyproject/galaxy/pull/15844>`_
* Enable per-destination ``container_resolver_config_file`` by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#15884 <https://github.com/galaxyproject/galaxy/pull/15884>`_
* Updated doc and tests for attribute value filter by `@tuncK <https://github.com/tuncK>`_ in `#15929 <https://github.com/galaxyproject/galaxy/pull/15929>`_
* Make container builders use mamba by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#15953 <https://github.com/galaxyproject/galaxy/pull/15953>`_
* Code cleanups from ruff and pyupgrade by `@nsoranzo <https://github.com/nsoranzo>`_ in `#16035 <https://github.com/galaxyproject/galaxy/pull/16035>`_
* Vendorise ``packaging.versions.LegacyVersion`` by `@nsoranzo <https://github.com/nsoranzo>`_ in `#16058 <https://github.com/galaxyproject/galaxy/pull/16058>`_
* Merge ``Target`` class with ``CondaTarget`` by `@nsoranzo <https://github.com/nsoranzo>`_ in `#16181 <https://github.com/galaxyproject/galaxy/pull/16181>`_
* Small test decorator improvements. by `@jmchilton <https://github.com/jmchilton>`_ in `#16220 <https://github.com/galaxyproject/galaxy/pull/16220>`_
* tool_util: switch to mambaforge on non-32bit; add arm64 support by `@mr-c <https://github.com/mr-c>`_ in `#16223 <https://github.com/galaxyproject/galaxy/pull/16223>`_
* Fix tool remote test data by `@davelopez <https://github.com/davelopez>`_ in `#16311 <https://github.com/galaxyproject/galaxy/pull/16311>`_

=============
Other changes
=============

* Restore tmp mounting by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16533 <https://github.com/galaxyproject/galaxy/pull/16533>`_

-------------------
23.0.6 (2023-10-23)
-------------------


=========
Bug fixes
=========

* Fixes for extra files handling and cached object stores  by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16595 <https://github.com/galaxyproject/galaxy/pull/16595>`_
* Fix create/install commands for conda 23.9.0 by `@nsoranzo <https://github.com/nsoranzo>`_ in `#16831 <https://github.com/galaxyproject/galaxy/pull/16831>`_

-------------------
23.0.5 (2023-07-29)
-------------------


=========
Bug fixes
=========

* Allow duplicate labels in linter if outputs contain filters  by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#15933 <https://github.com/galaxyproject/galaxy/pull/15933>`_
* Fix parsing tool metadata from bio.tools by `@kysrpex <https://github.com/kysrpex>`_ in `#16449 <https://github.com/galaxyproject/galaxy/pull/16449>`_
* Linter: fix regex for profile version by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#16480 <https://github.com/galaxyproject/galaxy/pull/16480>`_
* Adjust test_data_download method in GalaxyInteractorApi so an admin user is not required by `@simonbray <https://github.com/simonbray>`_ in `#16482 <https://github.com/galaxyproject/galaxy/pull/16482>`_

-------------------
23.0.4 (2023-06-30)
-------------------

No recorded changes since last release

-------------------
23.0.3 (2023-06-26)
-------------------


=========
Bug fixes
=========

* xsd: add missing `sep` attribute for `has_n_columns` by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#16262 <https://github.com/galaxyproject/galaxy/pull/16262>`_
* Missing init prevents models.py being bundled into tool_util by `@nuwang <https://github.com/nuwang>`_ in `#16308 <https://github.com/galaxyproject/galaxy/pull/16308>`_

============
Enhancements
============

* When importing tool data bundles, use the first loc file for the matching table by `@natefoo <https://github.com/natefoo>`_ in `#16247 <https://github.com/galaxyproject/galaxy/pull/16247>`_

-------------------
23.0.2 (2023-06-13)
-------------------


=========
Bug fixes
=========

* Don't fail CWL tool parsing when Cheetah not installed by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16219 <https://github.com/galaxyproject/galaxy/pull/16219>`_
* Allow skipping ``expect_num_outputs`` when ``expect_failure`` is set in tool test by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#16237 <https://github.com/galaxyproject/galaxy/pull/16237>`_

-------------------
23.0.1 (2023-06-08)
-------------------


=========
Bug fixes
=========

* Fix assertion linting to not fail on byte suffixes by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#15873 <https://github.com/galaxyproject/galaxy/pull/15873>`_
* Fix ``get_test_from_anaconda()`` and ``base_image_for_targets()`` functions by `@nsoranzo <https://github.com/nsoranzo>`_ in `#16125 <https://github.com/galaxyproject/galaxy/pull/16125>`_
* Fix test search for mulled container hashes by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16170 <https://github.com/galaxyproject/galaxy/pull/16170>`_

============
Enhancements
============

* Allow setting auto_decompress property in staging interface by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16014 <https://github.com/galaxyproject/galaxy/pull/16014>`_

-------------------
22.1.5 (2022-11-14)
-------------------

* Set test status to success on expected failure

-------------------
22.1.4 (2022-10-28)
-------------------

* Add missing unittest_utils package to galaxy-tool-util

-------------------
22.1.3 (2022-10-27)
-------------------

* Pin minimum pyopenssl version when installing Conda
* Add ``--strict-channel-priority`` to conda create/install commands if using conda >=4.7.5

-------------------
22.1.2 (2022-08-29)
-------------------

* Fix lint context error level
* Pin galaxy-util to >= 22.1
* Fix biocontainer resolution without beaker cache

-------------------
22.1.1 (2022-08-22)
-------------------

* First release from the 22.01 branch of Galaxy

-------------------
21.9.2 (2021-11-23)
-------------------

* Fix linting of ``multiple="true"`` select inputs.

-------------------
21.9.1 (2021-11-03)
-------------------

* Fix tool linting.

-------------------
21.9.0 (2021-11-03)
-------------------

* First release from the 21.09 branch of Galaxy.

-------------------
21.1.2 (2021-06-23)
-------------------



-------------------
21.1.1 (2021-05-21)
-------------------



-------------------
21.1.0 (2021-03-19)
-------------------

* First release from the 21.01 branch of Galaxy.

-------------------
20.9.1 (2020-10-28)
-------------------

* Bugfixes to work around & annotate expected tool test failures.

-------------------
20.9.0 (2020-10-28)
-------------------

* First release from the 20.09 branch of Galaxy.

------------------------
20.9.0.dev2 (2020-08-02)
------------------------

* First release from the 20.09 branch of Galaxy.

-------------------
20.5.0 (2020-07-04)
-------------------

* First release from the 20.05 branch of Galaxy.

-------------------
20.1.0 (2020-07-04)
-------------------

* First release from the 20.01 branch of Galaxy.

-------------------
19.9.1 (2019-12-28)
-------------------

* Fix declared dependency problem with package.

-------------------
19.9.0 (2019-12-16)
-------------------

* Initial import from dev branch of Galaxy during 19.09 development cycle.
