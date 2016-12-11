#!/usr/bin/env python
# Little script to make HISTORY.rst more easy to format properly, lots TODO
# pull message down and embed, use arg parse, handle multiple, etc...
from __future__ import print_function

import ast
import calendar
import datetime
import json
import os
import re
import string
import sys
import textwrap

try:
    import requests
except ImportError:
    requests = None
try:
    from pygithub3 import Github
except ImportError:
    Github = None
from six import string_types
from six.moves.urllib.parse import urljoin

PROJECT_DIRECTORY = os.path.join(os.path.dirname(__file__), os.pardir)
SOURCE_DIR = os.path.join(PROJECT_DIRECTORY, "lib")
GALAXY_SOURCE_DIR = os.path.join(SOURCE_DIR, "galaxy")
GALAXY_VERSION_FILE = os.path.join(GALAXY_SOURCE_DIR, "version.py")
PROJECT_OWNER = "galaxyproject"
PROJECT_NAME = "galaxy"
PROJECT_URL = "https://github.com/%s/%s" % (PROJECT_OWNER, PROJECT_NAME)
PROJECT_API = "https://api.github.com/repos/%s/%s/" % (PROJECT_OWNER, PROJECT_NAME)
RELEASES_PATH = os.path.join(PROJECT_DIRECTORY, "doc", "source", "releases")
RELEASE_DELTA_MONTHS = 4  # Number of months between releases.

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

%s
===============================

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

New Galaxy repository
  .. code-block:: shell

      $$ git clone -b release_${release} https://github.com/galaxyproject/galaxy.git

Update of existing Galaxy repository
  .. code-block:: shell

      $$ git checkout release_${release} && git pull --ff-only origin release_${release}

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


