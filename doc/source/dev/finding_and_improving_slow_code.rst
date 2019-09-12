Finding and improving slow Galaxy code
--------------------------------------

This is a short howto on how one can find slow code in Galaxy (but this
should apply to other projects as well).

I will walk through how I have improved the tool form building speed in
https://github.com/galaxyproject/galaxy/pull/4541.

Identifying the problem
~~~~~~~~~~~~~~~~~~~~~~~

@bgruening mentioned that loading the tool form was slow on his server,
and I checked ours and saw that for certain tools it took around 2-3
seconds to load the tool form, while for others this was significantly
faster.

Identifying a rough entrypoint for profiling the code
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you know the part in the UI that is slow, you can identify the
corresponding API endpoint (assuming the backend is slow) by looking at
the network tab in Chrome's JavaScript console while doing the operation
that is slow. When I clicked on HISAT2 in the tool menu, I saw that
there was a GET request to
http://127.0.0.1:8080/api/tools/toolshed.g2.bx.psu.edu/repos/iuc/hisat2/hisat2/2.0.5.2/build?tool\_version=2.0.5.2
that took 3 seconds to complete. Looking into `Galaxy's API
documentation <https://docs.galaxyproject.org/en/master/api/api.html#galaxy.webapps.galaxy.api.tools.ToolsController.build>`__
we can match this URL to the actual code in
`lib/galaxy/webapps/galaxy/api/tools.py <https://github.com/galaxyproject/galaxy/blob/release_17.05/lib/galaxy/webapps/galaxy/api/tools.py#L89>`__.

Profiling
~~~~~~~~~

I like the profilehooks library, which provides a decorator for
profiling specific functions like our ``build`` function. To use it,
install profilehooks into Galaxy's Python environment ( sourcing
Galaxy's virtualenv and running ``pip install profilehooks`` should be
enough) and import the profile function at the top of the file that
contains the function you would like to profile
(``from profilehooks import profile``), and then add an additional
``@profile`` decorator just above the ``build`` function. You can now
start Galaxy, hit the API endpoint a few times and shut down galaxy
again. You should see profilehooks output in your logs. This is the
output I saw

::

               6585515 function calls (6497718 primitive calls) in 9.560 seconds

       Ordered by: cumulative time, internal time, call count
       List reduced from 997 to 40 due to restriction <40>

       ncalls  tottime  percall  cumtime  percall filename:lineno(function)
            4    0.000    0.000    9.572    2.393 decorators.py:227(decorator)
            4    0.000    0.000    9.567    2.392 tools.py:89(build)
            4    0.000    0.000    9.566    2.391 __init__.py:1786(to_json)
        116/4    0.005    0.000    8.973    2.243 __init__.py:1877(populate_model)
        27312    0.063    0.000    8.110    0.000 dataset_matcher.py:74(hda_match)
         2184    0.005    0.000    6.426    0.003 dataset_matcher.py:163(hdca_match)
       100/56    0.001    0.000    6.389    0.114 grouping.py:625(to_dict)
      300/168    0.001    0.000    6.388    0.038 grouping.py:628(nested_to_dict)
    3720/2184    0.014    0.000    6.387    0.003 dataset_matcher.py:170(dataset_collection_match)
      768/324    0.002    0.000    6.386    0.020 {map}
      200/112    0.001    0.000    6.384    0.057 grouping.py:643(to_dict)
      468/308    0.001    0.000    6.381    0.021 grouping.py:646(input_to_dict)
    5376/2760    0.018    0.000    5.949    0.002 dataset_matcher.py:146(__valid_element)
          104    0.016    0.000    5.451    0.052 basic.py:1775(to_dict)
        27312    0.076    0.000    4.980    0.000 dataset_matcher.py:34(hda_accessible)
          328    0.011    0.000    4.965    0.015 query.py:2700(one)
         3840    0.009    0.000    4.825    0.001 dataset_matcher.py:106(__can_access_dataset)
          176    0.001    0.000    4.797    0.027 context.py:119(get_current_user_roles)
          176    0.004    0.000    4.796    0.027 __init__.py:237(all_roles)
          508    0.003    0.000    4.379    0.009 query.py:2756(__iter__)
        10680    0.042    0.000    3.028    0.000 dataset_matcher.py:47(valid_hda_match)
           32    0.002    0.000    2.975    0.093 basic.py:1943(to_dict)
          208    0.015    .000    2.924    0.014 basic.py:1480(get_initial_value)
         8144    0.021    0.000    2.645    0.000 __init__.py:2204(find_conversion_destination)
         8144    0.010    0.000    2.584    0.000 data.py:611(find_conversion_destination)
         8144    0.035    0.000    2.573    0.000 registry.py:818(find_conversion_destination_for_dataset_by_extensions)
          508    0.009    0.000    2.534    0.005 query.py:3204(_compile_context)
         8144    0.451    0.000    2.360    0.000 registry.py:798(get_converters_by_datatype)
          508    0.003    0.000    2.083    0.004 query.py:3568(setup_context)
     1580/508    0.054    0.000    2.080    0.004 loading.py:224(_setup_entity_query)
    20660/9712    0.062    0.000    2.056    0.000 interfaces.py:498(setup)
     1072/360    0.011    0.000    1.997    0.006 strategies.py:1114(setup_query)
          816    0.004    0.000    1.928    0.002 basic.py:208(to_dict)
          508    0.004    0.000    1.842    0.004 query.py:2770(_execute_and_instances)
          508    0.002    0.000    1.786    0.004 base.py:846(execute)
          508    0.001    0.000    1.783    0.004 elements.py:322(_execute_on_connection)
          508    0.005    0.000    1.782    0.004 base.py:975(_execute_clauseelement)
          128    0.002    0.000    1.781    0.014 basic.py:1878(match_multirun_collections)
      13308    0.064    0.000    1.716    0.000 visitors.py:199(traverse)
      13308    0.088    0.000    1.651    0.000 visitors.py:304(replacement_traverse)

