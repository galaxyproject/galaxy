{% macro print_statistics_table(has_metrics) -%}

        | | *Value* |
        |-|-|
        | **Sum** *(ms)* | ``{{ has_metrics.sum }}`` |
        | **Median** *(ms)* | ``{{ has_metrics.median }}`` |
        | **Mean** *(ms)* | ``{{ has_metrics.mean }}`` |
        | **Standard Deviation** | ``{{ has_metrics.stdev }}`` |
        | **Count** | ``{{ has_metrics.count }}`` |

{%- endmacro %}

{% macro test_header(test) -%}
{%       if test.outcome == 'passed' %}

* <details class="rcorners light-green"><summary class="light-green">&#9989; {{ test.nodeid }}</summary><div class="padded">
{%       else %}

* <details class="rcorners light-red"><summary class="light-red">&#10060; {{ test.nodeid }}</summary><div class="padded">
{%       endif %}
{%- endmacro %}

## Test Summary
{% set state = namespace(found=false) %}
{% set state.passed = raw_data.results.total - raw_data.results.failures - raw_data.results.skips | default(0) %}
{% set state.failed = raw_data.results.failures | default(0) %}
{% set state.skipped = raw_data.results.skipped | default(0) %}

<div class="progress">
  <div class="progress-bar progress-bar-success" style="width: {{ (state.passed / raw_data.results.total) * 100 if raw_data.results.total else 0 }}%" aria-valuenow="{{ state.success }}" aria-valuemin="0" aria-valuemax="{{ raw_data.results.total }}" data-toggle="tooltip" title="{{state.success}} Passed">
  </div>
  <div class="progress-bar progress-bar-warning" style="width: {{ (state.skipped / raw_data.results.total) * 100 if raw_data.results.total else 0 }}%" aria-valuenow="{{ state.skipped }}" aria-valuemin="0" aria-valuemax="{{ raw_data.results.total }}" data-toggle="tooltip" title="{{state.skipped}} Skipped">
  </div>
  <div class="progress-bar progress-bar-danger" style="width: {{ ((state.failed) / raw_data.results.total) * 100 if raw_data.results.total else 0 }}%" aria-valuenow="{{ state.failure }}" aria-valuemin="0" aria-valuemax="{{ raw_data.results.total }}" title="{{state.failed}} Failed">
  </div>
</div>

# Tests

{% for status, desc in {'failed': 'Failed', 'passed': 'Passed'}.items() if state[status]%}
<details><summary>{{ desc }} Tests</summary>
{%   for test in raw_data.tests %}
{%     if test.outcome == status %}

{{ test_header(test) }}

   API Endpoint Metrics for Test
{% if 'api_endpoint_metrics' in test %}

{% for api_endpoint, api_endpoint_metrics in test.api_endpoint_metrics.items() %}
   * <details><summary><tt>{{api_endpoint_metrics.label}}</tt></summary>

        **Total Time**

        {{ print_statistics_table(api_endpoint_metrics.total_time) }}

        **SQL Time**

        {{ print_statistics_table(api_endpoint_metrics.sql_time) }}

     </details>
{% endfor %}

{% endif %}

{% if 'internals_metrics' in test %}

   Galaxy Internals Metrics for Test
{% for endpoint, endpoint_metrics in test.internals_metrics.items() %}
   * <details><summary><tt>{{endpoint_metrics.label}}</tt></summary>

        **Total Time**

        {{ print_statistics_table(endpoint_metrics.total_time) }}

     </details>
{% endfor %}

{% endif %}

{% endif %}

{% endfor %}
</div></details>

{% endfor %}

# API Endpoint Metrics across Tests

<details><summary>Expand</summary>

{% for api_endpoint, api_endpoint_metrics in raw_data.api_endpoint_metrics.items() %}    
   * <details><summary><tt>{{api_endpoint_metrics.label}}</tt></summary>

        **Total Time**

        {{ print_statistics_table(api_endpoint_metrics.total_time) }}

        **SQL Time**

        {{ print_statistics_table(api_endpoint_metrics.sql_time) }}

     </details>
{% endfor %}

</details>

# Internals Metrics across Tests

<details><summary>Expand</summary>

{% for api_endpoint, internals_metrics in raw_data.internals_metrics.items() %}    
   * <details><summary><tt>{{internals_metrics.label}}</tt></summary>

        **Total Time**

        {{ print_statistics_table(internals_metrics.total_time) }}

     </details>
{% endfor %}

</details>

{% if include_raw_metrics %}

# All Timings

<details><summary>Expand</summary>

{% for timings in raw_data.all_timings %}    

{{ timings }}

{% endfor %}

</details>

{% endif %}