RELEASE_ISSUE_TEMPLATE = string.Template("""

- [X] **Prep**

      - [X] ~~Create this release issue ``make release-issue RELEASE_CURR=${version}``.~~
      - [X] ~~Set freeze date (${freeze_date}).~~

- [ ] **Branch Release (on or around ${freeze_date})**

      - [ ] Ensure all [blocking milestone PRs](https://github.com/galaxyproject/galaxy/pulls?q=is%3Aopen+is%3Apr+milestone%3A${version}) have been merged, delayed, or closed.

            make release-check-blocking-prs RELEASE_CURR=${version}
      - [ ] Merge the latest release into dev and push upstream.

            make release-merge-stable-to-next RELEASE_PREVIOUS=release_${previous_version}
            make release-push-dev

      - [ ] Create and push release branch:

            make release-create-rc RELEASE_CURR=${version} RELEASE_NEXT=${next_version}

      - [ ] Open PRs from your fork of branch ``version-${version}`` to upstream ``release_${version}`` and of ``version-${next_version}.dev`` to ``dev``.

      - [ ] Open PR against ``release_${version}`` branch to pin flake8 deps in tox.ini to the latest available version.

      - [ ] Update ``next_milestone`` in [P4's configuration](https://github.com/galaxyproject/p4) to `${next_version}` so it properly tags new PRs.

- [ ] **Deploy and Test Release**

      - [ ] Update test.galaxyproject.org to ensure it is running a dev at or past branch point (${freeze_date} + 1 day).
      - [ ] Update testtoolshed.g2.bx.psu.edu to ensure it is running a dev at or past branch point (${freeze_date} + 1 day).
      - [ ] Deploy to usegalaxy.org (${freeze_date} + 1 week).
      - [ ] Deploy to toolshed.g2.bx.psu.edu (${freeze_date} + 1 week).
      - [ ] [Update BioBlend CI testing](https://github.com/galaxyproject/bioblend/commit/b74b1c302a1b8fed86786b40d7ecc3520cbadcd3) to include a ``release_${version}`` target: add ``- TOX_ENV=py27 GALAXY_VERSION=release_${version}`` to the ``env`` list in ``.travis.yml`` .

- [ ] **Create Release Notes**

      - [ ] Review merged PRs and ensure they all have a milestones attached. [Link](https://github.com/galaxyproject/galaxy/pulls?q=is%3Apr+is%3Amerged+no%3Amilestone)
      - [ ] Checkout release branch

            git checkout release_${version} -b ${version}_release_notes
      - [ ] Check for obvious missing metadata in release PRs

            make release-check-metadata RELEASE_CURR=${version}
      - [ ] Bootstrap the release notes

            make release-bootstrap-history RELEASE_CURR=${version}
      - [ ] Open newly created files and manually curate major topics and release notes.

            - [ ] inject 3 witty comments
            - [ ] inject one whimsical story
            - [ ] inject one topical reference (preferably satirical in nature) to contemporary world event
      - [ ] Commit release notes.

            git add docs/; git commit -m "Release notes for $version"; git push upstream ${version}_release_notes
      - [ ] Open a pull request for new release note branch.
      - [ ] Merge release note pull request.

- [ ] **Do Release**

      - [ ] Ensure all [blocking milestone issues](https://github.com/galaxyproject/galaxy/issues?q=is%3Aopen+is%3Aissue+milestone%3A${version}) have been resolved.

            make release-check-blocking-issues RELEASE_CURR=${version}
      - [ ] Ensure all [blocking milestone PRs](https://github.com/galaxyproject/galaxy/pulls?q=is%3Aopen+is%3Apr+milestone%3A${version}) have been merged or closed.

            make release-check-blocking-prs RELEASE_CURR=${version}
      - [ ] Ensure previous release is merged into current. (TODO: Add Makefile target or this.)
      - [ ] Create and push release tag:

            make release-create RELEASE_CURR=${version}

- [ ] **Do Docker Release**

      - [ ] Change the [dev branch](https://github.com/bgruening/docker-galaxy-stable/tree/dev
) of the Galaxy Docker container to ${next_version}
      - [ ] Merge dev into master

- [ ] **Ensure Tool Tests use Latest Release**

      - [ ]  Update GALAXY_RELEASE in https://github.com/galaxyproject/tools-iuc/blob/master/.travis.yml#L6

      - [ ]  Update GALAXY_RELEASE in https://github.com/galaxyproject/tools-devteam/blob/master/.travis.yml#L6

- [ ] **Announce Release**

      - [ ] Verify release included in https://docs.galaxyproject.org/en/master/releases/index.html
      - [ ] Review announcement in https://github.com/galaxyproject/galaxy/blob/dev/doc/source/releases/${version}_announce.rst
      - [ ] Stage annoucement content (Wiki, Biostars, Bit.ly link) on annouce date to capture date tags. Note: all final content does not need to be completed to do this.
      - [ ] Create wiki *highlights* and post to http://galaxyproject.org News (w/ RSS) and NewsBriefs. [An Example](https://wiki.galaxyproject.org/News/2016_04_GalaxyRelease).
      - [ ] Tweet docs news *highlights* via bit.ly link to https://twitter.com/galaxyproject/ (As user ``galaxyproject``, password in Galaxy password store under ``twitter.com / galaxyproject`` ). [An Example](https://twitter.com/galaxyproject/status/733029921316986881).
      - [ ] Post *highlights* type News to Galaxy Biostars https://biostar.usegalaxy.org. [An Example](https://biostar.usegalaxy.org/p/17712/).
      - [ ] Email *highlights* to [galaxy-dev](http://dev.list.galaxyproject.org/) and [galaxy-announce](http://announce.list.galaxyproject.org/) @lists.galaxyproject.org. [An Example](http://dev.list.galaxyproject.org/The-Galaxy-release-16-04-is-out-tp4669419.html)
      - [ ] Adjust http://getgalaxy.org text and links to match current master branch (TODO: describe how to do this)

- [ ] **Prepare for next release**

      - [ ] Ensure milestone ``${next_version}`` exists.
      - [ ] Create release issue for next version ``make release-issue RELEASE_CURR=${next_version}``.
      - [ ] Schedule committer meeting to discuss re-alignment of priorities.
      - [ ] Close this issue.

""")

# https://api.github.com/repos/galaxyproject/galaxy/pulls?base=dev&state=closed
# https://api.github.com/repos/galaxyproject/galaxy/pulls?base=release_15.07&state=closed
# https://api.github.com/repos/galaxyproject/galaxy/compare/release_15.05...dev


def commit_time(commit_hash):
    api_url = urljoin(PROJECT_API, "commits/%s" % commit_hash)
    req = requests.get(api_url).json()
    return datetime.datetime.strptime(req["commit"]["committer"]["date"], "%Y-%m-%dT%H:%M:%SZ")


