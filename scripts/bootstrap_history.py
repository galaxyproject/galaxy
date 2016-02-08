#!/usr/bin/env python
# Little script to make HISTORY.rst more easy to format properly, lots TODO
# pull message down and embed, use arg parse, handle multiple, etc...

import calendar
import datetime
import os
import re
import string
import sys
try:
    import requests
except ImportError:
    requests = None
import urlparse
import textwrap
import json
try:
    from pygithub3 import Github
except ImportError:
    Github = None


PROJECT_DIRECTORY = os.path.join(os.path.dirname(__file__), os.pardir)
PROJECT_OWNER = "galaxyproject"
PROJECT_NAME = "galaxy"
PROJECT_URL = "https://github.com/%s/%s" % (PROJECT_OWNER, PROJECT_NAME)
PROJECT_API = "https://api.github.com/repos/%s/%s/" % (PROJECT_OWNER, PROJECT_NAME)

RELEASES = [
    ("15.05", "b16ac25cdc0f2b64d6af34ea1e6ff253d8a71ee4"),
    ("15.07", "e44c8db9dea56b8d1a2f941ce572b0f14e999d4c"),
    ("15.10", "ef55279d58eced4b90632a572a8fc5a227ceefb9"),
    ("16.01", "cc23adb0a962f1c9780b838604718319a0a71888"),
]

# Uncredit pull requestors... kind of arbitrary at this point.
DEVTEAM = [
    "afgane", "dannon", "blankenberg",
    "davebx", "martenson", "jmchilton",
    "tnabtaf", "natefoo", "carlfeberhard",
    "jgoecks", "guerler", "jennaj",
    "nekrut", "jxtx", "nitesh1989"
]

TEMPLATE = """
.. to_doc

-------------------------------
%s
-------------------------------

.. announce_start

Enhancements
-------------------------------

.. major_feature


.. feature


.. enhancement


.. small_enhancement



Fixes
-------------------------------

.. major_bug


.. bug


.. github_links
"""

ANNOUNCE_TEMPLATE = string.Template("""
===========================================================
${month_name} 20${year} Galaxy Release (v ${release})
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

      % git checkout v${release}


`BitBucket <https://bitbucket.org/galaxy/galaxy-dist>`__
===========================================================

Upgrade
  .. code-block:: shell

      % hg pull
      % hg update latest_${release}


See `our wiki <https://wiki.galaxyproject.org/Develop/SourceCode>`__ for additional details regarding the source code locations.

Release Notes
===========================================================

.. include:: ${release}.rst
   :start-after: announce_start

.. include:: _thanks.rst
""")

NEXT_TEMPLATE = string.Template("""
===========================================================
${month_name} 20${year} Galaxy Release (v ${version})
===========================================================


Schedule
===========================================================
 * Planned Freeze Date: ${freeze_date}
 * Planned Release Date: ${release_date}
""")

# https://api.github.com/repos/galaxyproject/galaxy/pulls?base=dev&state=closed
# https://api.github.com/repos/galaxyproject/galaxy/pulls?base=release_15.07&state=closed
# https://api.github.com/repos/galaxyproject/galaxy/compare/release_15.05...dev


def commit_time(commit_hash):
    api_url = urlparse.urljoin(PROJECT_API, "commits/%s" % commit_hash)
    req = requests.get(api_url).json()
    return datetime.datetime.strptime(req["commit"]["committer"]["date"], "%Y-%m-%dT%H:%M:%SZ")


