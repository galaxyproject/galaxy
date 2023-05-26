import datetime
import os
import pathlib
import re
import subprocess
from dataclasses import (
    dataclass,
    field,
)
from typing import (
    Any,
    List,
    Optional,
    Set,
)

import click
from bootstrap_history import (
    _pr_to_labels,
    _text_target,
    strip_release,
)
from click.core import (
    Context,
    Parameter,
)
from docutils import (
    frontend,
    utils,
)
from docutils.parsers.rst import Parser
from github import (
    Github,
    PullRequest,
)
from packaging.version import Version

g = Github(os.environ.get("GITHUB_AUTH"))
PROJECT_OWNER = "galaxyproject"
PROJECT_NAME = "galaxy"
REPO = f"{PROJECT_OWNER}/{PROJECT_NAME}"

HISTORY_TEMPLATE = """History
-------

.. to_doc

"""
RELEASE_BRANCH_REGEX = re.compile(r"^release_(\d{2}\.\d{1,2})$")


class ClickVersion(click.ParamType):
    name = "pep440 version"

    def convert(self, value: Any, param: Optional[Parameter], ctx: Optional[Context]) -> Version:
        try:
            return Version(value)
        except Exception as e:
            self.fail(f"{value!r} is not a valid PEP440 version number: {str(e)}", param, ctx)


@dataclass
class ChangelogItem:
    version: Version
    changes: List[str]
    date: Optional[str] = None

    @property
    def is_empty_devrelease(self):
        return self.version.is_devrelease and not self.changes

    def __str__(self) -> str:
        change_lines = "\n".join(self.changes)
        if self.date:
            version_line = f"{self.version} ({self.date})"
        else:
            version_line = str(self.version)
        return f"""{'-' * len(version_line)}
{version_line}
{'-' * len(version_line)}

{change_lines}
"""


@dataclass
class Package:
    path: pathlib.Path
    current_version: str
    next_version: Optional[str] = None
    commits: Optional[Set[str]] = None
    prs: Optional[Set[PullRequest.PullRequest]] = None
    modified_paths: List[pathlib.Path] = field(default_factory=list)
    package_history: List[ChangelogItem] = field(default_factory=list)

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def setup_cfg(self) -> pathlib.Path:
        return self.path / "setup.cfg"

    @property
    def history_rst(self) -> pathlib.Path:
        return self.path / "HISTORY.rst"

    @property
    def changelog(self) -> str:
        changelog_string = "\n".join(str(h) for h in self.package_history)
        return f"{HISTORY_TEMPLATE}{changelog_string}"

    def write_history(self):
        self.history_rst.write_text(self.changelog)
        self.modified_paths.append(self.history_rst)

    def __repr__(self) -> str:
        pretty_string = f"[Package: {self.name}, Current Version: {self.current_version}"
        if self.next_version:
            pretty_string = f"{pretty_string[:-1]}, Next Version: {self.next_version}"
        return pretty_string


def get_sorted_package_paths(galaxy_root: pathlib.Path) -> List[pathlib.Path]:
    root_package_path = galaxy_root.joinpath("packages")
    sorted_packages = root_package_path.joinpath("packages_by_dep_dag.txt").read_text().splitlines()
    # Check that all packages are listed in packages_by_dep_dag.txt ?
    return [root_package_path.joinpath(package) for package in sorted_packages]


def read_package(package_path: pathlib.Path) -> Package:
    setup_cfg = package_path / "setup.cfg"
    package = None
    with setup_cfg.open() as content:
        for line in content:
            if line.startswith("version = "):
                version = line.strip().split("version = ")[-1]
                package = Package(path=package_path, current_version=version)
                break
    if not package:
        raise ValueError(f"{setup_cfg} does not contain version line")
    package.package_history = parse_changelog(package)
    return package