def release_issue(argv):
    release_name = argv[2]
    previous_release = _previous_release(release_name)
    new_version_params = _next_version_params(release_name)
    next_version = new_version_params["version"]
    freeze_date, release_date = _release_dates(release_name)
    release_issue_template_params = dict(
        version=release_name,
        next_version=next_version,
        previous_version=previous_release,
        freeze_date=freeze_date,
    )
    release_issue_contents = RELEASE_ISSUE_TEMPLATE.safe_substitute(**release_issue_template_params)
    github = _github_client()
    github.issues.create(
        data=dict(
            title="Publication of Galaxy Release v %s" % release_name,
            body=release_issue_contents,
        ),
        user=PROJECT_OWNER,
        repo=PROJECT_NAME,
    )
    return release_issue


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

    next_version_params = _next_version_params(release_name)
    next_version = next_version_params["version"]
    next_release_file = _release_file(next_version + "_announce.rst")

    next_announce = NEXT_TEMPLATE.substitute(**next_version_params)
    open(next_release_file, "w").write(next_announce.encode("utf-8"))
    releases_index = _release_file("index.rst")
    releases_index_contents = open(releases_index, "r").read()
    releases_index_contents = releases_index_contents.replace(".. annoucements\n", ".. annoucements\n   " + next_version + "_announce\n" )
    with open(releases_index, "w") as f:
        f.write(releases_index_contents)

    for pr in _get_prs(release_name):
        # 2015-06-29 18:32:13 2015-04-22 19:11:53 2015-08-12 21:15:45
        as_dict = {
            "title": pr.title,
            "number": pr.number,
            "head": pr.head,
        }
        main([argv[0], "--release_file", "%s.rst" % release_name, "--request", as_dict, "pr" + str(pr.number)])


def check_release(argv):
    github = _github_client()
    release_name = argv[2]
    for pr in _get_prs(release_name):
        _text_target(github, pr)


def check_blocking_prs(argv):
    release_name = argv[2]
    block = 0
    for pr in _get_prs(release_name, state="open"):
        print("WARN: Blocking PR| %s" % _pr_to_str(pr))
        block = 1

    sys.exit(block)


def check_blocking_issues(argv):
    release_name = argv[2]
    block = 0
    github = _github_client()
    issues = github.issues.list_by_repo(
        user='galaxyproject',
        repo='galaxy',
        state="open"
    )
    for page in issues:
        for issue in page:
            if issue.milestone and issue.milestone.title == release_name and "Publication of Galaxy Release" not in issue.title:
                print("WARN: Blocking issue| %s" % _issue_to_str(issue))
                block = 1

    sys.exit(block)


def _pr_to_str(pr):
    if isinstance(pr, string_types):
        return pr
    return "PR #%s (%s) %s" % (pr.number, pr.title, pr.html_url)


def _issue_to_str(pr):
    if isinstance(pr, string_types):
        return pr
    return "Issue #%s (%s) %s" % (pr.number, pr.title, pr.html_url)


def _next_version_params(release_name):
    month = int(release_name.split(".")[1])
    year = release_name.split(".")[0]
    next_month = (((month - 1) + RELEASE_DELTA_MONTHS) % 12) + 1
    next_month_name = calendar.month_name[next_month]
    if next_month < RELEASE_DELTA_MONTHS:
        next_year = int(year) + 1
    else:
        next_year = year
    next_version = "%s.%02d" % (next_year, next_month)
    freeze_date, release_date = _release_dates(next_version)
    return dict(
        version=next_version,
        year=next_year,
        month_name=next_month_name,
        freeze_date=freeze_date,
        release_date=release_date,
    )


def _release_dates(version):
    year, month = version.split(".")
    first_of_month = datetime.date(int(year) + 2000, int(month), 1)
    freeze_date = next_weekday(first_of_month, 0)
    release_date = next_weekday(first_of_month, 0) + datetime.timedelta(21)
    return freeze_date, release_date


def _get_prs(release_name, state="closed"):
    github = _github_client()
    pull_requests = github.pull_requests.list(
        state=state,
        user=PROJECT_OWNER,
        repo=PROJECT_NAME,
    )
    for page in pull_requests:
        for pr in page:
            merged_at = pr.merged_at
            milestone = pr.milestone
            proper_state = state != "closed" or merged_at
            if not proper_state or not milestone or milestone['title'] != release_name:
                continue
            yield pr


