#!/usr/bin/env python
# Little script to make HISTORY.rst more easy to format properly, lots TODO
# pull message down and embed, use arg parse, handle multiple, etc...

import datetime
import os
import re
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
    ("15.10", "d554136658e165c84a42b988f39009c185325919"),
]

# Uncredit pull requestors... kind of arbitrary at this point.
DEVTEAM = ["afgane", "dannon", "blankenberg", "davebx", "martenson", "jmchilton", "tnabtaf", "natefoo", "carlfeberhard", "jgoecks", "guerler", "jennaj", "nekrut", "jxtx", "nitesh1989"]

TEMPLATE = """
.. to_doc

-------------------------------
%s
-------------------------------

Enhancements
-------------------------------

.. enhancements


Fixes
-------------------------------


.. fixes


.. github_links
"""

# TODO: for 15.10 use this template...
ANNOUNCE_TEMPLATE = """
===========================================================
TODO Galaxy Release (v %s)
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

      % git checkout v%s


`BitBucket <https://bitbucket.org/galaxy/galaxy-dist>`__
===========================================================

Upgrade
  .. code-block:: shell

      % hg pull
      % hg update latest_%s


See `our wiki <https://wiki.galaxyproject.org/Develop/SourceCode>`__ for additional details regarding the source code locations.

Release Notes
===========================================================

.. include:: %s.rst
   :start-after: enhancements

.. include:: _thanks.rst
"""


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
    print release_info
    release_commit_start = None
    release_commit_end = None

    for i, release_info in enumerate(RELEASES):
        if release_name == release_info[0]:
            release_commit_start = release_info[1]
            release_commit_end = RELEASES[i + 1][1]

    if release_commit_start is None:
        raise Exception("Failed to find information for version %s" % release_name)

    start_release_time = commit_time(release_commit_start)
    end_release_time = commit_time(release_commit_end)

    for page in _get_prs():
        for pr in page:
            base_label = pr.base['label']
            if base_label == "galaxyproject:dev":
                merged_at = pr.merged_at
                if merged_at is None:
                    continue
                before_branch = merged_at < start_release_time
                after_branch = merged_at > end_release_time
                print "%s %s %s" % (merged_at, start_release_time, end_release_time)
                if before_branch or after_branch:
                    print "SKIPPING"
                    continue
            elif base_label != "galaxyproject:release_%s" % release_name:
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
    pull_requests = github.pull_requests.list(state='closed', user=PROJECT_OWNER, repo=PROJECT_NAME)
    return pull_requests


def main(argv):
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
            to_doc += "(Thanks to `@%s <https://github.com/%s>`__.) " % (
                owner, owner,
            )
        to_doc += "`Pull Request {0}`_".format(pull_request)
        if github:
            labels = []
            try:
                labels = github.issues.labels.list_by_issue(int(pull_request), user=PROJECT_OWNER, repo=PROJECT_NAME)
            except:
                pass
            is_bug = is_enhancement = False
            for label in labels:
                if label.name == "bug":
                    is_bug = True
                if label.name == "enhancement":
                    is_enhancement = True
            if is_enhancement:
                text_target = "enhancements"
            elif is_bug:
                text_target = "fixes"
            else:
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
    return "\n".join(wrapper.wrap(message))

if __name__ == "__main__":
    main(sys.argv)
