import subprocess
import os

SSH_OPTIONS = ['-o', 'StrictHostKeyChecking=no', '-o', 'PreferredAuthentications=publickey', '-o', 'PubkeyAuthentication=yes']


def rsync_get_file(uri_from, uri_to, user, host, port, key):
    cmd = [
        'rsync',
        '-e',
        'ssh -i %s -p %s %s' % (key, port, ' '.join(SSH_OPTIONS)),
        '%s@%s:%s' % (user, host, uri_from),
        uri_to,
    ]
    _call(cmd)


def rsync_post_file(uri_from, uri_to, user, host, port, key):
    _ensure_dir(uri_to, key, port, user, host)
    cmd = [
        'rsync',
        '-e',
        'ssh -i %s -p %s %s' % (key, port, ' '.join(SSH_OPTIONS)),
        uri_from,
        '%s@%s:%s' % (user, host, uri_to),
    ]
    _call(cmd)


def scp_get_file(uri_from, uri_to, user, host, port, key):
    cmd = [
        'scp',
        '-P', str(port),
        '-i', key
    ] + SSH_OPTIONS + [
        '%s@%s:%s' % (user, host, uri_from),
        uri_to,
    ]
    _call(cmd)


def scp_post_file(uri_from, uri_to, user, host, port, key):
    _ensure_dir(uri_to, key, port, user, host)
    cmd = [
        'scp',
        '-P', str(port),
        '-i', key,
    ] + SSH_OPTIONS + [
        uri_from,
        '%s@%s:%s' % (user, host, uri_to),
    ]
    _call(cmd)


def _ensure_dir(uri_to, key, port, user, host):
    directory = os.path.dirname(uri_to)
    cmd = [
        'ssh',
        '-i', key,
        '-p', str(port),
    ] + SSH_OPTIONS + [
        '%s@%s' % (user, host),
        'mkdir', '-p', directory,
    ]
    _call(cmd)


def _call(cmd):
    exit_code = subprocess.check_call(cmd)
    if exit_code != 0:
        raise Exception("%s exited with code %s" % (cmd[0], exit_code))


___all__ = [
    'rsync_post_file',
    'rsync_get_file',
    'scp_post_file',
    'scp_get_file'
]
