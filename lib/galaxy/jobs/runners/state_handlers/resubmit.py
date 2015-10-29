import logging

__all__ = ['failure']

log = logging.getLogger(__name__)

MESSAGES = dict(
    walltime_reached='it reached the walltime',
    memory_limit_reached='it exceeded the amount of allocated memory'
)


def failure(app, job_runner, job_state):
    runner_state = getattr(job_state, 'runner_state', None)
    if (not runner_state or
        runner_state not in (job_state.runner_states.WALLTIME_REACHED,
                             job_state.runner_states.MEMORY_LIMIT_REACHED)):
        # not set or not a handleable runner state
        return
    # Intercept jobs that hit the walltime and have a walltime or
    # nonspecific resubmit destination configured
    for resubmit in job_state.job_destination.get('resubmit'):
        condition = resubmit.get('condition', None)
        if condition and condition != runner_state:
            # There is a resubmit defined for the destination but
            # its condition is not for the encountered state
            continue
        log.info("(%s/%s) Job will be resubmitted to '%s' because %s at "
                 "the '%s' destination",
                 job_state.job_wrapper.job_id,
                 job_state.job_id,
                 resubmit['destination'],
                 MESSAGES[job_state.runner_state],
                 job_state.job_wrapper.job_destination.id )
        # fetch JobDestination for the id or tag
        new_destination = app.job_config.get_destination(
            resubmit['destination'])
        # Resolve dynamic if necessary
        new_destination = (job_state.job_wrapper.job_runner_mapper
                           .cache_job_destination(new_destination))
        # Reset job state
        job_state.job_wrapper.clear_working_directory()
        job_state.job_wrapper.invalidate_external_metadata()
        job = job_state.job_wrapper.get_job()
        if resubmit.get('handler', None):
            log.debug('(%s/%s) Job reassigned to handler %s',
                      job_state.job_wrapper.job_id, job_state.job_id,
                      resubmit['handler'])
            job.set_handler(resubmit['handler'])
            job_runner.sa_session.add( job )
            # Is this safe to do here?
            job_runner.sa_session.flush()
        # Cache the destination to prevent rerunning dynamic after
        # resubmit
        job_state.job_wrapper.job_runner_mapper \
            .cached_job_destination = new_destination
        job_state.job_wrapper.set_job_destination(new_destination)
        # Clear external ID (state change below flushes the change)
        job.job_runner_external_id = None
        # Allow the UI to query for resubmitted state
        if job.params is None:
            job.params = {}
        job_state.runner_state_handled = True
        info = "This job was resubmitted to the queue because %s on its " \
               "compute resource." % MESSAGES[job_state.runner_state]
        job_runner.mark_as_resubmitted(job_state, info=info)
        return