def do_release(argv):
    release_name = argv[2]
    release_file = _release_file(release_name + ".rst")
    release_info = TEMPLATE % release_name
    open(release_file, "w").write(release_info.encode("utf-8"))
    month = int(release_name.split(".")[1])
    month_name = calendar.month_name[month]
    year = release_name.split(".")[0]

    announce_info = ANNOUNCE_TEMPLATE.substitute(
        month_name=month_name,
        year=year,
        release=release_name
    )
    announce_file = _release_file(release_name + "_announce.rst")
    open(announce_file, "w").write(announce_info.encode("utf-8"))

    next_month = (((month - 1) + 3) % 12) + 1
    next_month_name = calendar.month_name[next_month]
    if next_month < 3:
        next_year = int(year) + 1
    else:
        next_year = year
    next_version = "%s.%02d" % (next_year, next_month)
    first_of_next_month = datetime.date(int(next_year) + 2000, next_month, 1)
    freeze_date = next_weekday(first_of_next_month, 0)
    release_date = next_weekday(first_of_next_month, 0) + datetime.timedelta(21)

    next_release_file = _release_file(next_version + "_announce.rst")
    next_announce = NEXT_TEMPLATE.substitute(
        version=next_version,
        year=next_year,
        month_name=next_month_name,
        freeze_date=freeze_date,
        release_date=release_date,
    )
    open(next_release_file, "w").write(next_announce.encode("utf-8"))

    for page in _get_prs():
        for pr in page:
            merged_at = pr.merged_at
            milestone = pr.milestone
            if not merged_at or not milestone or milestone['title'] != release_name:
                continue
            # 2015-06-29 18:32:13 2015-04-22 19:11:53 2015-08-12 21:15:45
            as_dict = {
                "title": pr.title,
                "number": pr.number,
                "head": pr.head,
            }
            main([argv[0], "--release_file", "%s.rst" % release_name, "--request", as_dict, "pr" + str(pr.number)])


def _get_prs():
    github = _github_client()
    pull_requests = github.pull_requests.list(
        state='closed',
        user=PROJECT_OWNER,
        repo=PROJECT_NAME,
    )
    return pull_requests


def main(argv):
    if requests is None:
        raise Exception("Requests library not found, please pip install requests")
    github = _github_client()
    newest_release = None

    if argv[1] == "--release":
        do_release(argv)
        return

    if argv[1] == "--release_file":
        newest_release = argv[2]
        argv = [argv[0]] + argv[3:]

    if argv[1] == "--request":
        req = argv[2]
        argv = [argv[0]] + argv[3:]
    else:
        req = None

    releases_path = os.path.join(PROJECT_DIRECTORY, "doc", "source", "releases")
    if newest_release is None:
        newest_release = sorted(os.listdir(releases_path))[-1]
    history_path = os.path.join(releases_path, newest_release)
    history = open(history_path, "r").read().decode("utf-8")

    def extend(from_str, line):
        from_str += "\n"
        return history.replace(from_str, from_str + line + "\n" )

    ident = argv[1]

    message = ""
    if len(argv) > 2:
        message = argv[2]
    elif not (ident.startswith("pr") or ident.startswith("issue")):
        api_url = urlparse.urljoin(PROJECT_API, "commits/%s" % ident)
        if req is None:
            req = requests.get(api_url).json()
        commit = req["commit"]
        message = commit["message"]
        message = get_first_sentence(message)
    elif requests is not None and ident.startswith("pr"):
        pull_request = ident[len("pr"):]
        api_url = urlparse.urljoin(PROJECT_API, "pulls/%s" % pull_request)
        if req is None:
            req = requests.get(api_url).json()
        message = req["title"]
    elif requests is not None and ident.startswith("issue"):
        issue = ident[len("issue"):]
        api_url = urlparse.urljoin(PROJECT_API, "issues/%s" % issue)
        if req is None:
            req = requests.get(api_url).json()
        message = req["title"]
    else:
        message = ""

    text_target = "to_doc"
    to_doc = message + " "

    owner = None
    if ident.startswith("pr"):
        pull_request = ident[len("pr"):]
        user = req["head"]["user"]
        owner = user["login"]
        if owner in DEVTEAM:
            owner = None
        text = ".. _Pull Request {0}: {1}/pull/{0}".format(pull_request, PROJECT_URL)
        history = extend(".. github_links", text)
        if owner:
            to_doc += "\n(Thanks to `@%s <https://github.com/%s>`__.)" % (
                owner, owner,
            )
        to_doc += "\n`Pull Request {0}`_".format(pull_request)
        if github:
            labels = []
            try:
                labels = github.issues.labels.list_by_issue(int(pull_request), user=PROJECT_OWNER, repo=PROJECT_NAME)
            except Exception:
                pass
            is_bug = is_enhancement = is_feature = is_minor = is_major = is_merge = is_small_enhancement = False
            for label in labels:
                label_name = label.name.lower()
                if label_name == "minor":
                    is_minor = True
                elif label_name == "major":
                    is_major = True
                elif label_name == "merge":
                    is_merge = True
                elif label_name == "kind/bug":
                    is_bug = True
                elif label_name == "kind/feature":
                    is_feature = True
                elif label_name == "kind/enhancement":
                    is_enhancement = True
                elif label_name in ["kind/testing", "kind/refactoring"]:
                        is_small_enhancement = True

            is_some_kind_of_enhancement = is_enhancement or is_feature or is_small_enhancement

            if not( is_bug or is_some_kind_of_enhancement or is_minor or is_merge ):
                print "No kind/ or minor or merge label found for %s" % pull_request
                text_target = None

            if is_minor or is_merge:
                return

            if is_some_kind_of_enhancement and is_major:
                text_target = "major_feature"
            elif is_feature:
                text_target = "feature"
            elif is_enhancement:
                text_target = "enhancement"
            elif is_some_kind_of_enhancement:
                text_target = "small_enhancement"
            elif is_major:
                text_target = "major_bug"
            elif is_bug:
                text_target = "bug"
            else:
                print "Logic problem, cannot determine section for %s" % pull_request
                text_target = None
    elif ident.startswith("issue"):
        issue = ident[len("issue"):]
        text = ".. _Issue {0}: {1}/issues/{0}".format(issue, PROJECT_URL)
        history = extend(".. github_links", text)
        to_doc += "`Issue {0}`_".format(issue)
    else:
        short_rev = ident[:7]
        text = ".. _{0}: {1}/commit/{0}".format(short_rev, PROJECT_URL)
        history = extend(".. github_links", text)
        to_doc += "{0}_".format(short_rev)

    to_doc = wrap(to_doc)
    history = extend(".. %s\n" % text_target, to_doc)
    open(history_path, "w").write(history.encode("utf-8"))


