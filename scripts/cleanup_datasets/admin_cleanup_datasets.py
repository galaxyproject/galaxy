#!/usr/bin/env python
"""
Mark datasets as deleted that are older than specified cutoff
and (optionaly) with a tool_id that matches the specified search
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
from __future__ import print_function

import argparse
import logging
import os
import shutil
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta
from time import strftime

import sqlalchemy as sa
from mako.template import Template
from sqlalchemy import and_, false

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, 'lib')))

import galaxy.config
import galaxy.model.mapping
import galaxy.util
from galaxy.util.script import app_properties_from_args, populate_config_args

from cleanup_datasets import CleanupDatasetsApplication  # noqa: I100

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
    parser.add_argument('legacy_config', metavar='CONFIG', type=str,
                        default=None,
                        nargs='?',
                        help='config file (legacy, use --config instead)')
    parser.add_argument("-d", "--days", dest="days", action="store",
                        type=int, help="number of days (60)", default=60)
    parser.add_argument("--tool_id", default=None,
                        help="Text to match against tool_id"
                        "Default: match all")
    parser.add_argument("--template", default=None,
                        help="Mako Template file to use as email "
                        "Variables are 'cutoff' for the cutoff in days, "
                        "'email' for users email and "
                        "'datasets' which is a list of tuples "
                        "containing 'dataset' and 'history' names. "
                        "Default: admin_cleanup_deletion_template.txt")
    parser.add_argument("-i", "--info_only", action="store_true",
                        dest="info_only", help="info about the requested action",
                        default=False)
    parser.add_argument("-e", "--email_only", action="store_true",
                        dest="email_only", help="Send emails only, don't delete",
                        default=False)
    parser.add_argument("--smtp", default=None,
                        help="SMTP Server to use to send email. "
                        "Default: [read from galaxy ini file]")
    parser.add_argument("--fromaddr", default=None,
                        help="From address to use to send email. "
                        "Default: [read from galaxy ini file]")
    populate_config_args(parser)

    args = parser.parse_args()
    config_override = None
    if args.legacy_config:
        config_override = args.legacy_config

    app_properties = app_properties_from_args(args, legacy_config_override=config_override)

    if args.smtp is not None:
        app_properties['smtp_server'] = args.smtp
    if app_properties.get('smtp_server') is None:
        parser.error("SMTP Server must be specified as an option (--smtp) "
                     "or in the config file (smtp_server)")

    if args.fromaddr is not None:
        app_properties['email_from'] = args.fromaddr
    if app_properties.get('email_from') is None:
        parser.error("From address must be specified as an option "
                     "(--fromaddr) or in the config file "
                     "(email_from)")

    scriptdir = os.path.dirname(os.path.abspath(__file__))
    template_file = args.template
    if template_file is None:
        default_template = os.path.join(scriptdir,
                                        'admin_cleanup_deletion_template.txt')
        sample_template_file = "%s.sample" % default_template
        if os.path.exists(default_template):
            template_file = default_template
        elif os.path.exists(sample_template_file):
            print("Copying %s to %s" % (sample_template_file, default_template))
            shutil.copyfile(sample_template_file, default_template)
            template_file = default_template
        else:
            parser.error("Default template (%s) or sample template (%s) not "
                         "found, please specify template as an option "
                         "(--template)." % default_template,
                         sample_template_file)
    elif not os.path.exists(template_file):
        parser.error("Specified template file (%s) not found." % template_file)

    config = galaxy.config.Configuration(**app_properties)

    app = CleanupDatasetsApplication(config)
    cutoff_time = datetime.utcnow() - timedelta(days=args.days)
    now = strftime("%Y-%m-%d %H:%M:%S")

    print("##########################################")
    print("\n# %s - Handling stuff older than %i days" % (now, args.days))

    if args.info_only:
        print("# Displaying info only ( --info_only )\n")
    elif args.email_only:
        print("# Sending emails only, not deleting ( --email_only )\n")

    administrative_delete_datasets(
        app, cutoff_time, args.days, tool_id=args.tool_id,
        template_file=template_file, config=config,
        email_only=args.email_only, info_only=args.info_only)
    app.shutdown()
    sys.exit(0)


def administrative_delete_datasets(app, cutoff_time, cutoff_days,
                                   tool_id, template_file,
                                   config, email_only=False,
                                   info_only=False):
    # Marks dataset history association deleted and email users
    start = time.time()
    # Get HDAs older than cutoff time (ignore tool_id at this point)
    # We really only need the id column here, but sqlalchemy barfs when
    # trying to select only 1 column
    hda_ids_query = sa.select(
        (app.model.HistoryDatasetAssociation.table.c.id,
         app.model.HistoryDatasetAssociation.table.c.deleted),
        whereclause=and_(
            app.model.Dataset.table.c.deleted == false(),
            app.model.HistoryDatasetAssociation.table.c.update_time < cutoff_time,
            app.model.HistoryDatasetAssociation.table.c.deleted == false()),
        from_obj=[sa.outerjoin(
                  app.model.Dataset.table,
                  app.model.HistoryDatasetAssociation.table)])

    # Add all datasets associated with Histories to our list
    hda_ids = []
    hda_ids.extend(
        [row.id for row in hda_ids_query.execute()])

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
        user_query = sa.select(
            [app.model.HistoryDatasetAssociation.table,
             app.model.History.table,
             app.model.User.table],
            whereclause=and_(
                app.model.HistoryDatasetAssociation.table.c.id == hda_id),
            from_obj=[sa.join(app.model.User.table,
                              app.model.History.table)
                      .join(app.model.HistoryDatasetAssociation.table)],
            use_labels=True)
        for result in user_query.execute():
            user_notifications[result[app.model.User.table.c.email]].append(
                (result[app.model.HistoryDatasetAssociation.table.c.name],
                 result[app.model.History.table.c.name]))
            deleted_instance_count += 1
            if not info_only and not email_only:
                # Get the HistoryDatasetAssociation objects
                hda = app.sa_session.query(
                    app.model.HistoryDatasetAssociation).get(hda_id)
                if not hda.deleted:
                    # Mark the HistoryDatasetAssociation as deleted
                    hda.deleted = True
                    app.sa_session.add(hda)
                    print("Marked HistoryDatasetAssociation id %d as "
                          "deleted" % hda.id)
                app.sa_session.flush()

    emailtemplate = Template(filename=template_file)
    for (email, dataset_list) in user_notifications.items():
        msgtext = emailtemplate.render(email=email,
                                       datasets=dataset_list,
                                       cutoff=cutoff_days)
        subject = "Galaxy Server Cleanup " \
            "- %d datasets DELETED" % len(dataset_list)
        fromaddr = config.email_from
        print()
        print("From: %s" % fromaddr)
        print("To: %s" % email)
        print("Subject: %s" % subject)
        print("----------")
        print(msgtext)
        if not info_only:
            galaxy.util.send_mail(fromaddr, email, subject,
                                  msgtext, config)

    stop = time.time()
    print()
    print("Marked %d dataset instances as deleted" % deleted_instance_count)
    print("Total elapsed time: ", stop - start)
    print("##########################################")


def _get_tool_id_for_hda(app, hda_id):
    # TODO Some datasets don't seem to have an entry in jtod or a copied_from
    if hda_id is None:
        return None
    job = app.sa_session.query(app.model.Job).\
        join(app.model.JobToOutputDatasetAssociation).\
        filter(app.model.JobToOutputDatasetAssociation.table.c.dataset_id ==
               hda_id).first()
    if job is not None:
        return job.tool_id
    else:
        hda = app.sa_session.query(app.model.HistoryDatasetAssociation).\
            get(hda_id)
        return _get_tool_id_for_hda(app, hda.
                                    copied_from_history_dataset_association_id)


if __name__ == "__main__":
    main()