def parse_changelog(package: Package) -> List[ChangelogItem]:
    settings = frontend.get_default_settings(Parser)
    document = utils.new_document(str(package.history_rst), settings)
    Parser().parse(package.history_rst.read_text(), document)
    changelog_items: List[ChangelogItem] = []
    root_section = document[0]
    assert root_section.tagname == "section"
    for release in root_section.children:
        # ignore title and comment
        if release.tagname == "section":
            assert release[0].tagname == "title"
            release_version = release[0].astext()
            current_date = None
            if " (" in release_version:
                version_str, current_date = release_version.split(" (")
                current_date = current_date.split(")")[0]
            else:
                # this should be a dev-release without changelog items
                # we will just omit this later
                version_str = release_version
            current_version = Version(version_str)
            changes = []
            for changelog_item in release[1:]:
                # could be bullet list or a nested section with bugfix, docs, etc
                if changelog_item.tagname == "bullet_list":
                    for child in changelog_item.children:
                        changes.append(f"* {child.rawsource.strip()}")
                elif changelog_item.tagname == "paragraph":
                    changes = changelog_item.rawsource.splitlines()
                elif changelog_item.tagname == "section":
                    kind = changelog_item[0].astext()
                    section_delimiter = "=" * len(kind)
                    changes.append(f"\n{section_delimiter}\n{kind}\n{section_delimiter}\n")
                    for section_changelog_item in changelog_item[1:]:
                        for child in section_changelog_item:
                            changes.append(f"* {child.rawsource.strip()}")
            changelog_items.append(ChangelogItem(version=current_version, date=current_date, changes=changes))

    # Filter out dev release versions without changelog, we're going to add these back after committing the release version
    clean_changelog_items: List[ChangelogItem] = []
    for item in changelog_items:
        if not item.is_empty_devrelease:
            if item.date is None:
                raise Exception(
                    f"Error in '{package.history_rst}'. Changelog entry for version '{item.version}' has no date but contains changes. You have to fix this manually."
                )
            clean_changelog_items.append(item)
    return sorted(clean_changelog_items, key=lambda item: datetime.datetime.fromisoformat(item.date), reverse=True)


def bump_package_version(package: Package, new_version: Version):
    new_content = []
    content = package.setup_cfg.read_text().splitlines()
    for line in content:
        if line.startswith("version = "):
            line = f"version = {new_version}"
        new_content.append(line)
    package.setup_cfg.write_text("\n".join(new_content))
    package.modified_paths.append(package.setup_cfg)


def get_commits_since_last_version(package: Package, last_version_tag: str):
    click.echo(f"finding commits to package {package.name} made since {last_version_tag}")
    package_source_paths = []
    commits = set()
    for code_dir in ["galaxy", "tests", "galaxy_test"]:
        package_code_path = package.path / code_dir
        if package_code_path.exists():
            # get all symlinks pointing to a directory
            for item in package_code_path.iterdir():
                # Check if the item is a symlink and if its target points to a directory
                if item.is_symlink() and item.resolve().is_dir():
                    package_source_paths.append(item.resolve())
    for package_source_path in package_source_paths:
        result = subprocess.run(
            [
                "git",
                "log",
                "--oneline",
                "--no-merges",
                "--pretty=format:%h",
                f"{last_version_tag}..HEAD",
                package_source_path,
            ],
            cwd=package.path,
            capture_output=True,
            text=True,
        )
        result.check_returncode()
        for line in result.stdout.splitlines():
            if line:
                commits.add(line)
    package.commits = commits


def commits_to_prs(packages: List[Package]):
    commits = set.union(*(p.commits for p in packages))
    pr_cache = {}
    commit_to_pr = {}
    for commit in commits:
        # Get the list of pull requests associated with the commit
        commit_obj = g.get_repo(REPO).get_commit(commit)
        prs = commit_obj.get_pulls()
        if not prs:
            raise Exception(f"commit {commit} has no associated PRs")
        for pr in prs:
            if pr.number not in pr_cache:
                pr_cache[pr.number] = pr
            commit_to_pr[commit] = pr_cache[pr.number]
    for package in packages:
        package.prs = set(commit_to_pr[commit] for commit in package.commits)


def update_package_history(package: Package, new_version: Version):
    sorted_and_formatted_changes = []
    changes = {"Bug fixes": [], "Enhancements": [], "Other changes": []}
    if not package.prs:
        # Skip publishing packages if no change ?
        sorted_and_formatted_changes.append("No recorded changes since last release")
    else:
        for pr in sorted(package.prs, key=lambda pr: pr.number):
            category = "Other changes"
            text_target = _text_target(pr, labels=_pr_to_labels(pr), skip_merge=False)
            if text_target:
                if "bug" in text_target:
                    category = "Bug fixes"
                if "enhancement" in text_target or "feature" in text_target:
                    category = "Enhancements"
            changes[category].append(
                f"* {strip_release(pr.title)} by `@{pr.user.login} <https://github.com/{pr.user.login}>`_ in `#{pr.number} <{pr.html_url}>`_"
            )

    for kind, entries in changes.items():
        if entries:
            section_delimiter = "=" * len(kind)
            sorted_and_formatted_changes.append(f"\n{section_delimiter}\n{kind}\n{section_delimiter}\n")
        sorted_and_formatted_changes.extend(entries)

    now = datetime.datetime.now().strftime("%Y-%m-%d")
    package.package_history.insert(
        0, ChangelogItem(version=new_version, changes=sorted_and_formatted_changes, date=now)
    )
    package.write_history()