def _github_client():
    if Github:
        github_json = os.path.expanduser("~/.github.json")
        github = Github(**json.load(open(github_json, "r")))
    else:
        github = None
    return github


def _release_file(release):
    releases_path = os.path.join(PROJECT_DIRECTORY, "doc", "source", "releases")
    if release is None:
        release = sorted(os.listdir(releases_path))[-1]
    history_path = os.path.join(releases_path, release)
    return history_path


def get_first_sentence(message):
    first_line = message.split("\n")[0]
    return first_line


def process_sentence(message):
    # Strip tags like [15.07].
    message = re.sub("^\s*\[.*\]\s*", "", message)
    # Link issues and pull requests...
    issue_url = "https://github.com/%s/%s/issues" % (PROJECT_OWNER, PROJECT_NAME)
    message = re.sub(r'#(\d+)', r'`#\1 <%s/\1>`__' % issue_url, message)
    return message


def wrap(message):
    message = process_sentence(message)
    wrapper = textwrap.TextWrapper(initial_indent="* ")
    wrapper.subsequent_indent = '  '
    wrapper.width = 78
    message_lines = message.splitlines()
    first_lines = "\n".join(wrapper.wrap(message_lines[0]))
    wrapper.initial_indent = "  "
    rest_lines = "\n".join(["\n".join(wrapper.wrap(m)) for m in message_lines[1:]])
    return first_lines + ("\n" + rest_lines if rest_lines else "")


def next_weekday(d, weekday):
    """ Return the next week day (0 for Monday, 6 for Sunday) starting from ``d``. """
    days_ahead = weekday - d.weekday()
    if days_ahead <= 0:  # Target day already happened this week
        days_ahead += 7
    return d + datetime.timedelta(days_ahead)


if __name__ == "__main__":
    main(sys.argv)
