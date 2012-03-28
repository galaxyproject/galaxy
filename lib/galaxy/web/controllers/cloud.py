"""
Cloud Controller: handles all cloud interactions.

Adapted from Brad Chapman and Enis Afgan's BioCloudCentral
BioCloudCentral Source: https://github.com/chapmanb/biocloudcentral

"""

import datetime
import logging
import time
from galaxy import eggs
import pkg_resources
pkg_resources.require('boto')
import boto
from galaxy import web
from galaxy.web.base.controller import BaseUIController
from boto.ec2.regioninfo import RegionInfo
from boto.exception import EC2ResponseError

log = logging.getLogger(__name__)

class CloudController(BaseUIController):
    def __init__(self, app):
        BaseUIController.__init__(self, app)

    @web.expose
    def index(self, trans):
        return trans.fill_template("cloud/index.mako")

    @web.expose
    def launch_instance(self, trans, cluster_name, password, key_id, secret, instance_type):
        ec2_error = None
        try:
            # Create security group & key pair used when starting an instance
            ec2_conn = connect_ec2(key_id, secret)
            sg_name = create_cm_security_group(ec2_conn)
            kp_name, kp_material = create_key_pair(ec2_conn)
        except EC2ResponseError, err:
            ec2_error = err.error_message
        if ec2_error:
            return trans.fill_template("cloud/run.mako", error = ec2_error)
        else:
            rs = run_instance(ec2_conn=ec2_conn,
                      user_provided_data={'cluster_name':cluster_name,
                                        'password':password,
                                        'access_key':key_id,
                                        'secret_key':secret,
                                        'instance_type':instance_type},
                      key_name=kp_name,
                      security_groups=[sg_name])
            if rs:
                instance = rs.instances[0]
                ct = 0
                while not instance.public_dns_name:
                    # Can take a second to have public dns name registered.
                    # DBTODO, push this into a page update, this is not ideal.
                    instance.update()
                    ct +=1
                    time.sleep(1)
                return trans.fill_template("cloud/run.mako",
                                            instance = rs.instances[0],
                                            kp_name = kp_name,
                                            kp_material = kp_material)
            else:
                return trans.fill_template("cloud/run.mako",
                        error = "Instance failure, but no specific error was detected.  Please check your AWS Console.")

# ## Cloud interaction methods
def connect_ec2(a_key, s_key):
    """ Create and return an EC2 connection object.
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
                          api_version='2011-11-01', # needed for availability zone support
                          is_secure=is_secure,
                          region=r,
                          port=ec2_port,
                          path=ec2_conn_path)
    return ec2_conn

def create_cm_security_group(ec2_conn, sg_name='CloudMan'):
    """ Create a security group with all authorizations required to run CloudMan.
        If the group already exists, check its rules and add the missing ones.
        Return the name of the created security group.
    """
    cmsg = None
    # Check if this security group already exists
    sgs = ec2_conn.get_all_security_groups()
    for sg in sgs:
        if sg.name == sg_name:
            cmsg = sg
            log.debug("Security group '%s' already exists; will add authorizations next." % sg_name)
            break
    # If it does not exist, create security group
    if cmsg is None:
        log.debug("Creating Security Group %s" % sg_name)
        cmsg = ec2_conn.create_security_group(sg_name, 'A security group for CloudMan')
    # Add appropriate authorization rules
    # If these rules already exist, nothing will be changed in the SG
    ports = (('80', '80'), # Web UI
             ('20', '21'), # FTP
             ('22', '22'), # ssh
             ('30000', '30100'), # FTP transfer
             ('42284', '42284')) # CloudMan UI
    for port in ports:
        try:
            if not rule_exists(cmsg.rules, from_port=port[0], to_port=port[1]):
                cmsg.authorize(ip_protocol='tcp', from_port=port[0], to_port=port[1], cidr_ip='0.0.0.0/0')
            else:
                log.debug("Rule (%s:%s) already exists in the SG" % (port[0], port[1]))
        except EC2ResponseError, e:
            log.error("A problem with security group authorizations: %s" % e)
    # Add rule that allows communication between instances in the same SG
    g_rule_exists = False # Flag to indicate if group rule already exists
    for rule in cmsg.rules:
        for grant in rule.grants:
            if grant.name == cmsg.name:
                g_rule_exists = True
                log.debug("Group rule already exists in the SG")
        if g_rule_exists:
            break
    if g_rule_exists is False:
        try:
            cmsg.authorize(src_group=cmsg)
        except EC2ResponseError, e:
            log.error("A problem w/ security group authorization: %s" % e)
    log.info("Done configuring '%s' security group" % cmsg.name)
    return cmsg.name

def rule_exists(rules, from_port, to_port, ip_protocol='tcp', cidr_ip='0.0.0.0/0'):
    """ A convenience method to check if an authorization rule in a security
        group exists.
    """
    for rule in rules:
        if rule.ip_protocol == ip_protocol and rule.from_port == from_port and \
           rule.to_port == to_port and cidr_ip in [ip.cidr_ip for ip in rule.grants]:
            return True
    return False

def create_key_pair(ec2_conn, key_name='cloudman_key_pair'):
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

def run_instance(ec2_conn, user_provided_data, image_id='ami-da58aab3',
                 kernel_id=None, ramdisk_id=None, key_name='cloudman_key_pair',
                 security_groups=['CloudMan']):
    """ Start an instance. If instance start was OK, return the ResultSet object
        else return None.
    """
    rs = None
    instance_type = user_provided_data['instance_type']
    # Remove 'instance_type' key from the dict before creating user data
    del user_provided_data['instance_type']
    placement = _find_placement(ec2_conn, instance_type)
    ud = "\n".join(['%s: %s' % (key, value) for key, value in user_provided_data.iteritems() if key != 'kp_material'])
    try:
        rs = ec2_conn.run_instances(image_id=image_id,
                                    instance_type=instance_type,
                                    key_name=key_name,
                                    security_groups=security_groups,
                                    user_data=ud,
                                    kernel_id=kernel_id,
                                    ramdisk_id=ramdisk_id,
                                    placement=placement)
    except EC2ResponseError, e:
        log.error("Problem starting an instance: %s" % e)
    if rs:
        try:
            log.info("Started an instance with ID %s" % rs.instances[0].id)
        except Exception, e:
            log.error("Problem with the started instance object: %s" % e)
    else:
        log.warning("Problem starting an instance?")
    return rs

def _find_placement(ec2_conn, instance_type):
    """Find a region zone that supports our requested instance type.

    We need to check spot prices in the potential availability zones
    for support before deciding on a region:

    http://blog.piefox.com/2011/07/ec2-availability-zones-and-instance.html
    """
    base = ec2_conn.region.name
    yesterday = datetime.datetime.now() - datetime.timedelta(1)
    for loc_choice in ["b", "a", "c", "d"]:
        cur_loc = "{base}{ext}".format(base=base, ext=loc_choice)
        if len(ec2_conn.get_spot_price_history(instance_type=instance_type,
                                               end_time=yesterday.isoformat(),
                                               availability_zone=cur_loc)) > 0:
            return cur_loc
    log.error("Did not find availabilty zone in {0} for {1}".format(base, instance_type))
    return None