def build_package(package: Package):
    click.echo(f"Running make clean for package {package.name}")
    subprocess.run(["make", "clean"], cwd=package.path)
    click.echo(f"running make dist for package {package.name}")
    subprocess.run(["make", "dist"], cwd=package.path)
    click.echo(f"running make lint-dist for package {package.name}")
    subprocess.run(["make", "lint-dist"], cwd=package.path)


def upload_package(package: Package, repository: str = "testpypi"):
    click.echo(f"uploading package {package.name} to {repository}")
    subprocess.run(["twine", "upload", "--repository", repository], cwd=package.path).check_returncode()


def get_root_version(galaxy_root: pathlib.Path) -> str:
    version_py = galaxy_root / "lib" / "galaxy" / "version.py"
    version_py_contents = version_py.read_text().splitlines()
    assert len(version_py_contents) == 3
    major_version = version_py_contents[0].split('"')[1]
    minor_version = version_py_contents[1].split('"')[1]
    return f"{major_version}.{minor_version}"


def set_root_version(galaxy_root: pathlib.Path, new_version: Version) -> pathlib.Path:
    major_galaxy_release_string = f"{new_version.major}.{new_version.minor}"
    minor_galaxy_release_string = str(new_version).replace(f"{major_galaxy_release_string}.", "")
    VERSION_PY_TEMPLATE = f"""VERSION_MAJOR = "{major_galaxy_release_string}"
VERSION_MINOR = "{minor_galaxy_release_string}"
VERSION = VERSION_MAJOR + (f".{{VERSION_MINOR}}" if VERSION_MINOR else "")
"""
    version_py = galaxy_root / "lib" / "galaxy" / "version.py"
    version_py.write_text(VERSION_PY_TEMPLATE)
    return version_py


def is_git_clean(galaxy_root: pathlib.Path):
    click.echo(f"Making sure galaxy clone at '{galaxy_root}' is clean")
    command = ["git", "diff-index", "--quiet", "HEAD"]
    result = subprocess.run(command, capture_output=True, text=True, cwd=galaxy_root)
    if result.returncode == 0:
        return True
    else:
        msg = f"Command '{' '.join(command)}' failed with exit code {result.returncode}"
        if result.returncode != 1 and result.stderr:
            msg = f"{msg}, stderr: {result.stderr}"
        click.echo(msg)
        return False


def get_current_branch(galaxy_root):
    current_branch_cmd = ["git", "rev-parse", "--abbrev-ref", "HEAD"]
    result = subprocess.run(current_branch_cmd, cwd=galaxy_root, capture_output=True, text=True)
    result.check_returncode()
    return result.stdout.strip()


def get_branches(galaxy_root: pathlib.Path, new_version: Version, current_branch: str):
    """
    Tries to get release and dev branches that we need to merge forward to.
    """
    major_minor_new_version = Version(f"{new_version.major}.{new_version.minor}")
    cmd = ["git", "branch", "--format=%(refname:short)"]
    result = subprocess.run(cmd, cwd=galaxy_root, capture_output=True, text=True)
    result.check_returncode()
    release_branches = []
    branches = result.stdout.splitlines()
    for branch in branches:
        match = RELEASE_BRANCH_REGEX.match(branch)
        if match:
            version = match.group(1)
            branch_version = Version(version)
            if branch_version > major_minor_new_version:
                release_branches.append(branch)
    if current_branch != "dev":
        release_branches.append("dev")
    return release_branches


