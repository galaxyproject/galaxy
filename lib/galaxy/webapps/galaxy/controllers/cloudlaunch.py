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
from galaxy.util.json import to_json_string

eggs.require('boto')
import boto
import boto.vpc
from boto.ec2.regioninfo import RegionInfo
from boto.exception import EC2ResponseError, S3ResponseError
from boto.s3.connection import OrdinaryCallingFormat, S3Connection

log = logging.getLogger(__name__)

logging.getLogger('boto').setLevel(logging.INFO)


PKEY_PREFIX = 'gxy_pkey'
DEFAULT_KEYPAIR = 'cloudman_keypair'
CLOUDMAN_TAG_KEY = 'galaxy:cloudman'


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
                                   bucket_default=bucket_default)

    @web.expose
    def get_account_info(self, trans, key_id, secret):
        """
        Get EC2 Account Info
        """
        account_info = {}
        try:
            ec2_conn = connect_ec2(key_id, secret)
            kps = ec2_conn.get_all_key_pairs()
        except EC2ResponseError, e:
            log.error("Problem starting an instance: %s\n%s" % (e, e.body))
            trans.response.status = 400
            return e.error_message or "Error retrieving account information.  Please verify your credentials are correct, and contact galaxy support to report this issue."
        account_info['keypairs'] = [akp.name for akp in kps]
        #Existing Clusters
        s3_conn = S3Connection(key_id, secret, calling_format=OrdinaryCallingFormat())
        buckets = s3_conn.get_all_buckets()
        clusters = []
        for bucket in buckets:
            try:
                pd = bucket.get_key('persistent_data.yaml')
            except S3ResponseError, e:
                # This can fail for a number of reasons for non-us and/or CNAME'd buckets.
                log.error("Problem fetching persistent_data.yaml from bucket: %s \n%s" % (e, e.body))
                continue
            if pd:
                # This is a cloudman bucket.
                # We need to get persistent data, and the cluster name.
                # DBTODO: Add pyyaml egg, and rewrite this.
                # This will also allow for much more sophisticated rendering of existing clusters
                # Currently, this zone detection is a hack.
                pd_contents = pd.get_contents_as_string()
                zone = get_zone_from_pd(pd_contents, ec2_conn)
                for key in bucket.list():
                    if key.name.endswith('.clusterName'):
                        clusters.append({'name': key.name.split('.clusterName')[0],
                                         'persistent_data': pd_contents,
                                         'zone': zone})
        account_info['clusters'] = clusters
        account_info['zones'] = [z.name for z in ec2_conn.get_all_zones()]
        return to_json_string(account_info)

    @web.expose
    def launch_instance(self, trans, cluster_name, password, key_id, secret, instance_type, share_string, keypair, ami=None, zone=None, bucket_default=None, **kwargs):
        ec2_error = None
        try:
            # Create security group & key pair used when starting an instance
            ec2_conn = connect_ec2(key_id, secret)
            sg = get_or_create_cm_security_group(ec2_conn)
            kp_name, kp_material = create_key_pair(ec2_conn, key_name=keypair)
        except EC2ResponseError, err:
            ec2_error = err.error_message
        if ec2_error:
            trans.response.status = 400
            return ec2_error
        #Get an elastic ip, add to UserData.
        user_provided_data = _format_user_data(cluster_name, key_id, secret, password, share_string, bucket_default)
        if not ami:
            ami = trans.app.config.cloudlaunch_default_ami
        rs = _run_instance(ec2_conn=ec2_conn,
                           image_id=ami,
                           user_provided_data=user_provided_data,
                           key_name=kp_name,
                           security_group_ids=[sg.id],
                           placement=zone,
                           instance_type=instance_type,
                           subnet_id=get_or_create_cm_subnet(key_id, secret, zone).id)
        if not rs:
            trans.response.status = 400
            return "Instance failure, but no specific error was detected.  Please check your AWS Console."
        instance = rs.instances[0]
        while not instance.public_dns_name:
            try:
                instance.update()
            except EC2ResponseError:
                # This can happen when update is invoked before the instance is fully registered.
                pass
            time.sleep(1)
        if kp_material:
            #We have created a keypair.  Save to tempfile for one time retrieval.
            (fd, fname) = tempfile.mkstemp(prefix=PKEY_PREFIX, dir=trans.app.config.new_file_path)
            f = os.fdopen(fd, 'wt')
            f.write(kp_material)
            f.close()
            kp_material_tag = fname[fname.rfind(PKEY_PREFIX) + len(PKEY_PREFIX):]
        else:
            kp_material_tag = None
        return to_json_string({'cluster_name': cluster_name,
                               'instance_id': rs.instances[0].id,
                               'image_id': rs.instances[0].image_id,
                               'public_dns_name': rs.instances[0].public_dns_name,
                               'kp_name': kp_name,
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


def get_zone_from_pd(pd_contents, ec2_conn):
    try:
        for line in pd_contents.split('\n'):
            if 'vol_id' in line:
                vol_id = line.split(':')[1].strip()
                v = ec2_conn.get_all_volumes(volume_ids=[vol_id])
                if v:
                    return v[0].zone
    except:
        # Things can go wrong with Zone detection outside of our control.  Use
        # the default zone if this happens.
        pass
    return ''


def connect_ec2(a_key, s_key):
    """
    Create and return an EC2 connection object.
    """
    # Use variables for forward looking flexibility
    # AWS connection values
    region_name = 'us-east-1'
    region_endpoint = 'ec2.amazonaws.com'
    is_secure = True
    ec2_port = None
    ec2_conn_path = '/'
    r = RegionInfo(name=region_name, endpoint=region_endpoint)
    ec2_conn = boto.connect_ec2(aws_access_key_id=a_key,
                                aws_secret_access_key=s_key,
                                is_secure=is_secure,
                                region=r,
                                port=ec2_port,
                                path=ec2_conn_path)
    return ec2_conn


def get_or_create_cm_security_group(ec2_conn, sg_name='CloudManVPC'):
    """
    Create a security group with all authorizations required to run CloudMan.
    If the group already exists, check its rules and add the missing ones.
    Return the name of the created security group.
    """
    cm_sg = None
    # Check if this security group already exists.  We can't use the built-in
    # filtering here, because VPC security groups can't be filtered by name.
    sg = ec2_conn.get_all_security_groups(filters={'group_name': sg_name})
    if sg:
        cm_sg = sg[0]
    else:
        # If it does not exist, create security group
        log.debug("Creating Security Group %s" % sg_name)
        cm_sg = ec2_conn.create_security_group(sg_name, 'A security group for CloudMan', vpc_id=get_or_create_cm_vpc(ec2_conn.access_key, ec2_conn.secret_key).id)
    # Add appropriate authorization rules
    # If these rules already exist, nothing will be changed in the SG
    ports = (('80', '80'),  # Web UI
             ('20', '21'),  # FTP
             ('22', '22'),  # ssh
             ('30000', '30100'),  # FTP transfer
             ('42284', '42284'))  # CloudMan UI
    for port in ports:
        if not rule_exists(cm_sg.rules, from_port=port[0], to_port=port[1]):
            cm_sg.authorize(ip_protocol='tcp', from_port=port[0], to_port=port[1], cidr_ip='0.0.0.0/0')
        else:
            log.debug("Rule (%s:%s) already exists in the SG" % (port[0], port[1]))
    # Add rule that allows communication between instances in the same SG
    g_rule_exists = False  # Flag to indicate if group rule already exists
    for rule in cm_sg.rules:
        for grant in rule.grants:#[g for g in rule.grants if g.name == cm_sg.name]:
            print grant.name
            if grant.name == cm_sg.name:
                g_rule_exists = True
                log.debug("Group rule already exists in the SG")
        if g_rule_exists:
            break
    #if g_rule_exists is False:
    #    cm_sg.authorize(src_group=cm_sg)
    log.info("Done configuring '%s' security group" % cm_sg.name)
    return cm_sg



def get_or_create_cm_vpc(a_key, s_key):
    vpc_conn = boto.vpc.VPCConnection(a_key, s_key)
    vpcs = vpc_conn.get_all_vpcs()
    cloudman_vpc = None
    for vpc in vpcs:
        if CLOUDMAN_TAG_KEY in vpc.tags:
            cloudman_vpc = vpc
    if not cloudman_vpc:
        #create a new one.
        cloudman_vpc = vpc_conn.create_vpc('10.0.0.0/16')
        cloudman_vpc.add_tag(CLOUDMAN_TAG_KEY, '')
    return cloudman_vpc


def get_or_create_cm_subnet(a_key, s_key, availability_zone):
    log.debug("GETTING SUBNET in %s" % availability_zone)
    vpc_conn = boto.vpc.VPCConnection(a_key, s_key)
    subnets = vpc_conn.get_all_subnets()
    cloudman_subnet = None
    for subnet in subnets:
        log.debug("SN: %s, SNAZ:AZ: %s:%s:%s" % (subnet, subnet.availability_zone, availability_zone, subnet.availability_zone == availability_zone))
        if (not availability_zone or subnet.availability_zone == availability_zone) and CLOUDMAN_TAG_KEY in subnet.tags:
            cloudman_subnet = subnet
    if not cloudman_subnet:
        #create a new one.
        cloudman_subnet = vpc_conn.create_subnet(get_or_create_cm_vpc(a_key, s_key).id, '10.0.0.0/24', availability_zone)
        cloudman_subnet.add_tag(CLOUDMAN_TAG_KEY, '')
    return cloudman_subnet


def _format_user_data(cluster_name, key_id, secret, password, share_string, bucket_default):
    user_provided_data = {'cluster_name': cluster_name,
                          'access_key': key_id,
                          'secret_key': secret}
    if password:
        user_provided_data['password'] = password
    if share_string:
        user_provided_data['share_string'] = share_string
    if bucket_default:
        user_provided_data['bucket_default'] = bucket_default
    return "\n".join(['%s: %s' % (key, value) for key, value in user_provided_data.iteritems() if key != 'kp_material'])


def rule_exists(rules, from_port, to_port, ip_protocol='tcp', cidr_ip='0.0.0.0/0'):
    """ A convenience method to check if an authorization rule in a security
        group exists.
    """
    for rule in rules:
        if rule.ip_protocol == ip_protocol and rule.from_port == from_port and \
           rule.to_port == to_port and cidr_ip in [ip.cidr_ip for ip in rule.grants]:
            return True
    return False


def create_key_pair(ec2_conn, key_name=DEFAULT_KEYPAIR):
    """ Create a key pair with the provided name.
        Return the name of the key or None if there was an error creating the key.
    """
    kp = None
    # Check if a key pair under the given name already exists. If it does not,
    # create it, else return.
    kps = ec2_conn.get_all_key_pairs()
    for akp in kps:
        if akp.name == key_name:
            log.debug("Key pair '%s' already exists; not creating it again." % key_name)
            return akp.name, None
    try:
        kp = ec2_conn.create_key_pair(key_name)
    except EC2ResponseError, e:
        log.error("Problem creating key pair '%s': %s" % (key_name, e))
        return None, None
    return kp.name, kp.material


def _run_instance(ec2_conn, user_provided_data, instance_type, image_id=None,
                  kernel_id=None, ramdisk_id=None, key_name=DEFAULT_KEYPAIR,
                  placement=None, security_group_ids=None, subnet_id=None):
    """
    Start an instance. If instance start was OK, return the ResultSet object
    else return None.
    """
    rs = None
    try:
        rs = ec2_conn.run_instances(image_id=image_id,
                                    instance_type=instance_type,
                                    key_name=key_name,
                                    security_group_ids=security_group_ids,
                                    user_data=user_provided_data,
                                    kernel_id=kernel_id,
                                    subnet_id=subnet_id,
                                    ramdisk_id=ramdisk_id,
                                    placement=placement)
    except EC2ResponseError, e:
        log.error("Problem starting an instance: %s\n%s" % (e, e.body))
    if rs:
        try:
            log.info("Started an instance with ID %s" % rs.instances[0].id)
        except Exception, e:
            log.error("Problem with the started instance object: %s" % e)
    else:
        log.warning("Problem starting an instance?")
    return rs