I loaded the tool form 4 times, as you can see on the second line of the
output (``ncalls=4``). The table is sorted by the cumulative time that the
functions ran while ``build`` was being evaluated.

Optimizing the slow function calls
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The most valuable targets for optimization therefore should be
relatively high in the table. I have seen two functions that I would not
think of as expensive and that should not be that high in the table:

``get_current_user_roles``, which took 4.8 seconds out of 9.5 seconds
total and is being called 176 times and ``get_converters_by_datatype``
which took 2.4 seconds out the 9.5 seconds total.

``get_current_user_roles`` is called in the context of
``hda_accessible`` and ``hda_accessible`` (these are also in our table)
in
https://github.com/galaxyproject/galaxy/blob/release\_17.05/lib/galaxy/tools/parameters/dataset\_matcher.py#L109
We can see that the ``current_user_roles`` attribute of
``DatasetMatcher`` instances are already being cached, however during
the course of filling in parameters in the tool building process a new
``DatasetMatcher`` instance is being created for each
``DataToolParameter`` in
https://github.com/galaxyproject/galaxy/blob/release\_17.05/lib/galaxy/tools/parameters/basic.py#L1456.
This means that the cached roles will be lost for the next
``DataToolParameter`` that we need to fill in. It would be great if we
didn't need to redo this expensive operation for each data input.

When building the tool interface we deal with a ``WorkRequestContext``
instance, which inherits from ``ProvidesUserContext`` in
https://github.com/galaxyproject/galaxy/blob/dev/lib/galaxy/managers/context.py#L119.
``ProvidesUserContext`` defines a ``get_current_user_roles`` method that
gets the current users' roles from the database. We can implement a
cached variant of this in ``WorkRequestContext``, which will be used
when building the tool form. You can find this change in
https://github.com/galaxyproject/galaxy/pull/4541/commits/d1a2007275f128fea051ead55fb47d2c2686abf5

