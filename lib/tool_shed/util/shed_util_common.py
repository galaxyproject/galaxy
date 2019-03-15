import json
import logging
import os
import re
import socket
import string

import sqlalchemy.orm.exc
from sqlalchemy import and_, false, true

import galaxy.tools.deps.requirements
from galaxy import util
from galaxy.util import checkers
from galaxy.web import url_for
from tool_shed.util import (
    basic_util,
    common_util,
    hg_util,
    repository_util
)

log = logging.getLogger(__name__)

MAX_CONTENT_SIZE = 1048576
DATATYPES_CONFIG_FILENAME = 'datatypes_conf.xml'
REPOSITORY_DATA_MANAGER_CONFIG_FILENAME = 'data_manager_conf.xml'

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

contact_owner_template = """
GALAXY TOOL SHED REPOSITORY MESSAGE
------------------------

The user '${username}' sent you the following message regarding your tool shed
repository named '${repository_name}'.  You can respond by sending a reply to
the user's email address: ${email}.
-----------------------------------------------------------------------------
${message}
-----------------------------------------------------------------------------
This message was sent from the Galaxy Tool Shed instance hosted on the server
'${host}'
"""


def can_eliminate_repository_dependency(metadata_dict, tool_shed_url, name, owner):
    """
    Determine if the relationship between a repository_dependency record
    associated with a tool_shed_repository record on the Galaxy side
    can be eliminated.
    """
    rd_dict = metadata_dict.get('repository_dependencies', {})
    rd_tups = rd_dict.get('repository_dependencies', [])
    for rd_tup in rd_tups:
        tsu, n, o, none1, none2, none3 = common_util.parse_repository_dependency_tuple(rd_tup)
        if tsu == tool_shed_url and n == name and o == owner:
            # The repository dependency is current, so keep it.
            return False
    return True


def can_eliminate_tool_dependency(metadata_dict, name, dependency_type, version):
    """
    Determine if the relationship between a tool_dependency record
    associated with a tool_shed_repository record on the Galaxy side
    can be eliminated.
    """
    td_dict = metadata_dict.get('tool_dependencies', {})
    for td_key, td_val in td_dict.items():
        if td_key == 'set_environment':
            for td in td_val:
                n = td.get('name', None)
                t = td.get('type', None)
                if n == name and t == dependency_type:
                    # The tool dependency is current, so keep it.
                    return False
        else:
            n = td_val.get('name', None)
            t = td_val.get('type', None)
            v = td_val.get('version', None)
            if n == name and t == dependency_type and v == version:
                # The tool dependency is current, so keep it.
                return False
    return True


def clean_dependency_relationships(trans, metadata_dict, tool_shed_repository, tool_shed_url):
    """
    Repositories of type tool_dependency_definition allow for defining a
    package dependency at some point in the change log and then removing the
    dependency later in the change log.  This function keeps the dependency
    relationships on the Galaxy side current by deleting database records
    that defined the now-broken relationships.
    """
    for rrda in tool_shed_repository.required_repositories:
        rd = rrda.repository_dependency
        r = rd.repository
        if can_eliminate_repository_dependency(metadata_dict, tool_shed_url, r.name, r.owner):
            message = "Repository dependency %s by owner %s is not required by repository %s, owner %s, "
            message += "removing from list of repository dependencies."
            log.debug(message % (r.name, r.owner, tool_shed_repository.name, tool_shed_repository.owner))
            trans.install_model.context.delete(rrda)
            trans.install_model.context.flush()
    for td in tool_shed_repository.tool_dependencies:
        if can_eliminate_tool_dependency(metadata_dict, td.name, td.type, td.version):
            message = "Tool dependency %s, version %s is not required by repository %s, owner %s, "
            message += "removing from list of tool dependencies."
            log.debug(message % (td.name, td.version, tool_shed_repository.name, tool_shed_repository.owner))
            trans.install_model.context.delete(td)
            trans.install_model.context.flush()


