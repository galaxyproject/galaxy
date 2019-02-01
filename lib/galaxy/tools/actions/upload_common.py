import ipaddress
import logging
import os
import shlex
import socket
import subprocess
import tempfile
from json import dump, dumps

from six import StringIO
from six.moves.urllib.parse import urlparse
from sqlalchemy.orm import eagerload_all
from webob.compat import cgi_FieldStorage

from galaxy import datatypes, util
from galaxy.exceptions import ConfigDoesNotAllowException, ObjectInvalid
from galaxy.managers import tags
from galaxy.util import unicodify
from galaxy.util.odict import odict

log = logging.getLogger(__name__)


def validate_url(url, ip_whitelist):
    # If it doesn't look like a URL, ignore it.
    if not (url.lstrip().startswith('http://') or url.lstrip().startswith('https://')):
        return url

    # Extract hostname component
    parsed_url = urlparse(url).netloc
    # If credentials are in this URL, we need to strip those.
    if parsed_url.count('@') > 0:
        # credentials.
        parsed_url = parsed_url[parsed_url.rindex('@') + 1:]
    # Percent encoded colons and other characters will not be resolved as such
    # so we don't have to either.

    # Sometimes the netloc will contain the port which is not desired, so we
    # need to extract that.
    port = None
    # However, it could ALSO be an IPv6 address they've supplied.
    if ':' in parsed_url:
        # IPv6 addresses have colons in them already (it seems like always more than two)
        if parsed_url.count(':') >= 2:
            # Since IPv6 already use colons extensively, they wrap it in
            # brackets when there is a port, e.g. http://[2001:db8:1f70::999:de8:7648:6e8]:100/
            # However if it ends with a ']' then there is no port after it and
            # they've wrapped it in brackets just for fun.
            if ']' in parsed_url and not parsed_url.endswith(']'):
                # If this +1 throws a range error, we don't care, their url
                # shouldn't end with a colon.
                idx = parsed_url.rindex(':')
                # We parse as an int and let this fail ungracefully if parsing
                # fails because we desire to fail closed rather than open.
                port = int(parsed_url[idx + 1:])
                parsed_url = parsed_url[:idx]
            else:
                # Plain ipv6 without port
                pass
        else:
            # This should finally be ipv4 with port. It cannot be IPv6 as that
            # was caught by earlier cases, and it cannot be due to credentials.
            idx = parsed_url.rindex(':')
            port = int(parsed_url[idx + 1:])
            parsed_url = parsed_url[:idx]

    # safe to log out, no credentials/request path, just an IP + port
    log.debug("parsed url, port: %s : %s", parsed_url, port)
    # Call getaddrinfo to resolve hostname into tuples containing IPs.
    addrinfo = socket.getaddrinfo(parsed_url, port)
    # Get the IP addresses that this entry resolves to (uniquely)
    # We drop:
    #   AF_* family: It will resolve to AF_INET or AF_INET6, getaddrinfo(3) doesn't even mention AF_UNIX,
    #   socktype: We don't care if a stream/dgram/raw protocol
    #   protocol: we don't care if it is tcp or udp.
    addrinfo_results = set([info[4][0] for info in addrinfo])
    # There may be multiple (e.g. IPv4 + IPv6 or DNS round robin). Any one of these
    # could resolve to a local addresses (and could be returned by chance),
    # therefore we must check them all.
    for raw_ip in addrinfo_results:
        # Convert to an IP object so we can tell if it is in private space.
        ip = ipaddress.ip_address(unicodify(raw_ip))
        # If this is a private address
        if ip.is_private:
            results = []
            # If this IP is not anywhere in the whitelist
            for whitelisted in ip_whitelist:
                # If it's an IP address range (rather than a single one...)
                if hasattr(whitelisted, 'subnets'):
                    results.append(ip in whitelisted)
                else:
                    results.append(ip == whitelisted)

            if any(results):
                # If we had any True, then THIS (and ONLY THIS) IP address that
                # that specific DNS entry resolved to is in whitelisted and
                # safe to access. But we cannot exit here, we must ensure that
                # all IPs that that DNS entry resolves to are likewise safe.
                pass
            else:
                # Otherwise, we deny access.
                raise ConfigDoesNotAllowException("Access to this address in not permitted by server configuration")
    return url