def merge_and_resolve_branches(galaxy_root: pathlib.Path, base_branch: str, new_branch: str, packages: List[Package]):
    checkout_cmd = ["git", "checkout", new_branch]
    subprocess.run(checkout_cmd, cwd=galaxy_root).check_returncode()

    package_paths = {p.path: p for p in packages}
    packages_to_rewrite: List[Package] = []
    for package_path in get_sorted_package_paths(galaxy_root):
        if package_path not in package_paths:
            continue
        package = read_package(package_path)
        packages_to_rewrite.append(package)

    merge_cmd = ["git", "merge", base_branch]
    result = subprocess.run(merge_cmd, cwd=galaxy_root, capture_output=True, text=True)
    merge_conflict = result.returncode != 0  # merge conflict expected
    # restore base galaxy version
    subprocess.run(["git", "checkout", new_branch, str(galaxy_root / "lib" / "galaxy" / "version.py")])
    # we rewrite the packages changelog
    for new_package in packages_to_rewrite:
        previous_package = package_paths[new_package.path]
        combined_history = previous_package.package_history + new_package.package_history
        new_history: List[ChangelogItem] = []
        last_changelog_item: Optional[ChangelogItem] = None
        for changelog_item in sorted(combined_history, key=lambda item: item.version, reverse=True):
            if last_changelog_item and changelog_item.version == last_changelog_item.version:
                assert (
                    last_changelog_item.changes == changelog_item.changes
                ), f"Changelog differs for version {changelog_item.version} of package {new_package.name}, you have to fix this manually.\nOffending lines are {last_changelog_item.changes} and {changelog_item.changes}"
                continue
            if not changelog_item.date and not changelog_item.changes:
                # dev0 version, we'll inject that later
                continue
            new_history.append(changelog_item)
            last_changelog_item = changelog_item
        # we change the original package in place so this continues to work if we merge forward across multiple branches
        previous_package.package_history = sorted(
            new_history, key=lambda item: datetime.datetime.fromisoformat(item.date), reverse=True
        )
        dev_version = Version(get_root_version(galaxy_root))
        previous_package.package_history.insert(0, ChangelogItem(version=dev_version, changes=[], date=None))
        previous_package.write_history()
        subprocess.run(["git", "add", str(previous_package.history_rst)])
        # restore setup.cfg
        subprocess.run(["git", "checkout", new_branch, str(previous_package.setup_cfg)]).check_returncode()
    # Commit changes
    if merge_conflict:
        subprocess.run(["git", "commit", "--no-edit"]).check_returncode()
    else:
        subprocess.run(["git", "commit", "--amend", "--no-edit"]).check_returncode()


def get_next_devN_version(galaxy_root) -> Version:
    root_version = Version(get_root_version(galaxy_root))
    if root_version.is_devrelease:
        minor_version = root_version.minor
        dev_version = root_version.dev + 1
    else:
        minor_version = root_version.minor + 1
        dev_version = 0
    return Version(f"{root_version.major}.{minor_version}.dev{dev_version}")


def is_merge_required(base_branch: str, new_branch: str, galaxy_root: pathlib.Path):
    subprocess.run(["git", "checkout", new_branch], cwd=galaxy_root).check_returncode()
    process = subprocess.run(
        ["git", "merge", "--no-commit", "--no-ff", base_branch], cwd=galaxy_root, capture_output=False
    )
    subprocess.run(["git", "merge", "--abort"], cwd=galaxy_root)
    if process.returncode == 0:
        return False
    return True


@click.group(help="Subcommands of this script can create new releases and build and upload package artifacts")
def cli():
    pass


def group_options(*options):
    def wrapper(function):
        for option in reversed(options):
            function = option(function)
        return function

    return wrapper


galaxy_root_option = click.option(
    "--galaxy-root", type=click.Path(exists=True, file_okay=False, resolve_path=True, path_type=pathlib.Path)
)
package_repository_option = click.option(
    "--package_repository",
    type=str,
    default="testpypi",
    help="Select target registry to upload packages to. Set to 'pypi' to upload to main pypi repository.",
)
packages_option = click.option(
    "--packages", "package_subset", multiple=True, type=str, default=None, help="Restrict build to specified packages"
)
no_confirm_option = click.option("--no-confirm", type=bool, is_flag=True, default=False)


@group_options(galaxy_root_option, package_repository_option, packages_option, no_confirm_option)
@cli.command("build-and-upload", help="Build and upload packages")
def build_and_upload(
    galaxy_root: pathlib.Path,
    package_subset: List[str],
    package_repository: str,
    no_confirm: bool,
):
    packages: List[Package] = []
    for package_path in get_sorted_package_paths(galaxy_root):
        if package_subset and package_path.name not in package_subset:
            continue
        package = read_package(package_path)
        packages.append(package)
    for package in packages:
        click.echo(f"Building package {package}")
        build_package(package)
    if no_confirm or click.confirm(f"Upload packages to {package_repository} ?"):
        for package in packages:
            click.echo(f"Uploading package {package}")
            upload_package(package, repository=package_repository)


