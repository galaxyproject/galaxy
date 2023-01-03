#!/usr/bin/env python
# Little script to make HISTORY.rst more easy to format properly, lots TODO
# pull message down and embed, use arg parse, handle multiple, etc...

import calendar
import datetime
import json
import os
import re
import string
import sys
import textwrap
from collections import OrderedDict
from urllib.parse import urljoin

import requests
from github import Github

PROJECT_DIRECTORY = os.path.join(os.path.dirname(__file__), os.pardir)
GALAXY_VERSION_FILE = os.path.join(PROJECT_DIRECTORY, "lib", "galaxy", "version.py")
PROJECT_OWNER = "galaxyproject"
PROJECT_NAME = "galaxy"
PROJECT_URL = f"https://github.com/{PROJECT_OWNER}/{PROJECT_NAME}"
PROJECT_API = f"https://api.github.com/repos/{PROJECT_OWNER}/{PROJECT_NAME}/"
RELEASES_PATH = os.path.join(PROJECT_DIRECTORY, "doc", "source", "releases")
RELEASE_DELTA_MONTHS = 4  # Number of months between releases.

TEMPLATE = """
.. to_doc

${release}
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


.. include:: ${release}_prs.rst

"""

ANNOUNCE_TEMPLATE = string.Template(
    """
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

Also check out the `${release} user release notes <${release}_announce_user.html>`__

Get Galaxy
==========

The code lives at `GitHub <https://github.com/galaxyproject/galaxy>`__ and you should have `Git <https://git-scm.com/>`__ to obtain it.

To get a new Galaxy repository run:
  .. code-block:: shell

      $$ git clone -b release_${release} https://github.com/galaxyproject/galaxy.git

To update an existing Galaxy repository run:
  .. code-block:: shell

      $$ git fetch origin && git checkout release_${release} && git pull --ff-only origin release_${release}

See the `community hub <https://galaxyproject.org/develop/source-code/>`__ for additional details on source code locations.

Release Notes
===========================================================

.. include:: ${release}.rst
   :start-after: announce_start

.. include:: _thanks.rst
"""
)

ANNOUNCE_USER_TEMPLATE = string.Template(
    """
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


New Visualizations
===========================================================

.. visualizations

New Datatypes
===========================================================

.. datatypes

Builtin Tool Updates
===========================================================

.. tools

Release Testing Team
===========================================================

A special thanks to the release testing team for testing many of the new features and reporting many bugs:

<team members go here>

Release Notes
===========================================================

Please see the :doc:`full release notes <${release}_announce>` for more details.

.. include:: ${release}_prs.rst

.. include:: _thanks.rst
"""
)

NEXT_TEMPLATE = string.Template(
    """
:orphan:

===========================================================
${month_name} 20${year} Galaxy Release (v ${version})
===========================================================


Schedule
===========================================================
 * Planned Freeze Date: ${freeze_date}
 * Planned Release Date: ${release_date}
"""
)

PRS_TEMPLATE = """
.. github_links
"""

