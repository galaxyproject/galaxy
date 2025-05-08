import json
import logging
import os
import socket
import string
from typing import (
    List,
    TYPE_CHECKING,
)

from sqlalchemy import (
    false,
    func,
    select,
    true,
)
from sqlalchemy.orm import scoped_session

from galaxy import util
from galaxy.tool_shed.util.shed_util_common import get_user
from galaxy.util import (
    checkers,
    unicodify,
)
from galaxy.web import url_for
from tool_shed.util import (
    basic_util,
    common_util,
    hg_util,
    repository_util,
)
from tool_shed.webapp import model

if TYPE_CHECKING:
    from tool_shed.structured_app import ToolShedApp
    from tool_shed.webapp.model import Repository

log = logging.getLogger(__name__)

MAX_CONTENT_SIZE = 1048576
DATATYPES_CONFIG_FILENAME = "datatypes_conf.xml"
REPOSITORY_DATA_MANAGER_CONFIG_FILENAME = "data_manager_conf.xml"

new_repo_email_alert_template = """
Sharable link:         ${sharable_link}
Repository name:       ${repository_name}
Revision:              ${revision}
Change description:
${description}

Uploaded by:           ${username}
Date content uploaded: ${display_date}

${content_alert_str}

-----------------------------------------------------------------------------
This change alert was sent from the Galaxy tool shed hosted on the server
"${host}"
-----------------------------------------------------------------------------
You received this alert because you registered to receive email when
new repositories were created in the Galaxy tool shed named "${host}".
-----------------------------------------------------------------------------
"""

email_alert_template = """
Sharable link:         ${sharable_link}
Repository name:       ${repository_name}
Revision:              ${revision}
Change description:
${description}

Changed by:     ${username}
Date of change: ${display_date}

${content_alert_str}

-----------------------------------------------------------------------------
This change alert was sent from the Galaxy tool shed hosted on the server
"${host}"
-----------------------------------------------------------------------------
You received this alert because you registered to receive email whenever
changes were made to the repository named "${repository_name}".
-----------------------------------------------------------------------------
"""


def count_repositories_in_category(app: "ToolShedApp", category_id: str) -> int:
    stmt = (
        select(func.count())
        .select_from(model.RepositoryCategoryAssociation)
        .where(model.RepositoryCategoryAssociation.category_id == app.security.decode_id(category_id))
    )
    count = app.model.session.scalar(stmt)
    assert count is not None
    return count


def get_categories(app: "ToolShedApp"):
    """Get all categories from the database."""
    sa_session = app.model.session
    stmt = select(model.Category).where(model.Category.deleted == false()).order_by(model.Category.name)
    return sa_session.scalars(stmt).all()


def get_category(app: "ToolShedApp", id: str):
    """Get a category from the database."""
    sa_session = app.model.session
    return sa_session.get(model.Category, app.security.decode_id(id))


def get_category_by_name(app: "ToolShedApp", name: str):
    """Get a category from the database via name."""
    sa_session = app.model.session
    stmt = select(model.Category).filter_by(name=name).limit(1)
    return sa_session.scalars(stmt).first()


def get_repository_file_contents(app: "ToolShedApp", file_path: str, repository_id: str, is_admin: bool = False) -> str:
    """Return the display-safe contents of a repository file for display in a browser."""
    safe_str = ""
    if not _is_path_browsable(app, file_path, repository_id, is_admin):
        log.warning("Request tries to access a file outside of the repository location. File path: %s", file_path)
        return "Invalid file path"
    # Symlink targets are checked by _is_path_browsable
    if os.path.islink(file_path):
        safe_str = f"link to: {basic_util.to_html_string(os.readlink(file_path))}"
        return safe_str
    elif checkers.is_gzip(file_path):
        return "<br/>gzip compressed file<br/>"
    elif checkers.is_bz2(file_path):
        return "<br/>bz2 compressed file<br/>"
    elif checkers.is_zip(file_path):
        return "<br/>zip compressed file<br/>"
    elif checkers.check_binary(file_path):
        return "<br/>Binary file<br/>"
    else:
        with open(file_path) as fh:
            for line in fh:
                safe_str = f"{safe_str}{basic_util.to_html_string(line)}"
                # Stop reading after string is larger than MAX_CONTENT_SIZE.
                if len(safe_str) > MAX_CONTENT_SIZE:
                    large_str = f"<br/>File contents truncated because file size is larger than maximum viewing size of {util.nice_size(MAX_CONTENT_SIZE)}<br/>"
                    safe_str = f"{safe_str}{large_str}"
                    break

        if len(safe_str) > basic_util.MAX_DISPLAY_SIZE:
            # Eliminate the middle of the file to display a file no larger than basic_util.MAX_DISPLAY_SIZE.
            # This may not be ideal if the file is larger than MAX_CONTENT_SIZE.
            join_by_str = f"<br/><br/>...some text eliminated here because file size is larger than maximum viewing size of {util.nice_size(basic_util.MAX_DISPLAY_SIZE)}...<br/><br/>"
            safe_str = util.shrink_string_by_size(
                safe_str,
                basic_util.MAX_DISPLAY_SIZE,
                join_by=join_by_str,
                left_larger=True,
                beginning_on_size_error=True,
            )
        return safe_str