The slowness in ``get_converters_by_datatype`` can be circumvented by
caching the result of this function, which I have done in
https://github.com/galaxyproject/galaxy/pull/4541/commits/471707bd7dfa048a412aad9cdcc1d0b4aea70bc7
(and fixed a mistake in
https://github.com/galaxyproject/galaxy/pull/4541/commits/2d8b242e697a08775879fc873578b5f244d4d5cb)

Checking how the changes affect the speed
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

After these changes we can verify that the code is faster now and that
the key functions we targeted are not as high anymore in the profiling
table output:

::

             1384317 function calls (1363256 primitive calls) in 2.215 seconds

       Ordered by: cumulative time, internal time, call count
       List reduced from 991 to 40 due to restriction <40>

       ncalls  tottime  percall  cumtime  percall filename:lineno(function)
            4    0.000    0.000    2.220    0.555 decorators.py:227(decorator)
            4    0.000    0.000    2.215    0.554 tools.py:89(build)
            4    0.000    0.000    2.214    0.554 __init__.py:1786(to_json)
        116/4    0.004    0.000    1.861    0.465 __init__.py:1877(populate_model)
       100/56    0.000    0.000    1.578    0.028 grouping.py:625(to_dict)
      300/168    0.000    0.000    1.577    0.009 grouping.py:628(nested_to_dict)
      768/324    0.001    0.000    1.576    0.005 {map}
      200/112    0.001    0.000    1.574    0.014 grouping.py:643(to_dict)
      468/308    0.001    0.000    1.572    0.005 grouping.py:646(input_to_dict)
         2184    0.003    0.000    1.055    0.000 dataset_matcher.py:163(hdca_match)
       153436    0.147    0.000    1.048    0.000 attributes.py:229(__get__)
    3720/2184    0.010    0.000    1.019    0.000 dataset_matcher.py:170(dataset_collection_match)
           32    0.002    0.000    0.956    0.030 basic.py:1943(to_dict)
     1924/964    0.005    0.000    0.901    0.001 attributes.py:561(get)
          960    0.006    0.000    0.875    0.001 strategies.py:492(_load_for_state)
        27312    0.051    0.000    0.860    0.000 dataset_matcher.py:74(hda_match)
          324    0.001    0.000    0.857    0.003 <string>:1(<lambda>)
          324    0.009    0.000    0.855    0.003 strategies.py:565(_emit_lazyload)
          104    0.012    0.000    0.807    0.008 basic.py:1775(to_dict)
          336    0.002    0.000    0.803    0.002 query.py:2756(__iter__)
          208    0.011    0.000    0.752    0.004 basic.py:1480(get_initial_value)
          180    0.004    0.000    0.666    0.004 query.py:2607(all)
    5376/2760    0.014    0.000    0.612    0.000 dataset_matcher.py:146(__valid_element)
          336    0.002    0.000    0.606    0.002 query.py:2770(_execute_and_instances)
          336    0.001    0.000    0.570    0.002 base.py:846(execute)
          336    0.001    0.000    0.569    0.002 elements.py:322(_execute_on_connection)
          336    0.003    0.000    0.568    0.002 base.py:975(_execute_clauseelement)
        10680    0.031    0.000    0.526    0.000 dataset_matcher.py:47(valid_hda_match)
          128    0.001    0.000    0.525    0.004 basic.py:1878(match_multirun_collections)
          156    0.003    0.000    0.446    0.003 query.py:2700(one)
          816    0.004    0.000    0.426    0.001 basic.py:208(to_dict)
          336    0.006    0.000    0.348    0.001 base.py:1061(_execute_context)
          152    0.003    0.000    0.342    0.002 loading.py:161(load_on_ident)
         44/4    0.001    0.000    0.324    0.081 __init__.py:219(populate_state)
        16360    0.052    0.000    0.307    0.000 data.py:713(matches_any)
         1300    0.007    0.000    0.302    0.000 loading.py:30(instances)
        60/40    0.001    0.000    0.294    0.007 grouping.py:608(get_initial_value)
    6168/3720    0.012    0.000    0.270    0.000 __init__.py:3222(populated)
         336    0.001    0.000    0.268    0.001 default.py:449(do_execute)
         336    0.262    0.001    0.267    0.001 {method 'execute' of 'psycopg2.extensions.cursor' objects}

As before I hit the `build` endpoint 4 times.
Both functions have disappeared from the table of the 40 longest running
function calls, and the total time required has decreased from 9.5 seconds to 2.2 seconds.