RELEASE_ISSUE_TEMPLATE = string.Template(
    """

- [X] **Prep**

    - [X] ~~Create this release issue ``make release-issue``.~~
    - [X] ~~Set freeze date (${freeze_date}).~~

- [ ] **Branch Release (on or around ${freeze_date})**

    - [ ] Ensure all [blocking milestone PRs](https://github.com/galaxyproject/galaxy/pulls?q=is%3Aopen+is%3Apr+milestone%3A${version}) have been merged, delayed, or closed.

          make release-check-blocking-prs

    - [ ] Merge the latest release into dev and push upstream.

          make release-merge-stable-to-next RELEASE_PREVIOUS=release_${previous_version}
          make release-push-dev

    - [ ] Create and push release branch:

          make release-create-rc

    - [ ] Create dev packages:

          cd packages && DEV_RELEASE=1 ./build_packages.sh


    - [ ] Review created packages (HISTORY.rst correct, setup.cfg correct, correct version in filename)
    - [ ] Upload galaxy-util & galaxy-tool-util dev packages to pypi
    - [ ] Open PR against planemo with a pin to the dev packages
    - [ ] Open PRs from your fork of branch ``version-${version}`` to upstream ``release_${version}`` and of ``version-${next_version}.dev`` to ``dev``.
    - [ ] Update ``MILESTONE_NUMBER`` in the [maintenance bot](https://github.com/galaxyproject/galaxy/blob/dev/.github/workflows/maintenance_bot.yaml) to `${next_version}` so it properly tags new PRs.

- [ ] **Issue Review Timeline Notes**

    - [ ] Ensure any security fixes will be ready prior to ${freeze_date} + 1 week, to allow time for notification prior to release.
    - [ ] Ensure ownership of outstanding bugfixes and track progress during freeze.

- [ ] **Deploy and Test Release**

    - [ ] Update test.galaxyproject.org to ensure it is running a dev at or past branch point (${freeze_date} + 1 day).
    - [ ] Update testtoolshed.g2.bx.psu.edu to ensure it is running a dev at or past branch point (${freeze_date} + 1 day).
    - [ ] Deploy to usegalaxy.org (${freeze_date} + 1 week).
    - [ ] Deploy to toolshed.g2.bx.psu.edu (${freeze_date} + 1 week).
    - [ ] [Update BioBlend CI testing](https://github.com/galaxyproject/bioblend/commit/b74b1c302a1b8fed86786b40d7ecc3520cbadcd3) to include a ``release_${version}`` target: add ``- TOX_ENV=py27 GALAXY_VERSION=release_${version}`` to the ``env`` list in ``.travis.yml`` .
    - [ ] Update GALAXY_RELEASE in IUC and devteam github workflows
        - [ ] https://github.com/galaxyproject/tools-iuc/blob/master/.github/workflows/
        - [ ] https://github.com/galaxyproject/tools-devteam/blob/master/.github/workflows/

- [ ] **Create Release Notes**

    - [ ] Review merged PRs and ensure they all have a milestones attached. [Link](https://github.com/galaxyproject/galaxy/pulls?utf8=%E2%9C%93&q=is%3Apr+is%3Amerged+no%3Amilestone+-label%3Amerge+)
    - [ ] Checkout release branch

          git checkout release_${version} -b ${version}_release_notes
    - [ ] Check for obvious missing metadata in release PRs

          make release-check-metadata RELEASE_CURR=${version}
    - [ ] Bootstrap the release notes

          make release-bootstrap-history RELEASE_CURR=${version}
    - [ ] Open newly created files and manually curate major topics and release notes.
    - [ ] Run python scripts/scripts/release-diff.py release_${previous_version} and add configuration changes to release notes.
    - [ ] Add new release to doc/source/releases/index.rst
    - [ ] Commit release notes.

          git add docs/; git commit -m "Release notes for $version"; git push upstream ${version}_release_notes
    - [ ] Open a pull request for new release note branch.
    - [ ] Merge release note pull request.

- [ ] **Do Release**

    - [ ] Ensure all [blocking milestone issues](https://github.com/galaxyproject/galaxy/issues?q=is%3Aopen+is%3Aissue+milestone%3A${version}) have been resolved.

          make release-check-blocking-issues RELEASE_CURR=${version}
    - [ ] Ensure all [blocking milestone PRs](https://github.com/galaxyproject/galaxy/pulls?q=is%3Aopen+is%3Apr+milestone%3A${version}) have been merged or closed.

          make release-check-blocking-prs RELEASE_CURR=${version}
    - [ ] Ensure all PRs merged into the pre-release branch during the freeze have [milestones attached](https://github.com/galaxyproject/galaxy/pulls?q=is%3Apr+is%3Aclosed+base%3Arelease_${version}+is%3Amerged+no%3Amilestone) and that they are the not [${next_version} milestones](https://github.com/galaxyproject/galaxy/pulls?q=is%3Apr+is%3Aclosed+base%3Arelease_${version}+is%3Amerged+milestone%3A${next_version})
    - [ ] Ensure release notes include all PRs added during the freeze by re-running the release note bootstrapping:

          make release-bootstrap-history
    - [ ] Ensure previous release is merged into current. [GitHub branch comparison](https://github.com/galaxyproject/galaxy/compare/release_${version}...release_${previous_version})
    - [ ] Create and push release tag:

          make release-create

    - [ ] Create dev packages:

          cd packages && ./build_packages.sh


    - [ ] Review created packages (HISTORY.rst correct, setup.cfg correct, correct version in filename)
    - [ ] Upload built packages to pypi
    - [ ] Add the branch `*/release_{version}` to Jenkins documentation build [configuration matrix](https://jenkins.galaxyproject.org/job/galaxy-sphinx-by-branch/configure).
    - [ ] Trigger the [branch documentation build](https://jenkins.galaxyproject.org/job/galaxy-sphinx-by-branch/)
    - [ ] Verify that everything is merged from ${version}->master, and then trigger the ['latest' documentation build](https://jenkins.galaxyproject.org/job/latest-Sphinx-Docs/)

- [ ] **Do Docker Release**

    - [ ] Change the [dev branch](https://github.com/bgruening/docker-galaxy-stable/tree/dev) of the Galaxy Docker container to ${next_version}
    - [ ] Merge dev into master

- [ ] **Announce Release**

    - [ ] Verify release included in https://docs.galaxyproject.org/en/master/releases/index.html
    - [ ] Review announcement in https://github.com/galaxyproject/galaxy/blob/dev/doc/source/releases/${version}_announce.rst
    - [ ] Stage announcement content (Hub, Galaxy Help, etc.) on announce date to capture date tags. Note: all final content does not need to be completed to do this.
    - [ ] Create hub *highlights* and post as a new "news" content item. [An example](https://galaxyproject.org/news/2018-9-galaxy-release/).
    - [ ] Tweet docs news *highlights* link as @galaxyproject on twitter. [An example](https://twitter.com/galaxyproject/status/973646125633695744).
    - [ ] Post *highlights* with tags `news` and `release` to [Galaxy Help](https://help.galaxyproject.org/). [An example](https://help.galaxyproject.org/t/galaxy-release-19-01/712).
    - [ ] Email *highlights* to [galaxy-dev](http://dev.list.galaxyproject.org/) and [galaxy-announce](http://announce.list.galaxyproject.org/) @lists.galaxyproject.org. [An example](http://dev.list.galaxyproject.org/The-Galaxy-release-16-04-is-out-tp4669419.html)
    - [ ] Adjust http://getgalaxy.org text and links to match current master branch by opening a PR at https://github.com/galaxyproject/galaxy-hub/

- [ ] **Prepare for next release**

    - [ ] Close milestone ``${version}`` and ensure milestone ``${next_version}`` exists.
    - [ ] Create release issue for next version ``make release-issue``.
    - [ ] Schedule committer meeting to discuss re-alignment of priorities.
    - [ ] Close this issue.
"""
)

