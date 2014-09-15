"""
Cloud Controller: handles all cloud interactions.

Adapted from Brad Chapman and Enis Afgan's BioCloudCentral
BioCloudCentral Source: https://github.com/chapmanb/biocloudcentral
"""

import logging
import os
import tempfile
import time

from galaxy import eggs
from galaxy import web
from galaxy.web.base.controller import BaseUIController
from galaxy.util.json import dumps

eggs.require('PyYAML')
eggs.require('boto')
eggs.require('bioblend')

from boto.exception import EC2ResponseError


from bioblend import cloudman

log = logging.getLogger(__name__)


PKEY_PREFIX = 'gxy_pkey'
DEFAULT_KEYPAIR = 'cloudman_keypair'
CLOUDMAN_TAG_KEY = 'galaxy:cloudman'

DEFAULT_INSTANCE_TYPES = [
    ("c3.large", "Compute optimized Large (2 vCPU/4GB RAM)"),
    ("c3.2xlarge", "Compute optimized 2xLarge (8 vCPU/15GB RAM)"),
    ("c3.8xlarge", "Compute optimized 8xLarge (32 vCPU/60GB RAM)"),
    ("r3.large", "Memory optimized Large (2 vCPU/15GB RAM)"),
    ("r3.2xlarge", "Memory optimized 2xLarge (8 vCPU/61GB RAM)"),
    ("r3.8xlarge", "Memory optimized 8xLarge (32 vCPU/244GB RAM)"),
]


class CloudController(BaseUIController):
    """Galaxy Cloud Functions"""

    def __init__(self, app):
        BaseUIController.__init__(self, app)

    @web.expose
    def index(self, trans, share_string=None, ami=None, bucket_default=None):
        """
        Serves the default page requesting AWS keys
        """
        return trans.fill_template("cloud/index.mako",
                                   default_keypair=DEFAULT_KEYPAIR,
                                   share_string=share_string,
                                   ami=ami,
                                   bucket_default=bucket_default,
                                   instance_types=DEFAULT_INSTANCE_TYPES)

    @web.expose
    def get_account_info(self, trans, key_id, secret):
        """
        Get EC2 Account Info
        """
        account_info = {}
        cml = cloudman.launch.CloudManLauncher(key_id, secret)
        ec2_conn = cml.connect_ec2(key_id, secret)
        kps = ec2_conn.get_all_key_pairs()
        account_info['clusters'] = cml.get_clusters_pd()
        account_info['keypairs'] = [akp.name for akp in kps]
        return dumps(account_info)

    @web.expose
    def launch_instance(self, trans, cluster_name, password, key_id, secret,
                        instance_type, share_string, keypair, ami=None,
                        zone=None, bucket_default=None, **kwargs):
        ami = ami or trans.app.config.cloudlaunch_default_ami
        cfg = cloudman.CloudManConfig(key_id, secret, cluster_name, ami,
                                      instance_type, password, placement=zone)
        cml = cloudman.launch.CloudManLauncher(key_id, secret)
        # This should probably be handled better on the bioblend side, but until
        # an egg update can be made, this needs to conditionally include the
        # parameter or not, even if the value is None.
        if bucket_default:
            result = cml.launch(cluster_name, ami, instance_type, password,
                                cfg.kernel_id, cfg.ramdisk_id, cfg.key_name,
                                cfg.security_groups, cfg.placement,
                                bucket_default=bucket_default)
        else:
            result = cml.launch(cluster_name, ami, instance_type, password,
                                cfg.kernel_id, cfg.ramdisk_id, cfg.key_name,
                                cfg.security_groups, cfg.placement)
        # result is a dict with sg_names, kp_name, kp_material, rs, and instance_id
        if not result['rs']:
            trans.response.status = 400
            return "Instance failure, but no specific error was detected.  Please check your AWS Console."
        instance = result['rs'].instances[0]
        while not instance.public_dns_name:
            try:
                instance.update()
            except EC2ResponseError:
                # This can happen when update is invoked before the instance is fully registered.
                pass
            time.sleep(1)
        if result['kp_material']:
            # We have created a keypair.  Save to tempfile for one time retrieval.
            (fd, fname) = tempfile.mkstemp(prefix=PKEY_PREFIX, dir=trans.app.config.new_file_path)
            f = os.fdopen(fd, 'wt')
            f.write(result['kp_material'])
            f.close()
            kp_material_tag = fname[fname.rfind(PKEY_PREFIX) + len(PKEY_PREFIX):]
        else:
            kp_material_tag = None
        return dumps({'cluster_name': cluster_name,
                               'instance_id': result['rs'].instances[0].id,
                               'image_id': result['rs'].instances[0].image_id,
                               'public_dns_name': result['rs'].instances[0].public_dns_name,
                               'kp_name': result['kp_name'],
                               'kp_material_tag': kp_material_tag})

    @web.expose
    def get_pkey(self, trans, kp_material_tag=None):
        if kp_material_tag:
            expected_path = os.path.join(trans.app.config.new_file_path, PKEY_PREFIX + kp_material_tag)
            if os.path.exists(expected_path):
                f = open(expected_path)
                kp_material = f.read()
                f.close()
                trans.response.headers['Content-Length'] = int( os.stat( expected_path ).st_size )
                trans.response.set_content_type( "application/octet-stream" )  # force octet-stream so Safari doesn't append mime extensions to filename
                trans.response.headers["Content-Disposition"] = 'attachment; filename="%s.pem"' % DEFAULT_KEYPAIR
                os.remove(expected_path)
                return kp_material
        trans.response.status = 400
        return "Invalid identifier"