def generate_tool_guid(repository_clone_url, tool):
    """
    Generate a guid for the installed tool.  It is critical that this guid matches the guid for
    the tool in the Galaxy tool shed from which it is being installed.  The form of the guid is
    <tool shed host>/repos/<repository owner>/<repository name>/<tool id>/<tool version>
    """
    tmp_url = common_util.remove_protocol_and_user_from_clone_url(repository_clone_url)
    return '%s/%s/%s' % (tmp_url, tool.id, tool.version)


def get_categories(app):
    """Get all categories from the database."""
    sa_session = app.model.context.current
    return sa_session.query(app.model.Category) \
                     .filter(app.model.Category.table.c.deleted == false()) \
                     .order_by(app.model.Category.table.c.name) \
                     .all()


def get_category(app, id):
    """Get a category from the database."""
    sa_session = app.model.context.current
    return sa_session.query(app.model.Category).get(app.security.decode_id(id))


def get_category_by_name(app, name):
    """Get a category from the database via name."""
    sa_session = app.model.context.current
    try:
        return sa_session.query(app.model.Category).filter_by(name=name).one()
    except sqlalchemy.orm.exc.NoResultFound:
        return None


def get_tool_shed_repo_requirements(app, tool_shed_url, repositories=None, repo_info_dicts=None):
    """
    Contact tool_shed_url for a list of requirements for a repository or a list of repositories.
    Returns a list of requirements, where each requirement is a dictionary with name and version as keys.
    """
    if not repositories and not repo_info_dicts:
        raise Exception("Need to pass either repository or repo_info_dicts")
    if repositories:
        if not isinstance(repositories, list):
            repositories = [repositories]
        repository_params = [{'name': repository.name,
                             'owner': repository.owner,
                             'changeset_revision': repository.changeset_revision} for repository in repositories]
    else:
        if not isinstance(repo_info_dicts, list):
            repo_info_dicts = [repo_info_dicts]
        repository_params = []
        for repo_info_dict in repo_info_dicts:
            for name, repo_info_tuple in repo_info_dict.items():
                # repo_info_tuple is a list, but keep terminology
                owner = repo_info_tuple[4]
                changeset_revision = repo_info_tuple[2]
                repository_params.append({'name': name,
                                          'owner': owner,
                                          'changeset_revision': changeset_revision})
    pathspec = ["api", "repositories", "get_repository_revision_install_info"]
    tools = []
    for params in repository_params:
        response = util.url_get(tool_shed_url,
                                password_mgr=app.tool_shed_registry.url_auth(tool_shed_url),
                                pathspec=pathspec,
                                params=params
                                )
        json_response = json.loads(response)
        valid_tools = json_response[1].get('valid_tools', [])
        if valid_tools:
            tools.extend(valid_tools)
    return get_requirements_from_tools(tools)


def get_requirements_from_tools(tools):
    return {tool['id']: galaxy.tools.deps.requirements.ToolRequirements.from_list(tool['requirements']) for tool in tools}


def get_requirements_from_repository(repository):
    if not repository.includes_tools:
        return {}
    else:
        return get_requirements_from_tools(repository.metadata.get('tools', []))


def get_ctx_rev(app, tool_shed_url, name, owner, changeset_revision):
    """
    Send a request to the tool shed to retrieve the ctx_rev for a repository defined by the
    combination of a name, owner and changeset revision.
    """
    tool_shed_url = common_util.get_tool_shed_url_from_tool_shed_registry(app, tool_shed_url)
    params = dict(name=name, owner=owner, changeset_revision=changeset_revision)
    pathspec = ['repository', 'get_ctx_rev']
    ctx_rev = util.url_get(tool_shed_url, password_mgr=app.tool_shed_registry.url_auth(tool_shed_url), pathspec=pathspec, params=params)
    return ctx_rev