GROUPPED_TAGS = OrderedDict(
    [
        ("area/visualizations", "viz"),
        ("area/datatypes", "datatypes"),
        ("area/tools", "tools"),
        ("area/workflows", "workflows"),
        ("area/client", "ui"),
        ("area/jobs", "jobs"),
        ("area/admin", "admin"),
    ]
)

# https://api.github.com/repos/galaxyproject/galaxy/pulls?base=dev&state=closed
# https://api.github.com/repos/galaxyproject/galaxy/pulls?base=release_15.07&state=closed
# https://api.github.com/repos/galaxyproject/galaxy/compare/release_15.05...dev


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
    repo = github.get_repo(f"{PROJECT_OWNER}/{PROJECT_NAME}")
    repo.create_issue(
        title=f"Publication of Galaxy Release v {release_name}",
        body=release_issue_contents,
    )
    return release_issue


def do_release(argv):
    release_name = argv[2]
    release_file = _release_file(release_name + ".rst")
    enhancement_targets = "\n\n".join(f".. enhancement_tag_{a}" for a in GROUPPED_TAGS.values())
    bug_targets = "\n\n".join(f".. bug_tag_{a}" for a in GROUPPED_TAGS.values())
    template = TEMPLATE
    template = template.replace(".. enhancement", f"{enhancement_targets}\n\n.. enhancement")
    template = template.replace(".. bug", f"{bug_targets}\n\n.. bug")
    release_info = string.Template(template).safe_substitute(release=release_name)
    _write_file(release_file, release_info, skip_if_exists=True)
    month = int(release_name.split(".")[1])
    month_name = calendar.month_name[month]
    year = release_name.split(".")[0]

    announce_info = ANNOUNCE_TEMPLATE.substitute(month_name=month_name, year=year, release=release_name)
    announce_file = _release_file(release_name + "_announce.rst")
    _write_file(announce_file, announce_info, skip_if_exists=True)

    announce_user_info = ANNOUNCE_USER_TEMPLATE.substitute(month_name=month_name, year=year, release=release_name)
    announce_user_file = _release_file(release_name + "_announce_user.rst")
    _write_file(announce_user_file, announce_user_info, skip_if_exists=True)

    prs_file = _release_file(release_name + "_prs.rst")
    seen_prs = set()
    try:
        with open(prs_file) as fh:
            seen_prs = set(re.findall(r"\.\. _Pull Request (\d*): https", fh.read()))
    except FileNotFoundError:
        pass
    _write_file(prs_file, PRS_TEMPLATE, skip_if_exists=True)

    next_version_params = _next_version_params(release_name)
    next_version = next_version_params["version"]
    next_release_file = _release_file(next_version + "_announce.rst")

    next_announce = NEXT_TEMPLATE.substitute(**next_version_params)
    open(next_release_file, "w").write(next_announce)
    releases_index = _release_file("index.rst")
    releases_index_contents = _read_file(releases_index)
    releases_index_contents = releases_index_contents.replace(
        ".. announcements\n", ".. announcements\n   " + next_version + "_announce\n"
    )
    _write_file(releases_index, releases_index_contents, skip_if_exists=True)

    for pr in _get_prs(release_name):
        # 2015-06-29 18:32:13 2015-04-22 19:11:53 2015-08-12 21:15:45
        as_dict = {
            "title": pr.title.rstrip("."),
            "number": pr.number,
            "head": pr.head,
            "labels": _pr_to_labels(pr),
        }
        main(
            [argv[0], "--release_file", f"{release_name}.rst", "--request", as_dict, "pr" + str(pr.number)],
            seen_prs=seen_prs,
        )