def persist_uploads(params, trans):
    """
    Turn any uploads in the submitted form to persisted files.
    """
    if 'files' in params:
        new_files = []
        for upload_dataset in params['files']:
            f = upload_dataset['file_data']
            if isinstance(f, cgi_FieldStorage):
                assert not isinstance(f.file, StringIO)
                assert f.file.name != '<fdopen>'
                local_filename = util.mkstemp_ln(f.file.name, 'upload_file_data_')
                f.file.close()
                upload_dataset['file_data'] = dict(filename=f.filename,
                                                   local_filename=local_filename)
            elif type(f) == dict and 'local_filename' not in f:
                raise Exception('Uploaded file was encoded in a way not understood by Galaxy.')
            if 'url_paste' in upload_dataset and upload_dataset['url_paste'] and upload_dataset['url_paste'].strip() != '':
                upload_dataset['url_paste'] = datatypes.sniff.stream_to_file(
                    StringIO(validate_url(upload_dataset['url_paste'], trans.app.config.fetch_url_whitelist_ips)),
                    prefix="strio_url_paste_"
                )
            else:
                upload_dataset['url_paste'] = None
            new_files.append(upload_dataset)
        params['files'] = new_files
    return params


def handle_library_params(trans, params, folder_id, replace_dataset=None):
    # FIXME: the received params has already been parsed by util.Params() by the time it reaches here,
    # so no complex objects remain.  This is not good because it does not allow for those objects to be
    # manipulated here.  The received params should be the original kwd from the initial request.
    library_bunch = util.bunch.Bunch()
    library_bunch.replace_dataset = replace_dataset
    library_bunch.message = params.get('ldda_message', '')
    # See if we have any template field contents
    library_bunch.template_field_contents = {}
    template_id = params.get('template_id', None)
    library_bunch.folder = trans.sa_session.query(trans.app.model.LibraryFolder).get(trans.security.decode_id(folder_id))
    # We are inheriting the folder's info_association, so we may have received inherited contents or we may have redirected
    # here after the user entered template contents ( due to errors ).
    if template_id not in [None, 'None']:
        library_bunch.template = trans.sa_session.query(trans.app.model.FormDefinition).get(template_id)
        for field in library_bunch.template.fields:
            field_name = field['name']
            if params.get(field_name, False):
                field_value = util.restore_text(params.get(field_name, ''))
                library_bunch.template_field_contents[field_name] = field_value
    else:
        library_bunch.template = None
    library_bunch.roles = []
    for role_id in util.listify(params.get('roles', [])):
        role = trans.sa_session.query(trans.app.model.Role).get(role_id)
        library_bunch.roles.append(role)
    return library_bunch


def __new_history_upload(trans, uploaded_dataset, history=None, state=None):
    if not history:
        history = trans.history
    hda = trans.app.model.HistoryDatasetAssociation(name=uploaded_dataset.name,
                                                    extension=uploaded_dataset.file_type,
                                                    dbkey=uploaded_dataset.dbkey,
                                                    history=history,
                                                    create_dataset=True,
                                                    sa_session=trans.sa_session)
    trans.sa_session.add(hda)
    if state:
        hda.state = state
    else:
        hda.state = hda.states.QUEUED
    trans.sa_session.flush()
    history.add_dataset(hda, genome_build=uploaded_dataset.dbkey)
    permissions = trans.app.security_agent.history_get_default_permissions(history)
    trans.app.security_agent.set_all_dataset_permissions(hda.dataset, permissions)
    trans.sa_session.flush()
    return hda


