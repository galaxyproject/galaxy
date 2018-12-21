import re
import traceback
from logging import getLogger

from galaxy.tools.parser.error_level import StdioErrorLevel
from galaxy.util import unicodify
from galaxy.util.bunch import Bunch

log = getLogger(__name__)

DETECTED_JOB_STATE = Bunch(
    OK='ok',
    OUT_OF_MEMORY_ERROR='oom_error',
    GENERIC_ERROR='generic_error',
)


ERROR_PEAK = 2000


def check_output(tool, stdout, stderr, tool_exit_code, job):
    """
    Check the output of a tool - given the stdout, stderr, and the tool's
    exit code, return DETECTED_JOB_STATE.OK if the tool exited succesfully or
    error type otherwise. No exceptions should be thrown. If this code encounters
    an exception, it returns OK so that the workflow can continue;
    otherwise, a bug in this code could halt workflow progress.

    Note that, if the tool did not define any exit code handling or
    any stdio/stderr handling, then it reverts back to previous behavior:
    if stderr contains anything, then False is returned.
    """
    # By default, the tool succeeded. This covers the case where the code
    # has a bug but the tool was ok, and it lets a workflow continue.
    state = DETECTED_JOB_STATE.OK

    stdout = unicodify(stdout)
    stderr = unicodify(stderr)

    try:
        # Check exit codes and match regular expressions against stdout and
        # stderr if this tool was configured to do so.
        # If there is a regular expression for scanning stdout/stderr,
        # then we assume that the tool writer overwrote the default
        # behavior of just setting an error if there is *anything* on
        # stderr.
        if len(tool.stdio_regexes) > 0 or len(tool.stdio_exit_codes) > 0:
            # Check the exit code ranges in the order in which
            # they were specified. Each exit_code is a StdioExitCode
            # that includes an applicable range. If the exit code was in
            # that range, then apply the error level and add a message.
            # If we've reached a fatal error rule, then stop.
            max_error_level = StdioErrorLevel.NO_ERROR
            if tool_exit_code is not None:
                for stdio_exit_code in tool.stdio_exit_codes:
                    if (tool_exit_code >= stdio_exit_code.range_start and
                            tool_exit_code <= stdio_exit_code.range_end):
                        # Tack on a generic description of the code
                        # plus a specific code description. For example,
                        # this might prepend "Job 42: Warning (Out of Memory)\n".
                        code_desc = stdio_exit_code.desc
                        if None is code_desc:
                            code_desc = ""
                        tool_msg = ("%s: Exit code %d (%s)" % (
                            StdioErrorLevel.desc(stdio_exit_code.error_level),
                            tool_exit_code,
                            code_desc))
                        log.info("Job %s: %s" % (job.get_id_tag(), tool_msg))
                        stderr = tool_msg + "\n" + stderr
                        max_error_level = max(max_error_level,
                                              stdio_exit_code.error_level)
                        if max_error_level >= StdioErrorLevel.MAX:
                            break

            if max_error_level < StdioErrorLevel.FATAL:
                # We'll examine every regex. Each regex specifies whether
                # it is to be run on stdout, stderr, or both. (It is
                # possible for neither stdout nor stderr to be scanned,
                # but those regexes won't be used.) We record the highest
                # error level, which are currently "warning" and "fatal".
                # If fatal, then we set the job's state to ERROR.
                # If warning, then we still set the job's state to OK
                # but include a message. We'll do this if we haven't seen
                # a fatal error yet
                for regex in tool.stdio_regexes:
                    # If ( this regex should be matched against stdout )
                    #   - Run the regex's match pattern against stdout
                    #   - If it matched, then determine the error level.
                    #       o If it was fatal, then we're done - break.
                    # Repeat the stdout stuff for stderr.
                    # TODO: Collapse this into a single function.
                    if regex.stdout_match:
                        regex_match = re.search(regex.match, stdout,
                                                re.IGNORECASE)
                        if regex_match:
                            rexmsg = __regex_err_msg(regex_match, regex)
                            log.info("Job %s: %s"
                                     % (job.get_id_tag(), rexmsg))
                            stdout = rexmsg + "\n" + stdout
                            max_error_level = max(max_error_level,
                                                  regex.error_level)
                            if max_error_level >= StdioErrorLevel.FATAL:
                                break

                    if regex.stderr_match:
                        regex_match = re.search(regex.match, stderr,
                                                re.IGNORECASE)
                        if regex_match:
                            rexmsg = __regex_err_msg(regex_match, regex)
                            log.info("Job %s: %s"
                                     % (job.get_id_tag(), rexmsg))
                            stderr = rexmsg + "\n" + stderr
                            max_error_level = max(max_error_level,
                                                  regex.error_level)
                            if max_error_level >= StdioErrorLevel.FATAL:
                                break

            # If we encountered a fatal error, then we'll need to set the
            # job state accordingly. Otherwise the job is ok:
            if max_error_level == StdioErrorLevel.FATAL_OOM:
                state = DETECTED_JOB_STATE.OUT_OF_MEMORY_ERROR
            elif max_error_level >= StdioErrorLevel.FATAL:
                log.debug("Tool exit code indicates an error, failing job.")
                state = DETECTED_JOB_STATE.GENERIC_ERROR
            else:
                state = DETECTED_JOB_STATE.OK

        # When there are no regular expressions and no exit codes to check,
        # default to the previous behavior: when there's anything on stderr
        # the job has an error, and the job is ok otherwise.
        else:
            # TODO: Add in the tool and job id:
            # log.debug( "Tool did not define exit code or stdio handling; "
            #          + "checking stderr for success" )
            if stderr:
                state = DETECTED_JOB_STATE.GENERIC_ERROR
            else:
                state = DETECTED_JOB_STATE.OK

        if DETECTED_JOB_STATE != DETECTED_JOB_STATE.OK and stderr:
            if stderr:
                peak = stderr[0:ERROR_PEAK]
                log.debug("job failed, standard error is - [%s]" % peak)

    # On any exception, return True.
    except Exception:
        tb = traceback.format_exc()
        log.warning("Tool check encountered unexpected exception; " +
                    "assuming tool was successful: " + tb)
        state = DETECTED_JOB_STATE.OK

    # Store the modified stdout and stderr in the job:
    if job is not None:
        job.set_streams(stdout, stderr)

    return state


def __regex_err_msg(match, regex):
    """
    Return a message about the match on tool output using the given
    ToolStdioRegex regex object. The regex_match is a MatchObject
    that will contain the string matched on.
    """
    # Get the description for the error level:
    err_msg = StdioErrorLevel.desc(regex.error_level) + ": "
    # If there's a description for the regular expression, then use it.
    # Otherwise, we'll take the first 256 characters of the match.
    if None is not regex.desc:
        err_msg += regex.desc
    else:
        mstart = match.start()
        mend = match.end()
        err_msg += "Matched on "
        # TODO: Move the constant 256 somewhere else besides here.
        if mend - mstart > 256:
            err_msg += match.string[mstart : mstart + 256] + "..."
        else:
            err_msg += match.string[mstart: mend]
    return err_msg