def get_next_prior_import_or_install_required_dict_entry(prior_required_dict, processed_tsr_ids):
    """
    This method is used in the Tool Shed when exporting a repository and its dependencies, and in Galaxy
    when a repository and its dependencies are being installed.  The order in which the prior_required_dict
    is processed is critical in order to ensure that the ultimate repository import or installation order is
    correctly defined.  This method determines the next key / value pair from the received prior_required_dict
    that should be processed.
    """
    # Return the first key / value pair that is not yet processed and whose value is an empty list.
    for key, value in prior_required_dict.items():
        if key in processed_tsr_ids:
            continue
        if not value:
            return key
    # Return the first key / value pair that is not yet processed and whose ids in value are all included
    # in processed_tsr_ids.
    for key, value in prior_required_dict.items():
        if key in processed_tsr_ids:
            continue
        all_contained = True
        for required_repository_id in value:
            if required_repository_id not in processed_tsr_ids:
                all_contained = False
                break
        if all_contained:
            return key
    # Return the first key / value pair that is not yet processed.  Hopefully this is all that is necessary
    # at this point.
    for key, value in prior_required_dict.items():
        if key in processed_tsr_ids:
            continue
        return key


def get_repository_categories(app, id):
    """Get categories of a repository on the tool shed side from the database via id"""
    sa_session = app.model.context.current
    return sa_session.query(app.model.RepositoryCategoryAssociation) \
        .filter(app.model.RepositoryCategoryAssociation.table.c.repository_id == app.security.decode_id(id))


def get_repository_file_contents(app, file_path, repository_id, is_admin=False):
    """Return the display-safe contents of a repository file for display in a browser."""
    safe_str = ''
    if not is_path_browsable(app, file_path, repository_id, is_admin):
        log.warning('Request tries to access a file outside of the repository location. File path: %s', file_path)
        return 'Invalid file path'
    # Symlink targets are checked by is_path_browsable
    if os.path.islink(file_path):
        safe_str = 'link to: ' + basic_util.to_html_string(os.readlink(file_path))
        return safe_str
    elif checkers.is_gzip(file_path):
        return '<br/>gzip compressed file<br/>'
    elif checkers.is_bz2(file_path):
        return '<br/>bz2 compressed file<br/>'
    elif checkers.is_zip(file_path):
        return '<br/>zip compressed file<br/>'
    elif checkers.check_binary(file_path):
        return '<br/>Binary file<br/>'
    else:
        for i, line in enumerate(open(file_path)):
            safe_str = '%s%s' % (safe_str, basic_util.to_html_string(line))
            # Stop reading after string is larger than MAX_CONTENT_SIZE.
            if len(safe_str) > MAX_CONTENT_SIZE:
                large_str = \
                    '<br/>File contents truncated because file size is larger than maximum viewing size of %s<br/>' % \
                    util.nice_size(MAX_CONTENT_SIZE)
                safe_str = '%s%s' % (safe_str, large_str)
                break

        if len(safe_str) > basic_util.MAX_DISPLAY_SIZE:
            # Eliminate the middle of the file to display a file no larger than basic_util.MAX_DISPLAY_SIZE.
            # This may not be ideal if the file is larger than MAX_CONTENT_SIZE.
            join_by_str = \
                "<br/><br/>...some text eliminated here because file size is larger than maximum viewing size of %s...<br/><br/>" % \
                util.nice_size(basic_util.MAX_DISPLAY_SIZE)
            safe_str = util.shrink_string_by_size(safe_str,
                                                  basic_util.MAX_DISPLAY_SIZE,
                                                  join_by=join_by_str,
                                                  left_larger=True,
                                                  beginning_on_size_error=True)
        return safe_str


def get_repository_files(folder_path):
    """Return the file hierarchy of a tool shed repository."""
    contents = []
    for item in os.listdir(folder_path):
        # Skip .hg directories
        if item.startswith('.hg'):
            continue
        contents.append(item)
    if contents:
        contents.sort()
    return contents