def check_release(argv):
    release_name = argv[2]
    for pr in _get_prs(release_name):
        _text_target(pr, labels=_pr_to_labels(pr))


def check_blocking_prs(argv):
    release_name = argv[2]
    block = 0
    for pr in _get_prs(release_name, state="open"):
        print(f"WARN: Blocking PR| {_pr_to_str(pr)}")
        block = 1

    sys.exit(block)


def check_blocking_issues(argv):
    release_name = argv[2]
    block = 0
    github = _github_client()
    repo = github.get_repo(f"{PROJECT_OWNER}/{PROJECT_NAME}")
    issues = repo.get_issues(state="open")
    for issue in issues:
        # issue can also be a pull request, which could be filtered out with `not issue.pull_request`
        if (
            issue.milestone
            and issue.milestone.title == release_name
            and "Publication of Galaxy Release" not in issue.title
        ):
            print(f"WARN: Blocking issue| {_issue_to_str(issue)}")
            block = 1

    sys.exit(block)


def _pr_to_str(pr):
    if isinstance(pr, str):
        return pr
    return f"PR #{pr.number} ({pr.title}) {pr.html_url}"


def _issue_to_str(pr):
    if isinstance(pr, str):
        return pr
    return f"Issue #{pr.number} ({pr.title}) {pr.html_url}"


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
    repo = github.get_repo(f"{PROJECT_OWNER}/{PROJECT_NAME}")
    pull_requests = repo.get_pulls(state=state)
    reached_old_prs = False

    for pr in pull_requests:
        if reached_old_prs:
            break

        if pr.created_at < datetime.datetime(2020, 5, 1, 0, 0):
            reached_old_prs = True
            pass
        merged_at = pr.merged_at
        milestone = pr.milestone
        proper_state = state != "closed" or merged_at
        if not proper_state or not milestone or milestone.title != release_name:
            continue
        yield pr


