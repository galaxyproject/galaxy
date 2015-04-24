/***************************Copyright-DO-NOT-REMOVE-THIS-LINE**
 * CONDOR Copyright Notice
 *
 * See LICENSE.TXT for additional notices and disclaimers.
 *
 * Copyright (c)1990-2001 CONDOR Team, Computer Sciences Department, 
 * University of Wisconsin-Madison, Madison, WI.  All Rights Reserved.  
 * No use of the CONDOR Software Program Source Code is authorized 
 * without the express consent of the CONDOR Team.  For more information 
 * contact: CONDOR Team, Attention: Professor Miron Livny, 
 * 7367 Computer Sciences, 1210 W. Dayton St., Madison, WI 53706-1685, 
 * (608) 262-0856 or miron@cs.wisc.edu.
 *
 * U.S. Government Rights Restrictions: Use, duplication, or disclosure 
 * by the U.S. Government is subject to restrictions as set forth in 
 * subparagraph (c)(1)(ii) of The Rights in Technical Data and Computer 
 * Software clause at DFARS 252.227-7013 or subparagraphs (c)(1) and 
 * (2) of Commercial Computer Software-Restricted Rights at 48 CFR 
 * 52.227-19, as applicable, CONDOR Team, Attention: Professor Miron 
 * Livny, 7367 Computer Sciences, 1210 W. Dayton St., Madison, 
 * WI 53706-1685, (608) 262-0856 or miron@cs.wisc.edu.
 ****************************Copyright-DO-NOT-REMOVE-THIS-LINE**/

#ifndef __DRMAA_H
#define __DRMAA_H

#ifdef WIN32
#define DLL_IMPORT_MAGIC __declspec(dllimport)
#define DLL_EXPORT_MAGIC __declspec(dllexport)
#ifdef DRMAA_DLL
#define DLL_MAGIC DLL_EXPORT_MAGIC
#else
#define DLL_MAGIC DLL_IMPORT_MAGIC
#endif
 
#else
#define DLL_MAGIC  /* a no-op on Unix */
#endif

