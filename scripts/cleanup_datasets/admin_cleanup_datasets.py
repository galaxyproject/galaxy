#!/usr/bin/env python
"""
Mark datasets as deleted that are older than specified cutoff
and (optionally) with a tool_id that matches the specified search
string.

This script is useful for administrators to cleanup after users who
leave many old datasets around.  It was modeled after the cleanup_datasets.py
script originally distributed with Galaxy.

Basic Usage:
    admin_cleanup_datasets.py galaxy.ini -d 60 \
        --template=email_template.txt

Required Arguments:
    config_file - the Galaxy configuration file (galaxy.ini)

Optional Arguments:
    -d --days - number of days old the dataset must be (default: 60)
    --tool_id - string to search for in dataset tool_id (default: all)
    --template - Mako template file to use for email notification
    -i --info_only - Print results, but don't email or delete anything
    -e --email_only - Email notifications, but don't delete anything
        Useful for notifying users of pending deletion

    --smtp - Specify smtp server
        If not specified, use smtp settings specified in config file
    --fromaddr - Specify from address
        If not specified, use email_from specified in config file

Email Template Variables:
   cutoff - the cutoff in days
   email - the users email address
   datasets - a list of tuples containing 'dataset' and 'history' names


Author: Lance Parsons (lparsons@princeton.edu)
"""

import argparse
import logging
import os
import shutil
import sys
import time
from collections import defaultdict
from datetime import (
    datetime,
    timedelta,
)
from time import strftime

import sqlalchemy as sa
from mako.template import Template
from sqlalchemy import (
    and_,
    false,
    select,
)
from sqlalchemy.orm import aliased

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, "lib")))

from cleanup_datasets import CleanupDatasetsApplication

import galaxy.config
import galaxy.util
from galaxy import model
from galaxy.util.script import (
    app_properties_from_args,
    populate_config_args,
)

log = logging.getLogger()
log.setLevel(logging.INFO)
log.addHandler(logging.StreamHandler(sys.stdout))

assert sys.version_info[:2] >= (2, 6)