def get_repository_from_refresh_on_change(app, **kwd):
    # The changeset_revision_select_field in several grids performs a refresh_on_change which sends in request parameters like
    # changeset_revison_1, changeset_revision_2, etc.  One of the many select fields on the grid performed the refresh_on_change,
    # so we loop through all of the received values to see which value is not the repository tip.  If we find it, we know the
    # refresh_on_change occurred and we have the necessary repository id and change set revision to pass on.
    repository_id = None
    v = None
    for k, v in kwd.items():
        changeset_revision_str = 'changeset_revision_'
        if k.startswith(changeset_revision_str):
            repository_id = app.security.encode_id(int(k.lstrip(changeset_revision_str)))
            repository = repository_util.get_repository_in_tool_shed(app, repository_id)
            if repository.tip(app) != v:
                return v, repository
    # This should never be reached - raise an exception?
    return v, None


def get_repository_type_from_tool_shed(app, tool_shed_url, name, owner):
    """
    Send a request to the tool shed to retrieve the type for a repository defined by the
    combination of a name and owner.
    """
    tool_shed_url = common_util.get_tool_shed_url_from_tool_shed_registry(app, tool_shed_url)
    params = dict(name=name, owner=owner)
    pathspec = ['repository', 'get_repository_type']
    repository_type = util.url_get(tool_shed_url, password_mgr=app.tool_shed_registry.url_auth(tool_shed_url), pathspec=pathspec, params=params)
    return repository_type


def get_tool_dependency_definition_metadata_from_tool_shed(app, tool_shed_url, name, owner):
    """
    Send a request to the tool shed to retrieve the current metadata for a
    repository of type tool_dependency_definition defined by the combination
    of a name and owner.
    """
    tool_shed_url = common_util.get_tool_shed_url_from_tool_shed_registry(app, tool_shed_url)
    params = dict(name=name, owner=owner)
    pathspec = ['repository', 'get_tool_dependency_definition_metadata']
    metadata = util.url_get(tool_shed_url, password_mgr=app.tool_shed_registry.url_auth(tool_shed_url), pathspec=pathspec, params=params)
    return metadata


def get_tool_panel_config_tool_path_install_dir(app, repository):
    """
    Return shed-related tool panel config, the tool_path configured in it, and the relative path to
    the directory where the repository is installed.  This method assumes all repository tools are
    defined in a single shed-related tool panel config.
    """
    tool_shed = common_util.remove_port_from_tool_shed_url(str(repository.tool_shed))
    relative_install_dir = '%s/repos/%s/%s/%s' % (tool_shed,
                                                  str(repository.owner),
                                                  str(repository.name),
                                                  str(repository.installed_changeset_revision))
    # Get the relative tool installation paths from each of the shed tool configs.
    shed_config_dict = repository.get_shed_config_dict(app)
    if not shed_config_dict:
        # Just pick a semi-random shed config.
        for shed_config_dict in app.toolbox.dynamic_confs(include_migrated_tool_conf=True):
            if (repository.dist_to_shed and shed_config_dict['config_filename'] == app.config.migrated_tools_config) \
                    or (not repository.dist_to_shed and shed_config_dict['config_filename'] != app.config.migrated_tools_config):
                break
    shed_tool_conf = shed_config_dict['config_filename']
    tool_path = shed_config_dict['tool_path']
    return shed_tool_conf, tool_path, relative_install_dir


def get_tool_path_by_shed_tool_conf_filename(app, shed_tool_conf):
    """
    Return the tool_path config setting for the received shed_tool_conf file by searching the tool box's in-memory list of shed_tool_confs for the
    dictionary whose config_filename key has a value matching the received shed_tool_conf.
    """
    for shed_tool_conf_dict in app.toolbox.dynamic_confs(include_migrated_tool_conf=True):
        config_filename = shed_tool_conf_dict['config_filename']
        if config_filename == shed_tool_conf:
            return shed_tool_conf_dict['tool_path']
        else:
            file_name = basic_util.strip_path(config_filename)
            if file_name == shed_tool_conf:
                return shed_tool_conf_dict['tool_path']
    return None


def get_user(app, id):
    """Get a user from the database by id."""
    sa_session = app.model.context.current
    return sa_session.query(app.model.User).get(app.security.decode_id(id))