def get_repository_files(folder_path):
    """Return the file hierarchy of a tool shed repository."""
    contents = []
    for item in os.listdir(folder_path):
        # Skip .hg directories
        if item.startswith(".hg"):
            continue
        contents.append(item)
    if contents:
        contents.sort()
    return contents


def get_repository_from_refresh_on_change(app: "ToolShedApp", **kwd):
    # The changeset_revision_select_field in several grids performs a refresh_on_change which sends in request parameters like
    # changeset_revison_1, changeset_revision_2, etc.  One of the many select fields on the grid performed the refresh_on_change,
    # so we loop through all of the received values to see which value is not the repository tip.  If we find it, we know the
    # refresh_on_change occurred and we have the necessary repository id and change set revision to pass on.
    repository_id = None
    v = None
    for k, v in kwd.items():
        changeset_revision_str = "changeset_revision_"
        if k.startswith(changeset_revision_str):
            repository_id = app.security.encode_id(int(k.lstrip(changeset_revision_str)))
            repository = repository_util.get_repository_in_tool_shed(app, repository_id)
            if repository.tip() != v:
                return v, repository
    # This should never be reached - raise an exception?
    return v, None


def handle_email_alerts(
    app: "ToolShedApp",
    host: str,
    repository: "Repository",
    content_alert_str: str = "",
    new_repo_alert: bool = False,
    admin_only: bool = False,
) -> None:
    """
    There are 2 complementary features that enable a tool shed user to receive email notification:

    1. Within User Preferences, they can elect to receive email when the first (or first valid)
       change set is produced for a new repository.
    2. When viewing or managing a repository, they can check the box labeled "Receive email alerts"
       which caused them to receive email alerts when updates to the repository occur.  This same feature
       is available on a per-repository basis on the repository grid within the tool shed.

    There are currently 4 scenarios for sending email notification when a change is made to a repository:

    1. An admin user elects to receive email when the first change set is produced for a new repository
       from User Preferences.  The change set does not have to include any valid content.  This allows for
       the capture of inappropriate content being uploaded to new repositories.
    2. A regular user elects to receive email when the first valid change set is produced for a new repository
       from User Preferences.  This differs from 1 above in that the user will not receive email until a
       change set that includes valid content is produced.
    3. An admin user checks the "Receive email alerts" check box on the manage repository page.  Since the
       user is an admin user, the email will include information about both HTML and image content that was
       included in the change set.
    4. A regular user checks the "Receive email alerts" check box on the manage repository page.  Since the
       user is not an admin user, the email will not include any information about both HTML and image content
       that was included in the change set.

    """
    sa_session = app.model.session
    repo = repository.hg_repo
    sharable_link = repository_util.generate_sharable_link_for_repository_in_tool_shed(
        repository, changeset_revision=None
    )
    smtp_server = app.config.smtp_server
    if smtp_server and (new_repo_alert or repository.email_alerts):
        # Send email alert to users that want them.
        if app.config.email_from is not None:
            email_from = app.config.email_from
        elif host.split(":")[0] in ["localhost", "127.0.0.1", "0.0.0.0"]:
            email_from = f"galaxy-no-reply@{socket.getfqdn()}"
        else:
            email_from = f"galaxy-no-reply@{host.split(':')[0]}"
        ctx = repo[repo.changelog.tip()]
        username = unicodify(ctx.user())
        try:
            username = username.split()[0]
        except Exception:
            pass
        # We'll use 2 template bodies because we only want to send content
        # alerts to tool shed admin users.
        if new_repo_alert:
            template = new_repo_email_alert_template
        else:
            template = email_alert_template
        display_date = hg_util.get_readable_ctx_date(ctx)
        description = unicodify(ctx.description())
        revision = f"{ctx.rev()}:{ctx}"
        admin_body = string.Template(template).safe_substitute(
            host=host,
            sharable_link=sharable_link,
            repository_name=repository.name,
            revision=revision,
            display_date=display_date,
            description=description,
            username=username,
            content_alert_str=content_alert_str,
        )
        body = string.Template(template).safe_substitute(
            host=host,
            sharable_link=sharable_link,
            repository_name=repository.name,
            revision=revision,
            display_date=display_date,
            description=description,
            username=username,
            content_alert_str="",
        )
        admin_users = app.config.get("admin_users", "").split(",")
        frm = email_from
        if new_repo_alert:
            subject = f"Galaxy tool shed alert for new repository named {str(repository.name)}"
            subject = subject[:80]
            email_alerts = []
            for user in get_users_with_repo_alert(sa_session, model.User):
                if admin_only:
                    if user.email in admin_users:
                        email_alerts.append(user.email)
                else:
                    email_alerts.append(user.email)
        else:
            subject = f"Galaxy tool shed update alert for repository named {str(repository.name)}"
            email_alerts = json.loads(repository.email_alerts)  # type:ignore[arg-type]
        for email in email_alerts:
            to = email.strip()
            # Send it
            try:
                if to in admin_users:
                    util.send_mail(frm, to, subject, admin_body, app.config)
                else:
                    util.send_mail(frm, to, subject, body, app.config)
            except Exception:
                log.exception("An error occurred sending a tool shed repository update alert by email.")


