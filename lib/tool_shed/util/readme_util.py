import logging

log = logging.getLogger(__name__)


def get_readme_file_names(repository_name):
    """Return a list of file names that will be categorized as README files for the received repository_name."""
    readme_files = ['readme', 'read_me', 'install']
    valid_filenames = ['%s.txt' % f for f in readme_files]
    valid_filenames.extend(['%s.rst' % f for f in readme_files])
    valid_filenames.extend(readme_files)
    valid_filenames.append('%s.txt' % repository_name)
    valid_filenames.append('%s.rst' % repository_name)
    return valid_filenames
