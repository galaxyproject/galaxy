#!/usr/bin/env python
import argparse
import json
import os
import statistics
import sys

import jinja2
from mir import html_report

DESCRIPTION = "Script to generate (potentially merged) HTML summary of Galaxy Test Performance"
templateLoader = jinja2.FileSystemLoader(searchpath="./scripts")
template_env = jinja2.Environment(loader=templateLoader)
TEMPLATE_FILE = "tests_markdown.tpl"
TEMPLATE_COMPARE_FILE = "tests_markdown_compare.tpl"
LINKS = [{"href": "https://github.com/galaxyproject/galaxy", "title": "Galaxy"}]


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    args = _parser().parse_args(argv)
    common_env = {
        "include_raw_metrics": args.include_raw_metrics,
    }
    if len(args.input_path) == 1:
        markdown_output = _summarize_one(args.input_path[0], common_env)
    else:
        markdown_output = _summarize_many(args.input_path, common_env)

    html_output = html_report(markdown_output, args.title, links=LINKS)
    with open(args.output_path, "w") as f:
        f.write(html_output)


def _summarize_one(input_path, common_env):
    environment = _prepare_raw_data(input_path)
    environment.update(common_env)
    template = template_env.get_template(TEMPLATE_FILE)
    output = template.render(environment)
    return output


def _summarize_many(input_paths, common_env):
    raw_data_dicts = []
    for arg in input_paths:
        raw_data_dicts.append(_prepare_raw_data(arg))
    environment = _merge_summarizes(raw_data_dicts)
    environment.update(common_env)
    template = template_env.get_template(TEMPLATE_COMPARE_FILE)
    output = template.render(environment)
    return output


def _empty_statistics():
    return {"count": 0, "sum": "n/a", "median": "n/a", "stdev": "n/a", "mean": "n/a"}


def _merge_summarizes(raw_data_dicts):
    tests = {}
    api_endpoints = {}
    internals = {}

    all_tests = set()
    all_api_endpoints = set()
    all_internal_metrics = set()
    all_labels = set()

    for raw_data_dict in raw_data_dicts:
        these_api_endpoints = raw_data_dict["raw_data"]["api_endpoint_metrics"]
        for api_endpoint in these_api_endpoints.keys():
            all_api_endpoints.add(api_endpoint)
        these_internal_endpoints = raw_data_dict["raw_data"]["internals_metrics"]
        for internal_endpoint in these_internal_endpoints.keys():
            all_internal_metrics.add(internal_endpoint)
        these_tests = raw_data_dict["raw_data"]["tests"]
        for test in these_tests:
            all_tests.add(test["nodeid"])
        all_labels.add(raw_data_dict["label"])

    for label in all_labels:
        for api_endpoint in all_api_endpoints:
            _ensure_has_dict_at_key(
                api_endpoints,
                api_endpoint,
                total_time={},
                sql_time={},
                sql_queries={},
            )
            api_endpoints[api_endpoint]["total_time"][label] = _empty_statistics()
            api_endpoints[api_endpoint]["sql_time"][label] = _empty_statistics()
        for internal_endpoint in all_internal_metrics:
            _ensure_has_dict_at_key(
                internals,
                internal_endpoint,
                total_time={},
            )
            internals[internal_endpoint]["total_time"][label] = _empty_statistics()
        for test in all_tests:
            if test not in tests:
                tests[test] = {}
            tests[test][label] = {"outcome": "absent"}

    for raw_data_dict in raw_data_dicts:
        ab_label = raw_data_dict["label"]
        these_api_endpoints = raw_data_dict["raw_data"]["api_endpoint_metrics"]
        these_internals = raw_data_dict["raw_data"]["internals_metrics"]
        these_tests = raw_data_dict["raw_data"]["tests"]

        for api_endpoint, endpoint_metrics in these_api_endpoints.items():
            api_endpoints[api_endpoint]["label"] = endpoint_metrics["label"]
            api_endpoints[api_endpoint]["total_time"][ab_label].update(endpoint_metrics["total_time"])
            api_endpoints[api_endpoint]["sql_time"][ab_label].update(endpoint_metrics["sql_time"])

        for endpoint, endpoint_metrics in these_internals.items():
            internals[endpoint]["label"] = endpoint_metrics["label"]
            internals[endpoint]["total_time"][ab_label].update(endpoint_metrics["total_time"])

        for test in these_tests:
            tests[test["nodeid"]][ab_label]["outcome"] = test.get("outcome")

    return {
        "raw_data": {
            "api_endpoint_metrics": api_endpoints,
            "internals_metrics": internals,
            "tests": tests,
        }
    }


def _prepare_raw_data(path):
    with open(path) as f:
        inp_dict = json.load(f)
    environment = dict(raw_data=inp_dict, label=os.path.basename(path))
    __inject_summary(environment)
    __inject_api_timing_summary_environment(environment)
    __inject_api_timing_summary_across_tests(environment)
    __inject_raw_timings(environment)
    return environment


def __inject_api_timing_summary_environment(environment):
    for test in environment["raw_data"]["tests"]:
        if "metadata" not in test:
            continue

        if "local_metrics" in test["metadata"]:
            __inject_api_timing_summary_test(test)


