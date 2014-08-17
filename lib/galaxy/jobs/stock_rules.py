""" Stock job 'dynamic' rules for use in job_conf.xml - these may cover some
simple use cases but will just proxy into functions in rule_helper so similar
functionality - but more tailored and composable can be utilized in custom
rules.
"""

from galaxy import util


def choose_one( rule_helper, job, destination_ids, hash_by="job" ):
    destination_id_list = util.listify( destination_ids )
    job_hash = rule_helper.job_hash( job, hash_by )
    return rule_helper.choose_one( destination_id_list, hash_value=job_hash )
