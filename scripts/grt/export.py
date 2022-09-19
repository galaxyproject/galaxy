#!/usr/bin/env python
"""Script for parsing Galaxy job information in preparation for submission to the Galactic radio telescope.

See doc/source/admin/grt.rst for more detailed usage information.
"""
import argparse
import json
import logging
import os
import sys
import tarfile
import time
from collections import defaultdict

import yaml

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, "lib")))
import galaxy
import galaxy.app
import galaxy.config
from galaxy.model.mapping import init_models_from_config
from galaxy.objectstore import build_object_store_from_config
from galaxy.util import (
    hash_util,
    unicodify,
)
from galaxy.util.script import (
    app_properties_from_args,
    populate_config_args,
)

sample_config = os.path.abspath(os.path.join(os.path.dirname(__file__), "grt.yml.sample"))
default_config = os.path.abspath(os.path.join(os.path.dirname(__file__), "grt.yml"))


def _init(args):
    properties = app_properties_from_args(args)
    config = galaxy.config.Configuration(**properties)
    object_store = build_object_store_from_config(config)
    if not config.database_connection:
        logging.warning(
            "The database connection is empty. If you are using the default value, please uncomment that in your galaxy.yml"
        )

    model = init_models_from_config(config, object_store=object_store)
    return (
        model,
        object_store,
        config,
    )


def kw_metrics(job):
    return {f"{metric.plugin}_{metric.metric_name}": metric.metric_value for metric in job.metrics}


def round_to_2sd(number):
    if number:
        return str(int(float("%.2g" % number)))
    else:
        return "-1"