def __inject_api_timing_summary_across_tests(environment):
    api_endpoints = {}
    internals = {}

    for test in environment["raw_data"]["tests"]:
        if "metadata" not in test:
            continue

        test_endpoints = test["api_endpoint_metrics"]
        for api_endpoint, endpoint_metrics in test_endpoints.items():
            _ensure_has_dict_at_key(
                api_endpoints,
                api_endpoint,
                total_time={"raw": []},
                sql_time={"raw": []},
                sql_queries={"raw": []},
            )
            api_endpoints[api_endpoint]["label"] = endpoint_metrics["label"]
            api_endpoints[api_endpoint]["total_time"]["raw"].extend(endpoint_metrics["total_time"]["raw"])
            api_endpoints[api_endpoint]["sql_time"]["raw"].extend(endpoint_metrics["sql_time"]["raw"])
            api_endpoints[api_endpoint]["sql_queries"]["raw"].extend(endpoint_metrics["sql_queries"]["raw"])

        test_endpoints = test["internals_metrics"]
        for api_endpoint, endpoint_metrics in test_endpoints.items():
            _ensure_has_dict_at_key(
                internals,
                api_endpoint,
                total_time={"raw": []},
            )
            internals[api_endpoint]["label"] = endpoint_metrics["label"]
            internals[api_endpoint]["total_time"]["raw"].extend(endpoint_metrics["total_time"]["raw"])

    for endpoint_metrics in api_endpoints.values():
        __inject_statistics(endpoint_metrics["total_time"])
        __inject_statistics(endpoint_metrics["sql_time"])
        __inject_statistics(endpoint_metrics["sql_queries"])

    for endpoint_metrics in internals.values():
        __inject_statistics(endpoint_metrics["total_time"])

    environment["raw_data"]["api_endpoint_metrics"] = api_endpoints
    environment["raw_data"]["internals_metrics"] = internals


def __inject_raw_timings(environment):
    all_timings = []

    for test in environment["raw_data"]["tests"]:
        if "metadata" not in test or "local_metrics" not in test["metadata"]:
            continue

        metrics = test["metadata"]["local_metrics"]
        timing = metrics["timing"]

        for endpoint, timings in timing.items():
            recording = timings[0].copy()
            recording["endpoint"] = endpoint
            all_timings.append(recording)

    environment["raw_data"]["all_timings"] = all_timings


def _ensure_has_dict_at_key(the_dict, key, **kwd):
    if key not in the_dict:
        the_dict[key] = dict(**kwd)


def __inject_api_timing_summary_test(test):
    metrics = test["metadata"]["local_metrics"]
    timing = metrics["timing"]
    counter = metrics["counter"]
    api_endpoints = {}
    internal_timings = {}

    def summarize_times(timings):
        times = [t["time"] for t in timings]
        return __inject_statistics(
            {
                "raw": times,
            }
        )

    def summarize_counter(c):
        counters = [t["n"] for t in c]
        return __inject_statistics(
            {
                "raw": counters,
            }
        )

    for endpoint, timings in timing.items():
        if not endpoint.startswith("api"):
            continue

        endpoint_summary = {"total_time": summarize_times(timings), "label": endpoint[len("api.") :]}
        sql_times = f"sql.{endpoint}"
        if sql_times in timing:
            endpoint_summary["sql_time"] = summarize_times(timing[sql_times])
        sql_queries = f"sqlqueries.{endpoint}"
        if sql_queries in counter:
            endpoint_summary["sql_queries"] = summarize_counter(counter[sql_queries])
        api_endpoints[endpoint] = endpoint_summary

    for endpoint, timings in timing.items():
        if not endpoint.startswith("internals"):
            continue

        internal_summary = {"total_time": summarize_times(timings), "label": endpoint[len("internals.") :]}
        internal_timings[endpoint] = internal_summary

    test["api_endpoint_metrics"] = api_endpoints
    test["internals_metrics"] = internal_timings


def __inject_statistics(from_dict):
    raw_values = from_dict["raw"]
    from_dict["sum"] = sum(raw_values)
    from_dict["median"] = f"{statistics.median(raw_values):.2f}"
    if len(raw_values) > 1:
        from_dict["stdev"] = f"{statistics.stdev(raw_values):.4f}"
    else:
        from_dict["stdev"] = "n/a"
    from_dict["mean"] = f"{statistics.mean(raw_values):.2f}"
    from_dict["count"] = len(raw_values)
    return from_dict


def __inject_summary(environment):
    total = 0
    failures = 0
    skips = 0
    for test in environment["raw_data"]["tests"]:
        total += 1
        status = test.get("outcome")
        if status == "failed":
            failures += 1
        elif status == "skipped":
            skips += 1
    environment["raw_data"]["results"] = {
        "total": total,
        "failures": failures,
        "skips": skips,
    }


def _parser():
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument("input_path", metavar="INPUT", type=str, nargs="+", help="structured input path (.json)")
    parser.add_argument("--output_path", type=str, default="test.html", help="output path (.html)")
    parser.add_argument("--title", type=str, default="Test Performance Summary", help="Performance Test Results")
    parser.add_argument("--include_raw_metrics", action="store_true", default=False)

    return parser


if __name__ == "__main__":
    main()