def main(argv, seen_prs=None):
    newest_release = None
    seen_prs = seen_prs or set()

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
    user_announce_path = history_path[0 : -len(".rst")] + "_announce_user.rst"
    prs_path = history_path[0 : -len(".rst")] + "_prs.rst"

    history = _read_file(history_path)
    user_announce = _read_file(user_announce_path)
    prs_content = _read_file(prs_path)

    def extend_target(target, line, source=history):
        from_str = f".. {target}\n"
        if target not in source:
            raise Exception(f"Failed to find target [{target}] in source [{source}]")
        return source.replace(from_str, from_str + line + "\n")

    ident = argv[1]

    if requests is None:
        raise Exception("Requests library not found, please pip install requests")
    if len(argv) > 2:
        message = argv[2]
    elif not (ident.startswith("pr") or ident.startswith("issue")):
        api_url = urljoin(PROJECT_API, f"commits/{ident}")
        if req is None:
            req = requests.get(api_url).json()
        commit = req["commit"]
        message = commit["message"]
        message = get_first_sentence(message)
    elif ident.startswith("pr"):
        pull_request = ident[len("pr") :]
        api_url = urljoin(PROJECT_API, f"pulls/{pull_request}")
        if req is None:
            req = requests.get(api_url).json()
        message = req["title"]
    elif ident.startswith("issue"):
        issue = ident[len("issue") :]
        api_url = urljoin(PROJECT_API, f"issues/{issue}")
        if req is None:
            req = requests.get(api_url).json()
        message = req["title"]
    else:
        message = ""

    text_target = "to_doc"
    to_doc = message + " "

    owner = None
    if ident.startswith("pr"):
        pull_request = ident[len("pr") :]
        if pull_request in seen_prs:
            to_doc = ""
        else:
            user = req["head"].user
            owner = user.login
            text = ".. _Pull Request {0}: {1}/pull/{0}".format(pull_request, PROJECT_URL)
            prs_content = extend_target("github_links", text, prs_content)
            to_doc += "\n(thanks to `@{} <https://github.com/{}>`__).".format(
                owner,
                owner,
            )
            to_doc += f"\n`Pull Request {pull_request}`_"
            labels = None
            if req and "labels" in req:
                labels = req["labels"]
            text_target = _text_target(pull_request, labels=labels)
    elif ident.startswith("issue"):
        issue = ident[len("issue") :]
        text = ".. _Issue {0}: {1}/issues/{0}".format(issue, PROJECT_URL)
        prs_content = extend_target("github_links", text, prs_content)
        to_doc += f"`Issue {issue}`_"
    else:
        short_rev = ident[:7]
        text = ".. _{0}: {1}/commit/{0}".format(short_rev, PROJECT_URL)
        prs_content = extend_target("github_links", text, prs_content)
        to_doc += f"{short_rev}_"

    if to_doc:
        to_doc = wrap(to_doc)
        if text_target is not None:
            history = extend_target(text_target, to_doc, history)
        if req and req["labels"]:
            labels = req["labels"]
            if "area/datatypes" in labels:
                user_announce = extend_target("datatypes", to_doc, user_announce)
            if "area/visualizations" in labels:
                user_announce = extend_target("visualizations", to_doc, user_announce)
            if "area/tools" in labels:
                user_announce = extend_target("tools", to_doc, user_announce)
        _write_file(history_path, history)
        _write_file(prs_path, prs_content)
        _write_file(user_announce_path, user_announce)


def _read_file(path):
    with open(path) as f:
        return f.read()