def handle_email_alerts(app, host, repository, content_alert_str='', new_repo_alert=False, admin_only=False):
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
       change set tha tincludes valid content is produced.
    3. An admin user checks the "Receive email alerts" check box on the manage repository page.  Since the
       user is an admin user, the email will include information about both HTML and image content that was
       included in the change set.
    4. A regular user checks the "Receive email alerts" check box on the manage repository page.  Since the
       user is not an admin user, the email will not include any information about both HTML and image content
       that was included in the change set.
    """
    sa_session = app.model.context.current
    repo = hg_util.get_repo_for_repository(app, repository=repository)
    sharable_link = repository_util.generate_sharable_link_for_repository_in_tool_shed(repository, changeset_revision=None)
    smtp_server = app.config.smtp_server
    if smtp_server and (new_repo_alert or repository.email_alerts):
        # Send email alert to users that want them.
        if app.config.email_from is not None:
            email_from = app.config.email_from
        elif host.split(':')[0] in ['localhost', '127.0.0.1', '0.0.0.0']:
            email_from = 'galaxy-no-reply@' + socket.getfqdn()
        else:
            email_from = 'galaxy-no-reply@' + host.split(':')[0]
        tip_changeset = repo.changelog.tip()
        ctx = repo.changectx(tip_changeset)
        try:
            username = ctx.user().split()[0]
        except Exception:
            username = ctx.user()
        # We'll use 2 template bodies because we only want to send content
        # alerts to tool shed admin users.
        if new_repo_alert:
            template = new_repo_email_alert_template
        else:
            template = email_alert_template
        display_date = hg_util.get_readable_ctx_date(ctx)
        admin_body = string.Template(template).safe_substitute(host=host,
                                                               sharable_link=sharable_link,
                                                               repository_name=repository.name,
                                                               revision='%s:%s' % (str(ctx.rev()), ctx),
                                                               display_date=display_date,
                                                               description=ctx.description(),
                                                               username=username,
                                                               content_alert_str=content_alert_str)
        body = string.Template(template).safe_substitute(host=host,
                                                         sharable_link=sharable_link,
                                                         repository_name=repository.name,
                                                         revision='%s:%s' % (str(ctx.rev()), ctx),
                                                         display_date=display_date,
                                                         description=ctx.description(),
                                                         username=username,
                                                         content_alert_str='')
        admin_users = app.config.get("admin_users", "").split(",")
        frm = email_from
        if new_repo_alert:
            subject = "Galaxy tool shed alert for new repository named %s" % str(repository.name)
            subject = subject[:80]
            email_alerts = []
            for user in sa_session.query(app.model.User) \
                                  .filter(and_(app.model.User.table.c.deleted == false(),
                                               app.model.User.table.c.new_repo_alert == true())):
                if admin_only:
                    if user.email in admin_users:
                        email_alerts.append(user.email)
                else:
                    email_alerts.append(user.email)
        else:
            subject = "Galaxy tool shed update alert for repository named %s" % str(repository.name)
            email_alerts = json.loads(repository.email_alerts)
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


def have_shed_tool_conf_for_install(app):
    return bool(app.toolbox.dynamic_confs(include_migrated_tool_conf=False))


def is_path_browsable(app, path, repository_id, is_admin=False):
    """
    Detects whether the given path is browsable i.e. is within the
    allowed repository folders. Admins can additionaly browse folders
    with tool dependencies.
    """
    if is_admin and is_path_within_dependency_dir(app, path):
        return True
    return is_path_within_repo(app, path, repository_id)


def is_path_within_dependency_dir(app, path):
    """
    Detect whether the given path is within the tool_dependency_dir folder on the disk.
    (Specified by the config option). Use to filter malicious symlinks targeting outside paths.
    """
    allowed = False
    resolved_path = os.path.realpath(path)
    tool_dependency_dir = app.config.get('tool_dependency_dir', None)
    if tool_dependency_dir:
        dependency_path = os.path.abspath(tool_dependency_dir)
        allowed = os.path.commonprefix([dependency_path, resolved_path]) == dependency_path
    return allowed


def is_path_within_repo(app, path, repository_id):
    """
    Detect whether the given path is within the repository folder on the disk.
    Use to filter malicious symlinks targeting outside paths.
    """
    repo_path = os.path.abspath(repository_util.get_repository_by_id(app, repository_id).repo_path(app))
    resolved_path = os.path.realpath(path)
    return os.path.commonprefix([repo_path, resolved_path]) == repo_path


def open_repository_files_folder(app, folder_path, repository_id, is_admin=False):
    """
    Return a list of dictionaries, each of which contains information for a file or directory contained
    within a directory in a repository file hierarchy.
    """
    if not is_path_browsable(app, folder_path, repository_id, is_admin):
        log.warning('Request tries to access a folder outside of the allowed locations. Folder path: %s', folder_path)
        return []
    try:
        files_list = get_repository_files(folder_path)
    except OSError as e:
        if str(e).find('No such file or directory') >= 0:
            # We have a repository with no contents.
            return []
    folder_contents = []
    for filename in files_list:
        is_folder = False
        full_path = os.path.join(folder_path, filename)
        is_link = os.path.islink(full_path)
        path_is_browsable = is_path_browsable(app, full_path, repository_id)
        if is_link and not path_is_browsable:
            log.warning('Valid folder contains a symlink outside of the repository location. Link found in: ' + str(full_path))
        if filename:
            if os.path.isdir(full_path) and path_is_browsable:
                # Append a '/' character so that our jquery dynatree will function properly.
                filename = '%s/' % filename
                full_path = '%s/' % full_path
                is_folder = True
            node = {"title": filename,
                    "isFolder": is_folder,
                    "isLazy": is_folder,
                    "tooltip": full_path,
                    "key": full_path}
            folder_contents.append(node)
    return folder_contents


def set_image_paths(app, text, encoded_repository_id=None, tool_shed_repository=None, tool_id=None, tool_version=None):
    """
    Handle tool help image display for tools that are contained in repositories in
    the tool shed or installed into Galaxy as well as image display in repository
    README files.  This method will determine the location of the image file and
    return the path to it that will enable the caller to open the file.
    """
    if text:
        if repository_util.is_tool_shed_client(app) and encoded_repository_id:
            route_to_images = 'admin_toolshed/static/images/%s' % encoded_repository_id
        elif encoded_repository_id:
            # We're in the tool shed.
            route_to_images = '/repository/static/images/%s' % encoded_repository_id
        elif tool_shed_repository and tool_id and tool_version:
            route_to_images = 'shed_tool_static/{shed}/{owner}/{repo}/{tool}/{version}'.format(
                shed=tool_shed_repository.tool_shed,
                owner=tool_shed_repository.owner,
                repo=tool_shed_repository.name,
                tool=tool_id,
                version=tool_version,
            )
        else:
            raise Exception("encoded_repository_id or tool_shed_repository and tool_id and tool_version must be provided")
        # We used to require $PATH_TO_IMAGES and ${static_path}, but
        # we now eliminate it if it's used.
        text = text.replace('$PATH_TO_IMAGES', '')
        text = text.replace('${static_path}', '')
        # Use regex to instantiate routes into the defined image paths, but replace
        # paths that start with neither http:// nor https://, which will allow for
        # settings like .. images:: http_files/images/help.png
        for match in re.findall('.. image:: (?!http)/?(.+)', text):
            text = text.replace(match, match.replace('/', '%2F'))
        text = re.sub(r'\.\. image:: (?!https?://)/?(.+)', r'.. image:: %s/\1' % route_to_images, text)
    return text


def tool_shed_is_this_tool_shed(toolshed_base_url):
    """Determine if a tool shed is the current tool shed."""
    cleaned_toolshed_base_url = common_util.remove_protocol_from_tool_shed_url(toolshed_base_url)
    cleaned_tool_shed = common_util.remove_protocol_from_tool_shed_url(str(url_for('/', qualified=True)))
    return cleaned_toolshed_base_url == cleaned_tool_shed