def __new_library_upload(trans, cntrller, uploaded_dataset, library_bunch, state=None):
    current_user_roles = trans.get_current_user_roles()
    if not ((trans.user_is_admin and cntrller in ['library_admin', 'api']) or trans.app.security_agent.can_add_library_item(current_user_roles, library_bunch.folder)):
        # This doesn't have to be pretty - the only time this should happen is if someone's being malicious.
        raise Exception("User is not authorized to add datasets to this library.")
    folder = library_bunch.folder
    if uploaded_dataset.get('in_folder', False):
        # Create subfolders if desired
        for name in uploaded_dataset.in_folder.split(os.path.sep):
            trans.sa_session.refresh(folder)
            matches = [x for x in active_folders(trans, folder) if x.name == name]
            if matches:
                folder = matches[0]
            else:
                new_folder = trans.app.model.LibraryFolder(name=name, description='Automatically created by upload tool')
                new_folder.genome_build = trans.app.genome_builds.default_value
                folder.add_folder(new_folder)
                trans.sa_session.add(new_folder)
                trans.sa_session.flush()
                trans.app.security_agent.copy_library_permissions(trans, folder, new_folder)
                folder = new_folder
    if library_bunch.replace_dataset:
        ld = library_bunch.replace_dataset
    else:
        ld = trans.app.model.LibraryDataset(folder=folder, name=uploaded_dataset.name)
        trans.sa_session.add(ld)
        trans.sa_session.flush()
        trans.app.security_agent.copy_library_permissions(trans, folder, ld)
    ldda = trans.app.model.LibraryDatasetDatasetAssociation(name=uploaded_dataset.name,
                                                            extension=uploaded_dataset.file_type,
                                                            dbkey=uploaded_dataset.dbkey,
                                                            library_dataset=ld,
                                                            user=trans.user,
                                                            create_dataset=True,
                                                            sa_session=trans.sa_session)
    if uploaded_dataset.get('tag_using_filenames', False):
        tag_from_filename = os.path.splitext(os.path.basename(uploaded_dataset.name))[0]
        tag_manager = tags.GalaxyTagManager(trans.sa_session)
        tag_manager.apply_item_tag(item=ldda, user=trans.user, name='name', value=tag_from_filename)

    trans.sa_session.add(ldda)
    if state:
        ldda.state = state
    else:
        ldda.state = ldda.states.QUEUED
    ldda.message = library_bunch.message
    trans.sa_session.flush()
    # Permissions must be the same on the LibraryDatasetDatasetAssociation and the associated LibraryDataset
    trans.app.security_agent.copy_library_permissions(trans, ld, ldda)
    if library_bunch.replace_dataset:
        # Copy the Dataset level permissions from replace_dataset to the new LibraryDatasetDatasetAssociation.dataset
        trans.app.security_agent.copy_dataset_permissions(library_bunch.replace_dataset.library_dataset_dataset_association.dataset, ldda.dataset)
    else:
        # Copy the current user's DefaultUserPermissions to the new LibraryDatasetDatasetAssociation.dataset
        trans.app.security_agent.set_all_dataset_permissions(ldda.dataset, trans.app.security_agent.user_get_default_permissions(trans.user))
        folder.add_library_dataset(ld, genome_build=uploaded_dataset.dbkey)
        trans.sa_session.add(folder)
        trans.sa_session.flush()
    ld.library_dataset_dataset_association_id = ldda.id
    trans.sa_session.add(ld)
    trans.sa_session.flush()
    # Handle template included in the upload form, if any.  If the upload is not asynchronous ( e.g., URL paste ),
    # then the template and contents will be included in the library_bunch at this point.  If the upload is
    # asynchronous ( e.g., uploading a file ), then the template and contents will be included in the library_bunch
    # in the get_uploaded_datasets() method below.
    if library_bunch.template and library_bunch.template_field_contents:
        # Since information templates are inherited, the template fields can be displayed on the upload form.
        # If the user has added field contents, we'll need to create a new form_values and info_association
        # for the new library_dataset_dataset_association object.
        # Create a new FormValues object, using the template we previously retrieved
        form_values = trans.app.model.FormValues(library_bunch.template, library_bunch.template_field_contents)
        trans.sa_session.add(form_values)
        trans.sa_session.flush()
        # Create a new info_association between the current ldda and form_values
        # TODO: Currently info_associations at the ldda level are not inheritable to the associated LibraryDataset,
        # we need to figure out if this is optimal
        info_association = trans.app.model.LibraryDatasetDatasetInfoAssociation(ldda, library_bunch.template, form_values)
        trans.sa_session.add(info_association)
        trans.sa_session.flush()
    # If roles were selected upon upload, restrict access to the Dataset to those roles
    if library_bunch.roles:
        for role in library_bunch.roles:
            dp = trans.app.model.DatasetPermissions(trans.app.security_agent.permitted_actions.DATASET_ACCESS.action, ldda.dataset, role)
            trans.sa_session.add(dp)
            trans.sa_session.flush()
    return ldda