def _is_path_browsable(app: "ToolShedApp", path: str, repository_id: str, is_admin: bool = False) -> bool:
    """
    Detects whether the given path is browsable i.e. is within the
    allowed repository folders. Admins can additionaly browse folders
    with tool dependencies.
    """
    if is_admin and is_path_within_dependency_dir(app, path):
        return True
    return is_path_within_repo(app, path, repository_id)


def is_path_within_dependency_dir(app: "ToolShedApp", path: str) -> bool:
    """
    Detect whether the given path is within the tool_dependency_dir folder on the disk.
    (Specified by the config option). Use to filter malicious symlinks targeting outside paths.
    """
    allowed = False
    resolved_path = os.path.realpath(path)
    if tool_dependency_dir := app.config.get("tool_dependency_dir", None):
        dependency_path = os.path.abspath(tool_dependency_dir)
        allowed = os.path.commonprefix([dependency_path, resolved_path]) == dependency_path
    return allowed


def is_path_within_repo(app: "ToolShedApp", path: str, repository_id: str) -> bool:
    """
    Detect whether the given path is within the repository folder on the disk.
    Use to filter malicious symlinks targeting outside paths.
    """
    repo_path = os.path.abspath(repository_util.get_repository_by_id(app, repository_id).repo_path(app))
    resolved_path = os.path.realpath(path)
    return os.path.commonprefix([repo_path, resolved_path]) == repo_path


def open_repository_files_folder(
    app: "ToolShedApp", folder_path: str, repository_id: str, is_admin: bool = False
) -> List:
    """
    Return a list of dictionaries, each of which contains information for a file or directory contained
    within a directory in a repository file hierarchy.
    """
    if not _is_path_browsable(app, folder_path, repository_id, is_admin):
        log.warning("Request tries to access a folder outside of the allowed locations. Folder path: %s", folder_path)
        return []
    try:
        files_list = get_repository_files(folder_path)
    except OSError as e:
        if str(e).find("No such file or directory") >= 0:
            # We have a repository with no contents.
            return []
    folder_contents = []
    for filename in files_list:
        is_folder = False
        full_path = os.path.join(folder_path, filename)
        is_link = os.path.islink(full_path)
        path_is_browsable = _is_path_browsable(app, full_path, repository_id)
        if is_link and not path_is_browsable:
            log.warning(
                f"Valid folder contains a symlink outside of the repository location. Link found in: {str(full_path)}"
            )
        if filename:
            if os.path.isdir(full_path) and path_is_browsable:
                # Append a '/' character so that our jquery dynatree will function properly.
                filename = f"{filename}/"
                full_path = f"{full_path}/"
                is_folder = True
            node = {
                "title": filename,
                "isFolder": is_folder,
                "isLazy": is_folder,
                "tooltip": full_path,
                "key": full_path,
            }
            folder_contents.append(node)
    return folder_contents


def tool_shed_is_this_tool_shed(toolshed_base_url, trans=None):
    """Determine if a tool shed is the current tool shed."""
    cleaned_toolshed_base_url = common_util.remove_protocol_from_tool_shed_url(toolshed_base_url)
    hostname = trans.repositories_hostname if trans else str(url_for("/", qualified=True))
    cleaned_tool_shed = common_util.remove_protocol_from_tool_shed_url(hostname)
    return cleaned_toolshed_base_url == cleaned_tool_shed


def get_users_with_repo_alert(session: scoped_session, user_model):
    stmt = select(user_model).where(user_model.deleted == false()).where(user_model.new_repo_alert == true())
    return session.scalars(stmt)


__all__ = (
    "count_repositories_in_category",
    "get_categories",
    "get_category",
    "get_category_by_name",
    "get_repository_file_contents",
    "get_user",
    "handle_email_alerts",
    "is_path_within_dependency_dir",
    "is_path_within_repo",
    "open_repository_files_folder",
    "tool_shed_is_this_tool_shed",
)
