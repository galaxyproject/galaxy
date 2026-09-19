{% macro print_statistics_table(has_metrics) -%}

        | | *{{ has_metrics.keys() | join("* | *") }}* |
        |-|-{{ has_metrics.values() | map(attribute="absent", default="-") | join("-|-") }}-|
        | **Sum** *(ms)* | ``{{ has_metrics.values() | map(attribute="sum") | join("`` | ``") }}`` |
        | **Median** *(ms)* | ``{{ has_metrics.values() | map(attribute="median") | join("`` | ``") }}`` |
        | **Mean** *(ms)* | ``{{ has_metrics.values() | map(attribute="mean") | join("`` | ``") }}`` |
        | **Standard Deviation** | ``{{ has_metrics.values() | map(attribute="stdev") | join("`` | ``") }}`` |
        | **Count** | ``{{ has_metrics.values() | map(attribute="count") | join("`` | ``") }}`` |

{%- endmacro %}

# Tests

<details><summary>Expand</summary>

{% for test_name, test in raw_data.tests.items() %}    
   * <details><summary><tt>{{test_name}}</tt></summary>

        | | *{{ test.keys() | join("* | *") }}* |
        |-|-{{ test.values() | map(attribute="absent", default="-") | join("-|-") }}-|
        | **Outcome** | ``{{ test.values() | map(attribute="outcome") | join("`` | ``") }}`` |

{% endfor %}

</details>

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

        *Total Time*

        {{ print_statistics_table(internals_metrics.total_time) }}

     </details>
{% endfor %}

</details>