#ifdef __cplusplus
extern "C"
{
#endif

/* ------------------- Constants ------------------- */
/*
 * Agreed buffer length constants
 * these are recommended minimum values
 */
#define DRMAA_ATTR_BUFFER 1024
#define DRMAA_CONTACT_BUFFER 1024
#define DRMAA_DRM_SYSTEM_BUFFER 1024
#define DRMAA_DRMAA_IMPLEMENTATION_BUFFER 1024
#define DRMAA_ERROR_STRING_BUFFER 1024
#define DRMAA_JOBNAME_BUFFER 1024
#define DRMAA_SIGNAL_BUFFER 32

/*
 * Agreed constants
 */
#define DRMAA_TIMEOUT_WAIT_FOREVER -1
#define DRMAA_TIMEOUT_NO_WAIT 0

#define DRMAA_JOB_IDS_SESSION_ANY "DRMAA_JOB_IDS_SESSION_ANY"
#define DRMAA_JOB_IDS_SESSION_ALL "DRMAA_JOB_IDS_SESSION_ALL"

#define DRMAA_SUBMISSION_STATE_ACTIVE "drmaa_active"
#define DRMAA_SUBMISSION_STATE_HOLD "drmaa_hold"

/*
 * Agreed placeholder names
 */
#define DRMAA_PLACEHOLDER_INCR "$drmaa_incr_ph$"
#define DRMAA_PLACEHOLDER_HD "$drmaa_hd_ph$"
#define DRMAA_PLACEHOLDER_WD "$drmaa_wd_ph$"

/*
 * Agreed names of job template attributes
 */
#define DRMAA_REMOTE_COMMAND "drmaa_remote_command"
#define DRMAA_JS_STATE "drmaa_js_state"
#define DRMAA_WD "drmaa_wd"
#define DRMAA_JOB_CATEGORY "drmaa_job_category"
#define DRMAA_NATIVE_SPECIFICATION "drmaa_native_specification"
#define DRMAA_BLOCK_EMAIL "drmaa_block_email"
#define DRMAA_START_TIME "drmaa_start_time"
#define DRMAA_JOB_NAME "drmaa_job_name"
#define DRMAA_INPUT_PATH "drmaa_input_path"
#define DRMAA_OUTPUT_PATH "drmaa_output_path"
#define DRMAA_ERROR_PATH "drmaa_error_path"
#define DRMAA_JOIN_FILES "drmaa_join_files"
#define DRMAA_TRANSFER_FILES "drmaa_transfer_files"
#define DRMAA_DEADLINE_TIME "drmaa_deadline_time"
#define DRMAA_WCT_HLIMIT "drmaa_wct_hlimit"
#define DRMAA_WCT_SLIMIT "drmaa_wct_slimit"
#define DRMAA_DURATION_HLIMIT "drmaa_duration_hlimit"
#define DRMAA_DURATION_SLIMIT "drmaa_duration_slimit"

/*
 * Agreed names of job template vector attributes
 */
#define DRMAA_V_ARGV "drmaa_v_argv"
#define DRMAA_V_ENV "drmaa_v_env"
#define DRMAA_V_EMAIL "drmaa_v_email"

/*
 * Agreed DRMAA errno values
 *
 * Note: The order in the enum is significant!
 */
  enum
  {
    /* ------------- these are relevant to all sections -------------- */
    DRMAA_ERRNO_SUCCESS = 0,
    DRMAA_ERRNO_INTERNAL_ERROR,
    DRMAA_ERRNO_DRM_COMMUNICATION_FAILURE,
    DRMAA_ERRNO_AUTH_FAILURE,
    DRMAA_ERRNO_INVALID_ARGUMENT,
    DRMAA_ERRNO_NO_ACTIVE_SESSION,
    DRMAA_ERRNO_NO_MEMORY,
    /* -------------- init and exit specific --------------- */
    DRMAA_ERRNO_INVALID_CONTACT_STRING,
    DRMAA_ERRNO_DEFAULT_CONTACT_STRING_ERROR,
    DRMAA_ERRNO_NO_DEFAULT_CONTACT_STRING_SELECTED,
    DRMAA_ERRNO_DRMS_INIT_FAILED,
    DRMAA_ERRNO_ALREADY_ACTIVE_SESSION,
    DRMAA_ERRNO_DRMS_EXIT_ERROR,
    /* ---------------- job attributes specific -------------- */
    DRMAA_ERRNO_INVALID_ATTRIBUTE_FORMAT,
    DRMAA_ERRNO_INVALID_ATTRIBUTE_VALUE,
    DRMAA_ERRNO_CONFLICTING_ATTRIBUTE_VALUES,
    /* --------------------- job submission specific -------------- */
    DRMAA_ERRNO_TRY_LATER,
    DRMAA_ERRNO_DENIED_BY_DRM,
    /* ------------------------- job control specific -------------- */
    DRMAA_ERRNO_INVALID_JOB,
    DRMAA_ERRNO_RESUME_INCONSISTENT_STATE,
    DRMAA_ERRNO_SUSPEND_INCONSISTENT_STATE,
    DRMAA_ERRNO_HOLD_INCONSISTENT_STATE,
    DRMAA_ERRNO_RELEASE_INCONSISTENT_STATE,
    DRMAA_ERRNO_EXIT_TIMEOUT,
    DRMAA_ERRNO_NO_RUSAGE,
    DRMAA_ERRNO_NO_MORE_ELEMENTS
  };

/*
 * Agreed DRMAA job states as returned by drmaa_job_ps()
 */
  enum
  {
    DRMAA_PS_UNDETERMINED = 0x00,
    DRMAA_PS_QUEUED_ACTIVE = 0x10,
    DRMAA_PS_SYSTEM_ON_HOLD = 0x11,
    DRMAA_PS_USER_ON_HOLD = 0x12,
    DRMAA_PS_USER_SYSTEM_ON_HOLD = 0x13,
    DRMAA_PS_RUNNING = 0x20,
    DRMAA_PS_SYSTEM_SUSPENDED = 0x21,
    DRMAA_PS_USER_SUSPENDED = 0x22,
    DRMAA_PS_USER_SYSTEM_SUSPENDED = 0x23,
    DRMAA_PS_DONE = 0x30,
    DRMAA_PS_FAILED = 0x40
  };

/*
 * Agreed DRMAA actions for drmaa_control()
 */
  enum
  {
    DRMAA_CONTROL_SUSPEND = 0,
    DRMAA_CONTROL_RESUME,
    DRMAA_CONTROL_HOLD,
    DRMAA_CONTROL_RELEASE,
    DRMAA_CONTROL_TERMINATE
  };

/* ------------------- Data types ------------------- */
/*
 * Agreed opaque DRMAA job template type
 * struct drmaa_job_template_s is defined elsewhere
 */
  typedef struct drmaa_job_template_s drmaa_job_template_t;

/* ---------- C/C++ language binding specific interfaces -------- */
  typedef struct drmaa_attr_names_s drmaa_attr_names_t;
  typedef struct drmaa_attr_values_s drmaa_attr_values_t;
  typedef struct drmaa_job_ids_s drmaa_job_ids_t;

/*
 * get next string attribute from string vector
 *
 * returns DRMAA_ERRNO_SUCCESS or DRMAA_ERRNO_INVALID_ATTRIBUTE_VALUE
 * if no such exists
 */
  DLL_MAGIC int drmaa_get_next_attr_name (drmaa_attr_names_t * values, char *value, size_t value_len);
  DLL_MAGIC int drmaa_get_next_attr_value (drmaa_attr_values_t * values, char *value,
				 size_t value_len);
  DLL_MAGIC int drmaa_get_next_job_id (drmaa_job_ids_t * values, char *value,
			     size_t value_len);

/*
 * release opaque string vector
 *
 * Opaque string vectors can be used without any constraint
 * until the release function has been called.
 */
  DLL_MAGIC void drmaa_release_attr_names (drmaa_attr_names_t * values);
  DLL_MAGIC void drmaa_release_attr_values (drmaa_attr_values_t * values);
  DLL_MAGIC void drmaa_release_job_ids (drmaa_job_ids_t * values);

/* ------------------- init/exit routines ------------------- */
/** Initialize the DRMAA API library and create a new DRMAA session.
    This routine must be called before any other calls to this library,
    except for drmaa_version().  Only one DRMAA session may be open at a time.
    @param contact NULL
    @param drmaa_context_error_buf contains a context sensitive error upon
           fail returned
    @return one of the general error codes or one of the following:
            DRMAA_ERRNO_INVALID_CONTACT_STRING
	    DRMAA_ERRNO_ALREADY_ACTIVE_SESSION
	    DRMAA_ERRNO_NO_DEFAULT_CONTACT_STRING_SELECTED
	    DRMAA_ERRNO_DEFAULT_CONTACT_STRING_ERROR
*/
  DLL_MAGIC int drmaa_init (const char *contact, char *error_diagnosis,
		  size_t error_diag_len);

/** Disengage from the DRMAA library, ending the current session.
    @param drmaa_context_error_buf contains a context sensitive error upon
           fail returned
    @return one of the general error codes or one of the following:
	    DRMAA_ERRNO_DRMS_EXIT_ERROR
	    DRMAA_ERRNO_NO_ACTIVE_SESSION
*/
  DLL_MAGIC int drmaa_exit (char *error_diagnosis, size_t error_diag_len);

/* ------------------- job template routines ------------------- */
/** Allocate a new job template
    @param jt new job template
    @param drmaa_context_error_buf contains a context sensitive error upon
           fail returned
    @return one of the general error codes or one of the following:
	    DRMAA_ERRNO_DRM_COMMUNICATION_FAILURE
*/
  DLL_MAGIC int drmaa_allocate_job_template (drmaa_job_template_t ** jt,
				   char *error_diagnosis,
				   size_t error_diag_len);

/** Deallocates a job template.
    @param jt job template to delete
    @param drmaa_context_error_buf contains a context sensitive error upon
           fail returned
    @return one of the general error codes or one of the following:
	    DRMAA_ERRNO_DRM_COMMUNICATION_FAILURE
*/
  DLL_MAGIC int drmaa_delete_job_template (drmaa_job_template_t * jt,
				 char *error_diagnosis,
				 size_t error_diag_len);

/** Sets the attribute to the given value in the given job template
    @param jt job template
    @param name name of attribute
    @param value value of attribute
    @param drmaa_context_error_buf contains a context sensitive error upon
           fail returned
    @return one of the general error codes or one of the following:
	    DRMAA_ERRNO_INVALID_ATTRIBUTE_FORMAT
	    DRMAA_ERRNO_INVALID_ATTRIBUTE_VALUE
	    DRMAA_ERRNO_CONFLICTING_ATTRIBUTE_VALUES
*/
  DLL_MAGIC int drmaa_set_attribute (drmaa_job_template_t * jt, const char *name,
			   const char *value, char *error_diagnosis,
			   size_t error_diag_len);

/** Retrieves the value of a given attribute from a given job template.
    @param jt job template
    @param name name of attribute
    @param value will be filled with the value of the attribute in jt
    @param error_diagnosis contains a context sensitive error upon
           fail returned
    @param error_diag_len length of the error buffer
    @return one of the general error codes or one of the following:
	    DRMAA_ERRNO_INVALID_ATTRIBUTE_VALUE
*/
  DLL_MAGIC int drmaa_get_attribute (drmaa_job_template_t * jt, const char *name,
			   char *value, size_t value_len,
			   char *error_diagnosis, size_t error_diag_len);

/** Adds <name, value> pairs to the list of vector attributes in jt
    @return one of the general error codes or one of the following:
	    DRMAA_ERRNO_INVALID_ATTRIBUTE_FORMAT
	    DRMAA_ERRNO_INVALID_ATTRIBUTE_VALUE
	    DRMAA_ERRNO_CONFLICTING_ATTRIBUTE_VALUE
*/
  DLL_MAGIC int drmaa_set_vector_attribute (drmaa_job_template_t * jt, const char *name,
				  const char *value[], char *error_diagnosis,
				  size_t error_diag_len);

/** Returns the values of a given job attribute in a given job template.
    @param jt job template
    @param name attribute name
    @param values filled with the attribute values upon success, terminated
           by a pointer to NULL
    @param error_diagnosis contains a context sensitive error upon
           fail returned
    @param error_diag_len length of the error buffer
    @return one of the general error codes or one of the following:
	    DRMAA_ERRNO_INVALID_ATTRIBUTE_VALUE
*/
  DLL_MAGIC int drmaa_get_vector_attribute (drmaa_job_template_t * jt, const char *name,
				  drmaa_attr_values_t ** values,
				  char *error_diagnosis,
				  size_t error_diag_len);

/** Returns the set of supported attribute names whose associated value
    is type String.  Includes supported DRMAA reserved attribute names
    and native attribute names.
    @return one of the general error codes or one of the following:
*/
  DLL_MAGIC int drmaa_get_attribute_names (drmaa_attr_names_t ** values,
				 char *error_diagnosis,
				 size_t error_diag_len);

/** Returns the set of supported attribute names whose associated value
    is type String Vector.  Includes supported DRMAA reserved attribute names
    and native attribute names.
    @return one of the general error codes or one of the following:
*/
  DLL_MAGIC int drmaa_get_vector_attribute_names (drmaa_attr_names_t ** values,
					char *error_diagnosis,
					size_t error_diag_len);

/* ------------------- job submission routines ------------------- */
/** Submits a job with attributes defined in the given job template.
    @param job_id filled with a printable NULL terminated string
           representing the job's id
    @param job_id_len size of the job_id param
    @param jt job template
    @param error_diagnosis contains a context sensitive error upon
           fail returned
    @param error_diag_len length of the error buffer
    @return one of the general error codes or one of the following:
	    DRMAA_ERRNO_TRY_LATER
	    DRMAA_ERRNO_DENIED_BY_DRM
	    DRMAA_ERRNO_DRM_COMMUNICATION_FAILURE
	    DMRAA_ERRNO_AUTH_FAILURE
 */
  DLL_MAGIC int drmaa_run_job (char *job_id, size_t job_id_len,
		     drmaa_job_template_t * jt, char *error_diagnosis,
		     size_t error_diag_len);

/**
    @param error_diagnosis contains a context sensitive error upon
           fail returned
    @param error_diag_len length of the error buffer
    @return one of the following error codes:
            DRMAA_ERRNO_SUCCESS
	    DRMAA_ERRNO_TRY_LATER
	    DRMAA_ERRNO_DENIED_BY_DRM
	    DRMAA_ERRNO_NO_MEMORY
	    DRMAA_ERRNO_DRM_COMMUNICATION_FAILURE
	    DMRAA_ERRNO_AUTH_FAILURE
 */
  DLL_MAGIC int drmaa_run_bulk_jobs (drmaa_job_ids_t ** jobids,
			   drmaa_job_template_t * jt, int start,
			   int end, int incr, char *error_diagnosis,
			   size_t error_diag_len);

/* ------------------- job control routines ------------------- */
/** Control the given jobid
    @param jobid Job to control
    @param action type of control to affect on job
    @param error_diagnosis contains a context sensitive error upon
           fail returned
    @param error_diag_len length of the error buffer
    @return one of the general error codes or one of the following:
	    DRMAA_ERRNO_RESUME_INCONSISTENT_STATE
	    DRMAA_ERRNO_SUSPEND_INCONSISTENT_STATE
	    DRMAA_ERRNO_HOLD_INCONSISTENT_STATE
	    DRMAA_ERRNO_RELEASE_INCONSISTENT_STATE
	    DRMAA_ERRNO_INVALID_JOB    
 */
  DLL_MAGIC int drmaa_control (const char *jobid, int action, char *error_diagnosis,
		     size_t error_diag_len);

/** Wait until all jobs specified by job_ids have finished execution.
    @param jobids Holds all job_ids to wait on
    @param timeout number of seconds to wait
    @param dispose determines if rusage data should be deleted or not
    @param error_diagnosis contains a context sensitive error upon
           fail returned
    @param error_diag_len length of the error buffer
    @return one of the general error codes or one of the following:
	    DRMAA_ERRNO_EXIT_TIMEOUT
	    DRMAA_ERRNO_INVALID_JOB
 */
  DLL_MAGIC int drmaa_synchronize (const char *job_ids[], signed long timeout,
			 int dispose, char *error_diagnosis,
			 size_t error_diag_len);

/** Waits for job id job_id to fail or finish execution.  
    @param job_id filled with a printable NULL terminated string
           representing the job's id
    @param job_id_out job id of ended job
    @param job_id_out_len length of job_id_out
    @param stat status code of job_id_out
    @param timeout number of seconds to wait for job
    @param rusage resource usage 
    @param error_diagnosis contains a context sensitive error upon
           fail returned
    @param error_diag_len length of the error buffer
    @return one of the general error codes or one of the following:
	    DRMAA_ERRNO_NO_RUSAGE
	    DRMAA_ERRNO_EXIT_TIMEOUT
	    DRMAA_ERRNO_INVALID_JOB
 */
  DLL_MAGIC int drmaa_wait (const char *job_id, char *job_id_out, size_t job_id_out_len,
		  int *stat, signed long timeout,
		  drmaa_attr_values_t ** rusage, char *error_diagnosis,
		  size_t error_diag_len);

/** Evalutes non-zero into exited if stat was returned for a job that terminated
    normally.
    @param exited Non-zero if job terminated normally
    @param stat Code returned from drmaa_wait()
    @param error_diagnosis contains a context sensitive error upon
           fail returned
    @param error_diag_len length of the error buffer
    @return one of the general error codes
*/
  DLL_MAGIC int drmaa_wifexited (int *exited, int stat, char *error_diagnosis,
		       size_t error_diag_len);

/** Evalutes process's exit code into exit_status if drmaa_wifexited() returned
    non-zero.
    @param exit_status Process's exit code
    @param stat Code returned from drmaa_wait()
    @param error_diagnosis contains a context sensitive error upon
           fail returned
    @param error_diag_len length of the error buffer
    @return one of the general error codes
*/
  DLL_MAGIC int drmaa_wexitstatus (int *exit_status, int stat, char *error_diagnosis,
			 size_t error_diag_len);

/** Evalutes signaled to non-zero if status was returned for a job that
    terminated due to the receipt of a signal.
    @param signaled Non-zero if stat indicates terminated via signal
    @param stat Code returned from drmaa_wait()
    @param error_diagnosis contains a context sensitive error upon
           fail returned
    @param error_diag_len length of the error buffer
    @return one of the general error codes
*/
  DLL_MAGIC int drmaa_wifsignaled (int *signaled, int stat, char *error_diagnosis,
			 size_t error_diag_len);

/** Returns the name of the signal that terminated the process if the 
    drmaa_wifsignaled() returned non-zero.
    @param signal Filled with signal name
    @param signal_len Size of signal buffer
    @param stat Code returned from drmaa_wait()
    @param error_diagnosis contains a context sensitive error upon
           fail returned
    @param error_diag_len length of the error buffer
    @return one of the general error codes
*/
  DLL_MAGIC int drmaa_wtermsig (char *signal, size_t signal_len, int stat,
		      char *error_diagnosis, size_t error_diag_len);

/** Evalutes core_dumped to non-zero if status was returned for a job that
    terminated and core_dumped.
    @param core_dumped Non-zero if stat indicates terminated and core dumped
    @param stat Code returned from drmaa_wait()
    @param error_diagnosis contains a context sensitive error upon
           fail returned
    @param error_diag_len length of the error buffer
    @return one of the general error codes
*/
  DLL_MAGIC int drmaa_wcoredump (int *core_dumped, int stat, char *error_diagnosis,
		       size_t error_diag_len);

/** Evalutes aborted to non-zero if status was returned for a job that
    terminated before ever running.
    @param aborted Non-zero if stat indicates job never ran 
    @param stat Code returned from drmaa_wait()
    @param error_diagnosis contains a context sensitive error upon
           fail returned
    @param error_diag_len length of the error buffer
    @return one of the general error codes
*/
  DLL_MAGIC int drmaa_wifaborted (int *aborted, int stat, char *error_diagnosis,
			size_t error_diag_len);

/** Gets the program status of a given job id.
 *  @param job_id job id
 *  @param remote_ps filled with status of the job
    @param error_diagnosis contains a context sensitive error upon
           fail returned
    @param error_diag_len length of the error buffer
    @return one of the general error codes or one of the following:
	    DRMAA_ERRNO_DRM_COMMUNICATION_FAILURE
	    DMRAA_ERRNO_AUTH_FAILURE
	    DRMAA_ERRNO_INVALID_JOB
 */
  DLL_MAGIC int drmaa_job_ps (const char *job_id, int *remote_ps, char *error_diagnosis,
		    size_t error_diag_len);

/* ------------------- auxiliary routines ------------------- */
/** Returns the error message associated with a particular error
    @param error_num the error number
    @return message associated with given error_num
*/
  DLL_MAGIC const char *drmaa_strerror (int drmaa_errno);

/** Returns the current contact information for DRM system.
    @return one of the general error codes
*/
  DLL_MAGIC int drmaa_get_contact (char *contact, size_t contact_len,
			 char *error_diagnosis, size_t error_diag_len);

/** Identifies the version of the DRMAA API this library implements.
    @param major major version number
    @param minor minor version number
    @return one of the general error codes
*/
  DLL_MAGIC int drmaa_version (unsigned int *major, unsigned int *minor,
		     char *error_diagnosis, size_t error_diag_len);

/** Identifies which DRM system is being used.
    @return one of the general error codes
*/
  DLL_MAGIC int drmaa_get_DRM_system (char *drm_system, size_t drm_system_len,
			    char *error_diagnosis, size_t error_diag_len);

/** Identifies which DRM system is being used.
    @return one of the general error codes
*/
  DLL_MAGIC int drmaa_get_DRMAA_implementation (char *impl, size_t impl_len,
				      char *error_diagnosis,
				      size_t error_diag_len);

#ifdef __cplusplus
}
#endif

#endif /* __DRMAA_H */