@cli.command("create-release", help="Create a new point release")
@group_options(galaxy_root_option)
@click.option("--new-version", type=ClickVersion(), help="Specify new release version. Must be valid PEP 440 version")
@click.option(
    "--last-commit",
    type=str,
    help="Specify commit or tag that was used for the last package release. This is used to find the changelog for packages.",
)
@click.option("--build-packages", type=bool, is_flag=True, default=True)
@click.option("--upload-packages", type=bool, is_flag=True, default=False)
@group_options(package_repository_option, packages_option, no_confirm_option)
def create_point_release(
    galaxy_root: pathlib.Path,
    new_version: Version,
    build_packages: bool,
    last_commit: Optional[str],
    package_subset: List[str],
    upload_packages: bool,
    package_repository: str,
    no_confirm: bool,
):
    # Update version.py
    if not is_git_clean(galaxy_root):
        click.confirm(
            "Your galaxy clone has untracked or staged changes, are you sure you want to continue ?", abort=True
        )
    root_version = get_root_version(galaxy_root)
    click.echo(f"Current Galaxy version is {root_version}, will create new version {new_version}")
    if not no_confirm:
        click.confirm("Does this look correct?", abort=True)
    base_branch = current_branch = get_current_branch(galaxy_root)
    newer_branches = get_branches(galaxy_root, new_version, base_branch)
    click.echo("Making sure that merging forward will result in clean merges")
    merge_required = False
    for new_branch in newer_branches:
        merge_required = is_merge_required(base_branch=current_branch, new_branch=new_branch, galaxy_root=galaxy_root)
        if merge_required:
            msg = f"Merge conflicts occurred while attempting to merge branch {current_branch} into {new_branch}. You should resolve conflicts and try again."
            if no_confirm:
                raise Exception(msg)
            click.echo(msg)
            if click.confirm("Continue anyway ?", abort=True):
                break
    subprocess.run(["git", "checkout", base_branch], cwd=galaxy_root)
    modified_paths = [set_root_version(galaxy_root, new_version)]
    # read packages and find prs that affect a package
    packages: List[Package] = []
    for package_path in get_sorted_package_paths(galaxy_root):
        if package_subset and package_path.name not in package_subset:
            continue
        package = read_package(package_path)
        packages.append(package)
        get_commits_since_last_version(package, last_commit)
    commits_to_prs(packages)
    # update package versions and changelog files
    for package in packages:
        if new_version:
            bump_package_version(package, str(new_version))
            update_package_history(package, new_version)
        if build_packages:
            build_package(package)
        modified_paths.extend(package.modified_paths)
    # show changed paths, optionally run git diff
    changed_paths = [str(p) for p in modified_paths]
    pretty_paths = "\n".join(changed_paths)
    click.echo(f"The following paths have been modified: \n{pretty_paths}")
    if not no_confirm and click.confirm("show diff ?"):
        cmd = ["git", "diff"]
        cmd.extend([str(p) for p in modified_paths])
        subprocess.run(cmd, cwd=galaxy_root)
    if (
        build_packages
        and upload_packages
        and (no_confirm or click.confirm(f"Upload packages to {package_repository} ?"))
    ):
        for package in packages:
            upload_package(package, repository=package_repository)
    # stage changes, commit and tag
    if not no_confirm:
        click.confirm("Stage and commit changes ?", abort=True)
    cmd = ["git", "add"]
    cmd.extend(changed_paths)
    subprocess.run(cmd, cwd=galaxy_root)
    subprocess.run(["git", "commit", "-m" f"Create version {new_version}"])
    if not no_confirm:
        click.confirm(f"Create git tag 'v{new_version}' ?", abort=True)
    subprocess.run(["git", "tag", f"v{new_version}"])
    dev_version = get_next_devN_version(galaxy_root)
    version_py = set_root_version(galaxy_root, dev_version)
    modified_paths = [version_py]
    for package in packages:
        bump_package_version(package, dev_version)
        package.package_history.insert(0, ChangelogItem(version=dev_version, changes=[], date=None))
        package.write_history()
        modified_paths.extend(package.modified_paths)
    cmd = ["git", "add"]
    cmd.extend([str(p) for p in modified_paths])
    subprocess.run(cmd)
    subprocess.run(["git", "commit", "-m", f"Start work on {dev_version}"])
    # merge changes into newer branches
    # special care needs to be taken for changelog files
    if not no_confirm and newer_branches:
        click.confirm(f"Merge branch '{base_branch}' into {', '.join(newer_branches)} ?", abort=True)
    for new_branch in newer_branches:
        click.echo(f"Merging {base_branch} into {new_branch}")
        merge_and_resolve_branches(galaxy_root, base_branch, new_branch, packages)


if __name__ == "__main__":
    cli()