def new_upload(trans, cntrller, uploaded_dataset, library_bunch=None, history=None, state=None, tag_list=None):
    if library_bunch:
        upload_target_dataset_instance = __new_library_upload(trans, cntrller, uploaded_dataset, library_bunch, state)
    else:
        upload_target_dataset_instance = __new_history_upload(trans, uploaded_dataset, history=history, state=state)

    if tag_list:
        trans.app.tag_handler.add_tags_from_list(trans.user, upload_target_dataset_instance, tag_list)

    return upload_target_dataset_instance


def get_uploaded_datasets(trans, cntrller, params, dataset_upload_inputs, library_bunch=None, history=None):
    uploaded_datasets = []
    for dataset_upload_input in dataset_upload_inputs:
        uploaded_datasets.extend(dataset_upload_input.get_uploaded_datasets(trans, params))
    for uploaded_dataset in uploaded_datasets:
        data = new_upload(trans, cntrller, uploaded_dataset, library_bunch=library_bunch, history=history)
        uploaded_dataset.data = data
    return uploaded_datasets


def create_paramfile(trans, uploaded_datasets):
    """
    Create the upload tool's JSON "param" file.
    """
    def _chown(path):
        try:
            # get username from email/username
            pwent = trans.user.system_user_pwent(trans.app.config.real_system_username)
            cmd = shlex.split(trans.app.config.external_chown_script)
            cmd.extend([path, pwent[0], str(pwent[3])])
            log.debug('Changing ownership of %s with: %s' % (path, ' '.join(cmd)))
            p = subprocess.Popen(cmd, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = p.communicate()
            assert p.returncode == 0, stderr
        except Exception as e:
            log.warning('Changing ownership of uploaded file %s failed: %s' % (path, str(e)))

    tool_params = []
    json_file_path = None
    for uploaded_dataset in uploaded_datasets:
        data = uploaded_dataset.data
        if uploaded_dataset.type == 'composite':
            # we need to init metadata before the job is dispatched
            data.init_meta()
            for meta_name, meta_value in uploaded_dataset.metadata.items():
                setattr(data.metadata, meta_name, meta_value)
            trans.sa_session.add(data)
            trans.sa_session.flush()
            params = dict(file_type=uploaded_dataset.file_type,
                          dataset_id=data.dataset.id,
                          dbkey=uploaded_dataset.dbkey,
                          type=uploaded_dataset.type,
                          metadata=uploaded_dataset.metadata,
                          primary_file=uploaded_dataset.primary_file,
                          composite_file_paths=uploaded_dataset.composite_files,
                          composite_files=dict((k, v.__dict__) for k, v in data.datatype.get_composite_files(data).items()))
        else:
            try:
                is_binary = uploaded_dataset.datatype.is_binary
            except Exception:
                is_binary = None
            try:
                link_data_only = uploaded_dataset.link_data_only
            except Exception:
                link_data_only = 'copy_files'
            try:
                uuid_str = uploaded_dataset.uuid
            except Exception:
                uuid_str = None
            try:
                purge_source = uploaded_dataset.purge_source
            except Exception:
                purge_source = True
            try:
                user_ftp_dir = os.path.abspath(trans.user_ftp_dir)
            except Exception:
                user_ftp_dir = None
            if user_ftp_dir and uploaded_dataset.path.startswith(user_ftp_dir):
                uploaded_dataset.type = 'ftp_import'
            params = dict(file_type=uploaded_dataset.file_type,
                          ext=uploaded_dataset.ext,
                          name=uploaded_dataset.name,
                          dataset_id=data.dataset.id,
                          dbkey=uploaded_dataset.dbkey,
                          type=uploaded_dataset.type,
                          is_binary=is_binary,
                          link_data_only=link_data_only,
                          uuid=uuid_str,
                          to_posix_lines=getattr(uploaded_dataset, "to_posix_lines", True),
                          auto_decompress=getattr(uploaded_dataset, "auto_decompress", True),
                          purge_source=purge_source,
                          space_to_tab=uploaded_dataset.space_to_tab,
                          run_as_real_user=trans.app.config.external_chown_script is not None,
                          check_content=trans.app.config.check_upload_content,
                          path=uploaded_dataset.path)
            # TODO: This will have to change when we start bundling inputs.
            # Also, in_place above causes the file to be left behind since the
            # user cannot remove it unless the parent directory is writable.
            if link_data_only == 'copy_files' and trans.app.config.external_chown_script:
                _chown(uploaded_dataset.path)
        tool_params.append(params)
    with tempfile.NamedTemporaryFile(mode="w", prefix='upload_params_', delete=False) as fh:
        json_file_path = fh.name
        dump(tool_params, fh)
    return json_file_path


def create_job(trans, params, tool, json_file_path, outputs, folder=None, history=None, job_params=None):
    """
    Create the upload job.
    """
    job = trans.app.model.Job()
    galaxy_session = trans.get_galaxy_session()
    if type(galaxy_session) == trans.model.GalaxySession:
        job.session_id = galaxy_session.id
    if trans.user is not None:
        job.user_id = trans.user.id
    if folder:
        job.library_folder_id = folder.id
    else:
        if not history:
            history = trans.history
        job.history_id = history.id
    job.tool_id = tool.id
    job.tool_version = tool.version
    job.set_state(job.states.UPLOAD)
    trans.sa_session.add(job)
    trans.sa_session.flush()
    log.info('tool %s created job id %d' % (tool.id, job.id))
    trans.log_event('created job id %d' % job.id, tool_id=tool.id)

    for name, value in tool.params_to_strings(params, trans.app).items():
        job.add_parameter(name, value)
    job.add_parameter('paramfile', dumps(json_file_path))
    object_store_id = None
    for i, output_object in enumerate(outputs):
        output_name = "output%i" % i
        if hasattr(output_object, "collection"):
            job.add_output_dataset_collection(output_name, output_object)
            output_object.job = job
        else:
            dataset = output_object
            if folder:
                job.add_output_library_dataset(output_name, dataset)
            else:
                job.add_output_dataset(output_name, dataset)
            # Create an empty file immediately
            if not dataset.dataset.external_filename and trans.app.config.legacy_eager_objectstore_initialization:
                dataset.dataset.object_store_id = object_store_id
                try:
                    trans.app.object_store.create(dataset.dataset)
                except ObjectInvalid:
                    raise Exception('Unable to create output dataset: object store is full')
                object_store_id = dataset.dataset.object_store_id

        trans.sa_session.add(output_object)

    job.object_store_id = object_store_id
    job.set_state(job.states.NEW)
    if job_params:
        for name, value in job_params.items():
            job.add_parameter(name, value)
    trans.sa_session.add(job)

    # Queue the job for execution
    trans.app.job_manager.enqueue(job, tool=tool)
    trans.log_event("Added job to the job queue, id: %s" % str(job.id), tool_id=job.tool_id)
    output = odict()
    for i, v in enumerate(outputs):
        if not hasattr(output_object, "collection_type"):
            output['output%i' % i] = v
    return job, output


def active_folders(trans, folder):
    # Stolen from galaxy.web.controllers.library_common (importing from which causes a circular issues).
    # Much faster way of retrieving all active sub-folders within a given folder than the
    # performance of the mapper.  This query also eagerloads the permissions on each folder.
    return trans.sa_session.query(trans.app.model.LibraryFolder) \
                           .filter_by(parent=folder, deleted=False) \
                           .options(eagerload_all("actions")) \
                           .order_by(trans.app.model.LibraryFolder.table.c.name) \
                           .all()