def main(argv):
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        "-r",
        "--report-directory",
        help="Directory to store reports in",
        default=os.path.abspath(os.path.join(".", "reports")),
    )
    parser.add_argument("-g", "--grt-config", help="Path to GRT config file", default=default_config)
    parser.add_argument(
        "-l",
        "--loglevel",
        choices=["debug", "info", "warning", "error", "critical"],
        help="Set the logging level",
        default="warning",
    )
    parser.add_argument("-b", "--batch-size", type=int, default=1000, help="Batch size for sql queries")
    parser.add_argument(
        "-m",
        "--max-records",
        type=int,
        default=5000000,
        help="Maximum number of records to include in a single report. This option should ONLY be used when reporting historical data. Setting this may require running GRT multiple times to capture all historical logs.",
    )
    populate_config_args(parser)

    args = parser.parse_args()
    logging.getLogger().setLevel(getattr(logging, args.loglevel.upper()))

    _times = []
    _start_time = time.time()

    def annotate(label, human_label=None):
        if human_label:
            logging.info(human_label)
        _times.append((label, time.time() - _start_time))

    annotate("init_start", "Loading GRT configuration...")
    try:
        with open(args.grt_config) as handle:
            config = yaml.safe_load(handle)
    except Exception:
        logging.info("Using default GRT configuration")
        with open(sample_config) as handle:
            config = yaml.safe_load(handle)
    annotate("init_end")

    REPORT_DIR = args.report_directory
    CHECK_POINT_FILE = os.path.join(REPORT_DIR, ".checkpoint")
    REPORT_IDENTIFIER = str(time.time())
    REPORT_BASE = os.path.join(REPORT_DIR, REPORT_IDENTIFIER)

    if os.path.exists(CHECK_POINT_FILE):
        with open(CHECK_POINT_FILE) as handle:
            last_job_sent = int(handle.read())
    else:
        last_job_sent = -1

    annotate("galaxy_init", "Loading Galaxy...")
    model, object_store, gxconfig = _init(args)

    # Galaxy overrides our logging level.
    logging.getLogger().setLevel(getattr(logging, args.loglevel.upper()))
    sa_session = model.context.current
    annotate("galaxy_end")

    # Fetch jobs COMPLETED with status OK that have not yet been sent.

    # Set up our arrays
    active_users = defaultdict(int)
    job_state_data = defaultdict(int)

    if not os.path.exists(REPORT_DIR):
        os.makedirs(REPORT_DIR)

    # Pick an end point so our queries can return uniform data.
    annotate("endpoint_start", "Identifying a safe endpoint for SQL queries")
    end_job_id = sa_session.query(model.Job.id).order_by(model.Job.id.desc()).first()[0]

    # Allow users to only report N records at once.
    if args.max_records > 0:
        if end_job_id - last_job_sent > args.max_records:
            end_job_id = last_job_sent + args.max_records

    annotate("endpoint_end", f"Processing jobs ({last_job_sent}, {end_job_id}]")

    # Remember the last job sent.
    if end_job_id == last_job_sent:
        logging.info("No new jobs to report")
        # So we can just quit now.
        sys.exit(0)

    # Unfortunately we have to keep this mapping for the sanitizer to work properly.
    job_tool_map = {}
    blacklisted_tools = config["sanitization"]["tools"]

    annotate("export_jobs_start", "Exporting Jobs")
    with open(REPORT_BASE + ".jobs.tsv", "w", encoding="utf-8") as handle_job:
        handle_job.write("\t".join(("id", "tool_id", "tool_version", "state", "create_time")) + "\n")
        for offset_start in range(last_job_sent, end_job_id, args.batch_size):
            logging.debug("Processing %s:%s", offset_start, min(end_job_id, offset_start + args.batch_size))
            for job in (
                sa_session.query(
                    model.Job.id,
                    model.Job.user_id,
                    model.Job.tool_id,
                    model.Job.tool_version,
                    model.Job.state,
                    model.Job.create_time,
                )
                .filter(model.Job.id > offset_start)
                .filter(model.Job.id <= min(end_job_id, offset_start + args.batch_size))
                .all()
            ):
                # If the tool is blacklisted, exclude everywhere
                if job[2] in blacklisted_tools:
                    continue

                try:
                    line = [
                        str(job[0]),  # id
                        job[2],  # tool_id
                        job[3],  # tool_version
                        job[4],  # state
                        str(job[5]),  # create_time
                    ]
                    cline = unicodify("\t".join(line) + "\n")
                    handle_job.write(cline)
                except Exception:
                    logging.warning("Unable to write out a 'handle_job' row. Ignoring the row.", exc_info=True)
                    continue
                # meta counts
                job_state_data[job[4]] += 1
                active_users[job[1]] += 1
                job_tool_map[job[0]] = job[2]
    annotate("export_jobs_end")

    annotate("export_datasets_start", "Exporting Datasets")
    with open(REPORT_BASE + ".datasets.tsv", "w", encoding="utf-8") as handle_datasets:
        handle_datasets.write(
            "\t".join(("job_id", "dataset_id", "extension", "file_size", "param_name", "type")) + "\n"
        )
        for offset_start in range(last_job_sent, end_job_id, args.batch_size):
            logging.debug("Processing %s:%s", offset_start, min(end_job_id, offset_start + args.batch_size))

            # four queries: JobToInputDatasetAssociation, JobToOutputDatasetAssociation, HistoryDatasetAssociation, Dataset

            job_to_input_hda_ids = (
                sa_session.query(
                    model.JobToInputDatasetAssociation.job_id,
                    model.JobToInputDatasetAssociation.dataset_id,
                    model.JobToInputDatasetAssociation.name,
                )
                .filter(model.JobToInputDatasetAssociation.job_id > offset_start)
                .filter(model.JobToInputDatasetAssociation.job_id <= min(end_job_id, offset_start + args.batch_size))
                .all()
            )

            job_to_output_hda_ids = (
                sa_session.query(
                    model.JobToOutputDatasetAssociation.job_id,
                    model.JobToOutputDatasetAssociation.dataset_id,
                    model.JobToOutputDatasetAssociation.name,
                )
                .filter(model.JobToOutputDatasetAssociation.job_id > offset_start)
                .filter(model.JobToOutputDatasetAssociation.job_id <= min(end_job_id, offset_start + args.batch_size))
                .all()
            )

            # add type and concat
            job_to_hda_ids = [[list(i), "input"] for i in job_to_input_hda_ids] + [
                [list(i), "output"] for i in job_to_output_hda_ids
            ]

            # put all of the hda_ids into a list
            hda_ids = [i[0][1] for i in job_to_hda_ids]

            hdas = (
                sa_session.query(
                    model.HistoryDatasetAssociation.id,
                    model.HistoryDatasetAssociation.dataset_id,
                    model.HistoryDatasetAssociation.extension,
                )
                .filter(model.HistoryDatasetAssociation.id.in_(hda_ids))
                .all()
            )

            # put all the dataset ids into a list
            dataset_ids = [i[1] for i in hdas]

            # get the sizes of the datasets
            datasets = (
                sa_session.query(model.Dataset.id, model.Dataset.total_size)
                .filter(model.Dataset.id.in_(dataset_ids))
                .all()
            )

            # datasets to dictionay for easy search
            hdas = {i[0]: i[1:] for i in hdas}
            datasets = {i[0]: i[1:] for i in datasets}

            for job_to_hda in job_to_hda_ids:

                job = job_to_hda[0]  # job_id, hda_id, name
                filetype = job_to_hda[1]  # input|output

                # No associated job
                if job[0] not in job_tool_map:
                    continue

                # If the tool is blacklisted, exclude everywhere
                if job_tool_map[job[0]] in blacklisted_tools:
                    continue

                hda_id = job[1]
                if hda_id is None:
                    continue

                dataset_id = hdas[hda_id][0]
                if dataset_id is None:
                    continue

                try:
                    line = [
                        str(job[0]),  # Job ID
                        str(hda_id),  # HDA ID
                        str(hdas[hda_id][1]),  # Extension
                        round_to_2sd(datasets[dataset_id][0]),  # File size
                        job[2],  # Parameter name
                        str(filetype),  # input/output
                    ]
                    cline = unicodify("\t".join(line) + "\n")
                    handle_datasets.write(cline)
                except Exception:
                    logging.warning("Unable to write out a 'handle_datasets' row. Ignoring the row.", exc_info=True)
                    continue
    annotate("export_datasets_end")

    annotate("export_metric_num_start", "Exporting Metrics (Numeric)")
    with open(REPORT_BASE + ".metric_num.tsv", "w", encoding="utf-8") as handle_metric_num:
        handle_metric_num.write("\t".join(("job_id", "plugin", "name", "value")) + "\n")
        for offset_start in range(last_job_sent, end_job_id, args.batch_size):
            logging.debug("Processing %s:%s", offset_start, min(end_job_id, offset_start + args.batch_size))
            for metric in (
                sa_session.query(
                    model.JobMetricNumeric.job_id,
                    model.JobMetricNumeric.plugin,
                    model.JobMetricNumeric.metric_name,
                    model.JobMetricNumeric.metric_value,
                )
                .filter(model.JobMetricNumeric.job_id > offset_start)
                .filter(model.JobMetricNumeric.job_id <= min(end_job_id, offset_start + args.batch_size))
                .all()
            ):
                # No associated job
                if metric[0] not in job_tool_map:
                    continue
                # If the tool is blacklisted, exclude everywhere
                if job_tool_map[metric[0]] in blacklisted_tools:
                    continue

                try:
                    line = [str(metric[0]), metric[1], metric[2], str(metric[3])]  # job id  # plugin  # name  # value

                    cline = unicodify("\t".join(line) + "\n")
                    handle_metric_num.write(cline)
                except Exception:
                    logging.warning("Unable to write out a 'handle_metric_num' row. Ignoring the row.", exc_info=True)
                    continue
    annotate("export_metric_num_end")

    # Now on to outputs.
    with tarfile.open(REPORT_BASE + ".tar.gz", "w:gz") as handle:
        for name in ("jobs", "metric_num", "datasets"):
            path = REPORT_BASE + "." + name + ".tsv"
            if os.path.exists(path):
                handle.add(path)

    for name in ("jobs", "metric_num", "datasets"):
        path = REPORT_BASE + "." + name + ".tsv"
        if os.path.exists(path):
            os.unlink(REPORT_BASE + "." + name + ".tsv")

    _times.append(("job_finish", time.time() - _start_time))
    sha = hash_util.memory_bound_hexdigest(hash_func=hash_util.sha256, path=REPORT_BASE + ".tar.gz")
    _times.append(("hash_finish", time.time() - _start_time))

    # Now serialize the individual report data.
    with open(REPORT_BASE + ".json", "w") as handle:
        json.dump(
            {
                "version": 3,
                "galaxy_version": gxconfig.version_major,
                "generated": REPORT_IDENTIFIER,
                "report_hash": "sha256:" + sha,
                "metrics": {
                    "_times": _times,
                },
                "users": {
                    "active": len(active_users.keys()),
                    "total": sa_session.query(model.User.id).count(),
                },
                "jobs": job_state_data,
            },
            handle,
        )

    # Write our checkpoint file so we know where to start next time.
    with open(CHECK_POINT_FILE, "w") as handle:
        handle.write(str(end_job_id))


if __name__ == "__main__":
    main(sys.argv)
