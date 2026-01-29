"""Stock job 'dynamic' rules for use in the job config file - these may cover some
simple use cases but will just proxy into functions in rule_helper so similar
functionality - but more tailored and composable can be utilized in custom
rules.
"""

from galaxy import util


def choose_one(rule_helper, job, destination_ids, hash_by="job"):
    destination_id_list = util.listify(destination_ids)
    job_hash = rule_helper.job_hash(job, hash_by)
    return rule_helper.choose_one(destination_id_list, hash_value=job_hash)


def burst(rule_helper, job, from_destination_ids, to_destination_id, num_jobs, job_states=None):
    from_destination_ids = util.listify(from_destination_ids)
    if rule_helper.should_burst(from_destination_ids, num_jobs=num_jobs, job_states=job_states):
        return to_destination_id
    else:
        return from_destination_ids[0]


def docker_dispatch(rule_helper, tool, docker_destination_id, default_destination_id):
    return docker_destination_id if rule_helper.supports_docker(tool) else default_destination_id