def main(argv):
    if requests is None:
        raise Exception("Requests library not found, please pip install requests")
    github = _github_client()
    newest_release = None

    if argv[1] == "--check-blocking-prs":
        check_blocking_prs(argv)
        return

    if argv[1] == "--check-blocking-issues":
        check_blocking_issues(argv)
        return

    if argv[1] == "--create-release-issue":
        release_issue(argv)
        return

    if argv[1] == "--release":
        do_release(argv)
        return

    if argv[1] == "--check-release":
        check_release(argv)
        return

    if argv[1] == "--release_file":
        newest_release = argv[2]
        argv = [argv[0]] + argv[3:]

    if argv[1] == "--request":
        req = argv[2]
        argv = [argv[0]] + argv[3:]
    else:
        req = None

    if newest_release is None:
        newest_release = sorted(os.listdir(RELEASES_PATH))[-1]
    history_path = os.path.join(RELEASES_PATH, newest_release)
    history = open(history_path, "r").read().decode("utf-8")

    def extend(from_str, line, source=history):
        from_str += "\n"
        return source.replace(from_str, from_str + line + "\n" )

    ident = argv[1]

    message = ""
    if len(argv) > 2:
        message = argv[2]
    elif not (ident.startswith("pr") or ident.startswith("issue")):
        api_url = urljoin(PROJECT_API, "commits/%s" % ident)
        if req is None:
            req = requests.get(api_url).json()
        commit = req["commit"]
        message = commit["message"]
        message = get_first_sentence(message)
    elif requests is not None and ident.startswith("pr"):
        pull_request = ident[len("pr"):]
        api_url = urljoin(PROJECT_API, "pulls/%s" % pull_request)
        if req is None:
            req = requests.get(api_url).json()
        message = req["title"]
    elif requests is not None and ident.startswith("issue"):
        issue = ident[len("issue"):]
        api_url = urljoin(PROJECT_API, "issues/%s" % issue)
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
            to_doc += "\n(thanks to `@%s <https://github.com/%s>`__)." % (
                owner, owner,
            )
        to_doc += "\n`Pull Request {0}`_".format(pull_request)
        if github:
            text_target = _text_target(github, pull_request)
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
    history = extend(".. %s\n" % text_target, to_doc, history)
    open(history_path, "w").write(history.encode("utf-8"))


def _text_target(github, pull_request):
    labels = []
    pr_number = None
    if isinstance(pull_request, string_types):
        pr_number = pull_request
    else:
        pr_number = pull_request.number

    try:
        labels = github.issues.labels.list_by_issue(int(pr_number), user=PROJECT_OWNER, repo=PROJECT_NAME)
    except Exception as e:
        print(e)
    is_bug = is_enhancement = is_feature = is_minor = is_major = is_merge = is_small_enhancement = False
    if len(labels) == 0:
        print('No labels found for %s' % pr_number)
        return None
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
        print("No kind/ or minor or merge label found for %s" % _pr_to_str(pull_request))
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
        print("Logic problem, cannot determine section for %s" % _pr_to_str(pull_request))
        text_target = None
    return text_target


def _previous_release(to):
    previous_release = None
    for release in _releases():
        if release == to:
            break

        previous_release = release

    return previous_release


def _latest_release():
    return _releases()[-1]


def _releases():
    all_files = sorted(os.listdir(RELEASES_PATH))
    release_note_file_pattern = re.compile(r"\d+\.\d+.rst")
    release_note_files = [f for f in all_files if release_note_file_pattern.match(f)]
    return sorted(f.rstrip('.rst') for f in release_note_files)


def _get_major_version():
    with open(GALAXY_VERSION_FILE, 'rb') as f:
        init_contents = f.read().decode('utf-8')

        def get_var(var_name):
            pattern = re.compile(r'%s\s+=\s+(.*)' % var_name)
            match = pattern.search(init_contents).group(1)
            return str(ast.literal_eval(match))
        return get_var("VERSION_MAJOR")


def _get_release_name(argv):
    if len(argv) > 2:
        return argv[2]
    else:
        return _get_major_version()


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