def main():
    """
    Datasets that are older than the specified cutoff and for which the tool_id
    contains the specified text will be marked as deleted in user's history and
    the user will be notified by email using the specified template file.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "legacy_config",
        metavar="CONFIG",
        type=str,
        default=None,
        nargs="?",
        help="config file (legacy, use --config instead)",
    )
    parser.add_argument("-d", "--days", dest="days", action="store", type=int, help="number of days (60)", default=60)
    parser.add_argument("--tool_id", default=None, help="Text to match against tool_id. Default: match all")
    parser.add_argument(
        "--template",
        default=None,
        help="Mako Template file to use as email "
        "Variables are 'cutoff' for the cutoff in days, "
        "'email' for users email and "
        "'datasets' which is a list of tuples "
        "containing 'dataset' and 'history' names. "
        "Default: admin_cleanup_deletion_template.txt",
    )
    parser.add_argument(
        "-i",
        "--info_only",
        action="store_true",
        dest="info_only",
        help="info about the requested action",
        default=False,
    )
    parser.add_argument(
        "-e",
        "--email_only",
        action="store_true",
        dest="email_only",
        help="Send emails only, don't delete",
        default=False,
    )
    parser.add_argument(
        "--smtp", default=None, help="SMTP Server to use to send email. Default: [read from galaxy config file]"
    )
    parser.add_argument(
        "--fromaddr", default=None, help="From address to use to send email. Default: [read from galaxy config file]"
    )
    populate_config_args(parser)

    args = parser.parse_args()
    config_override = None
    if args.legacy_config:
        config_override = args.legacy_config

    app_properties = app_properties_from_args(args, legacy_config_override=config_override)

    if args.smtp is not None:
        app_properties["smtp_server"] = args.smtp
    if app_properties.get("smtp_server") is None:
        parser.error("SMTP Server must be specified as an option (--smtp) or in the config file (smtp_server)")

    if args.fromaddr is not None:
        app_properties["email_from"] = args.fromaddr
    if app_properties.get("email_from") is None:
        parser.error("From address must be specified as an option (--fromaddr) or in the config file (email_from)")

    scriptdir = os.path.dirname(os.path.abspath(__file__))
    template_file = args.template
    if template_file is None:
        default_template = os.path.join(scriptdir, "admin_cleanup_deletion_template.txt")
        sample_template_file = f"{default_template}.sample"
        if os.path.exists(default_template):
            template_file = default_template
        elif os.path.exists(sample_template_file):
            print(f"Copying {sample_template_file} to {default_template}")
            shutil.copyfile(sample_template_file, default_template)
            template_file = default_template
        else:
            parser.error(
                "Default template ({default_template}) or sample template ({sample_template_file}) not "
                "found, please specify template as an option (--template)."
            )
    elif not os.path.exists(template_file):
        parser.error(f"Specified template file ({template_file}) not found.")

    config = galaxy.config.Configuration(**app_properties)

    app = CleanupDatasetsApplication(config)
    cutoff_time = datetime.utcnow() - timedelta(days=args.days)
    now = strftime("%Y-%m-%d %H:%M:%S")

    print("##########################################")
    print(f"\n# {now} - Handling stuff older than {args.days} days")

    if args.info_only:
        print("# Displaying info only ( --info_only )\n")
    elif args.email_only:
        print("# Sending emails only, not deleting ( --email_only )\n")

    administrative_delete_datasets(
        app,
        cutoff_time,
        args.days,
        tool_id=args.tool_id,
        template_file=template_file,
        config=config,
        email_only=args.email_only,
        info_only=args.info_only,
    )
    app.shutdown()
    sys.exit(0)


def administrative_delete_datasets(
    app, cutoff_time, cutoff_days, tool_id, template_file, config, email_only=False, info_only=False
):
    # Marks dataset history association deleted and email users
    start = time.time()
    session = app.sa_session

    # Aliases for ORM‑mapped classes
    HDA = aliased(app.model.HistoryDatasetAssociation)
    Hist = aliased(app.model.History)
    User = aliased(app.model.User)
    Dataset = aliased(app.model.Dataset)

    # Get HDAs older than cutoff time (ignore tool_id at this point)
    hda_ids_query = (
        select(HDA.id)
        .join(Dataset, Dataset.id == HDA.dataset_id, isouter=True)
        .where(and_(
            Dataset.deleted.is_(False),
            HDA.update_time < cutoff_time,
            HDA.deleted.is_(False)))
    )

    # Add all datasets associated with Histories to our list
    hda_ids = session.execute(hda_ids_query).scalars().all()

    # Now find the tool_id that generated the dataset (even if it was copied)
    tool_matched_ids = []
    if tool_id is not None:
        for hda_id in hda_ids:
            this_tool_id = _get_tool_id_for_hda(app, hda_id)
            if this_tool_id is not None and tool_id in this_tool_id:
                tool_matched_ids.append(hda_id)
        hda_ids = tool_matched_ids

    deleted_instance_count = 0
    user_notifications = defaultdict(list)

    # Process each of the Dataset objects
    for hda_id in hda_ids:
        # Bind hda_id for current iteration
        rows = session.execute(
            select(User.email, HDA.name, Hist.name)
            .join(Hist, Hist.user_id == User.id)
            .join(HDA, HDA.history_id == Hist.id)
            .where(HDA.id == hda_id)
        ).all()

        for email, dataset_name, history_name in rows:
            user_notifications[email].append((dataset_name, history_name))
            deleted_instance_count += 1

            if not info_only and not email_only:
                # Get the HistoryDatasetAssociation objects
                hda = session.get(app.model.HistoryDatasetAssociation, hda_id)
                if not hda.deleted:
                    # Mark the HistoryDatasetAssociation as deleted
                    hda.deleted = True
                    session.add(hda)
                    print(f"Marked HistoryDatasetAssociation id {hda.id} as deleted")

        if not info_only and not email_only:
            session.commit()

    emailtemplate = Template(filename=template_file)
    for email, dataset_list in user_notifications.items():
        msgtext = emailtemplate.render(email=email, datasets=dataset_list, cutoff=cutoff_days)
        subject = f"Galaxy Server Cleanup - {len(dataset_list)} datasets DELETED"
        fromaddr = config.email_from
        print()
        print(f"From: {fromaddr}")
        print(f"To: {email}")
        print(f"Subject: {subject}")
        print("----------")
        print(msgtext)
        if not info_only:
            galaxy.util.send_mail(fromaddr, email, subject, msgtext, config)

    stop = time.time()
    print()
    print(f"Marked {deleted_instance_count} dataset instances as deleted")
    print(f"Total elapsed time: {stop - start:.3f} seconds")
    print("##########################################")


def _get_tool_id_for_hda(app, hda_id):
    if hda_id is None:
        return None

    # Aliases for ORM‑mapped classes
    Job = aliased(app.model.Job)
    JTODA = aliased(app.model.JobToOutputDatasetAssociation)
    HDA = aliased(app.model.HistoryDatasetAssociation)

    session = app.sa_session

    job_query = (
        select(Job.tool_id)
        .join(JTODA, JTODA.job_id == Job.id)
        .where(JTODA.dataset_id == hda_id)
    )

    tool_id = session.execute(job_query).scalars().first()
    if tool_id is not None:
        return tool_id

    hda = session.get(app.model.HistoryDatasetAssociation, hda_id)
    if hda is None:
        return None

    return _get_tool_id_for_hda(app, hda.copied_from_history_dataset_association_id)


if __name__ == "__main__":
    main()