def _write_file(path, contents, skip_if_exists=False):
    if skip_if_exists and os.path.exists(path):
        return
    with open(path, "w") as f:
        f.write(contents)


def _text_target(pull_request, labels=None):
    if isinstance(pull_request, str):
        pr_number = pull_request
    else:
        pr_number = pull_request.number

    if labels is None:
        labels = []
        try:
            github = _github_client()
            labels = github.issues.labels.list_by_issue(int(pr_number), user=PROJECT_OWNER, repo=PROJECT_NAME)
            labels = [label.name.lower() for label in labels]
        except Exception as e:
            print(e)
    is_bug = is_enhancement = is_feature = is_minor = is_major = is_merge = is_small_enhancement = False
    if len(labels) == 0:
        print(f"No labels found for {pr_number}")
        return None
    for label_name in labels:
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
        elif label_name == "procedures":
            # Treat procedures as an implicit enhancement.
            is_enhancement = True

    is_some_kind_of_enhancement = is_enhancement or is_feature or is_small_enhancement

    if not (is_bug or is_some_kind_of_enhancement or is_minor or is_merge):
        print(f"No 'kind/*' or 'minor' or 'merge' or 'procedures' label found for {_pr_to_str(pull_request)}")
        text_target = None

    if is_minor or is_merge:
        return

    if is_some_kind_of_enhancement and is_major:
        text_target = "major_feature"
    elif is_feature:
        text_target = "feature"
    elif is_enhancement:
        for label, tag in GROUPPED_TAGS.items():
            if label in labels:
                text_target = f"enhancement_tag_{tag}"
                break
        else:
            text_target = "enhancement"
    elif is_some_kind_of_enhancement:
        text_target = "small_enhancement"
    elif is_major:
        text_target = "major_bug"
    elif is_bug:
        for label, tag in GROUPPED_TAGS.items():
            if label in labels:
                text_target = f"bug_tag_{tag}"
                break
        else:
            text_target = "bug"
    else:
        print(f"Logic problem, cannot determine section for {_pr_to_str(pull_request)}")
        text_target = None
    if text_target:
        text_target += "\n"
    return text_target


def _pr_to_labels(pr):
    labels = [label.name.lower() for label in pr.labels]
    return labels


def _previous_release(to):
    previous_release = None
    for release in _releases():
        if release == to:
            break

        previous_release = release

    return previous_release


def _releases():
    all_files = sorted(os.listdir(RELEASES_PATH))
    release_note_file_pattern = re.compile(r"\d+\.\d+.rst")
    release_note_files = [f for f in all_files if release_note_file_pattern.match(f)]
    return sorted(f.rstrip(".rst") for f in release_note_files)


def _github_client():
    github_json_path = os.path.expanduser("~/.github.json")
    with open(github_json_path) as fh:
        github_json_dict = json.load(fh)
    return Github(**github_json_dict)


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
    message = re.sub(r"^\s*\[.*\]\s*", r"", message)
    # Link issues and pull requests...
    issue_url = f"https://github.com/{PROJECT_OWNER}/{PROJECT_NAME}/issues"
    message = re.sub(r"#(\d+)", rf"`#\1 <{issue_url}/\1>`__", message)
    return message


def wrap(message):
    message = process_sentence(message)
    wrapper = textwrap.TextWrapper(initial_indent="* ")
    wrapper.subsequent_indent = "  "
    wrapper.width = 160
    message_lines = message.splitlines()
    first_lines = "\n".join(wrapper.wrap(message_lines[0]))
    wrapper.initial_indent = "  "
    rest_lines = "\n".join("\n".join(wrapper.wrap(m)) for m in message_lines[1:])
    return first_lines + ("\n" + rest_lines if rest_lines else "")


def next_weekday(d, weekday):
    """Return the next week day (0 for Monday, 6 for Sunday) starting from ``d``."""
    days_ahead = weekday - d.weekday()
    if days_ahead <= 0:  # Target day already happened this week
        days_ahead += 7
    return d + datetime.timedelta(days_ahead)


if __name__ == "__main__":
    main(sys.argv)
