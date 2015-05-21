
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

#include <assert.h>
#include <stdio.h>

#ifdef WIN32
#pragma warning (disable: 4996)
#define _CRT_SECURE_NO_DEPRECATE  // for latest SDK compilers
#endif

// define if drmaa_control() should wait to see the state change in log file
// (this blocks the whole library!)
// When disabled, ST_SUBMIT_SUSPEND_RESUME_WAIT easily breaks
#define DRMAA_CONTROL_SYNC

#include "auxDrmaa.h"
#include "drmaa_common.h"
#include "drmaa.h"

/* ------------------- private variables ------------------- */
static const char *drmaa_err_msgs[] = {
	/* ------------- these are relevant to all sections -------------- */
	"Success",
	"Internal error",
	"Failed to communicate properly with Condor",
	"Unauthorized use of Condor",
	"Invalid argument",
	"No active DRMAA session exists",
	"Unable to allocate needed memory",
	/* -------------- init and exit specific --------------- */
	"Invalid contact string",
	"Problem using default contact string",
	"No default contact string selected",
	"Initialization failed",
	"A DRMAA session is already active",
	"DRMS failed to exit properly",
	/* ---------------- job attributes specific -------------- */
	"Invalid attribute format",
	"Invalid attribute value",
	"Conflicting attribute values",
	/* --------------------- job submission specific -------------- */
	"Please try again later",
	"Request denied",
	/* ------------------------- job control specific -------------- */
	"Invalid job id",
	"Current job state does not permit it to be resumed",
	"Current job state does not permit it to be suspended",
	"Current job state does not permit it to be put on hold",
	"Current job state does not permit it to be released",
	"Timeout expired",
	"No rusage or stat information could be retrieved",
	"No more elements in vector"
};

static const char *signal_names[] = {
	"SIGHUP",
	"SIGINT",
	"SIGQUIT",
	"SIGILL",
	"SIGABRT",
	"SIGFPE",
	"SIGKILL",
	"SIGSEGV",
	"SIGPIPE",
	"SIGALRM",
	"SIGTERM",
	"SIGUSR1",
	"SIGUSR2",
	"SIGCHLD",
	"SIGCONT",
	"SIGSTOP",
	"SIGTSTP",
	"SIGTTIN",
	"SIGTTOU"
};

/* ------------------- private helper routines ------------------- */

#define CHECK_ACTIVE_SESSION() \
	do { \
		int res; \
		if (!session_lock_initialized) \
			return 0; \
		MUTEX_LOCK(session_lock); \
		res = session_state; \
		MUTEX_UNLOCK(session_lock); \
		if (res == INACTIVE) \
			return standard_drmaa_error(DRMAA_ERRNO_NO_ACTIVE_SESSION, error_diagnosis, error_diag_len); \
	} while (0)

/* ---------- C/C++ language binding specific interfaces -------- */
int
drmaa_get_next_attr_name(drmaa_attr_names_t * values, char *value, size_t value_len)
{
	if (!values || !value)
		return DRMAA_ERRNO_INVALID_ARGUMENT;

	if (values->index == values->size)
		return DRMAA_ERRNO_NO_MORE_ELEMENTS;

	if (values->index < values->size) {
		strlcpy(value, values->attrs[values->index], value_len);
		++values->index;
		return DRMAA_ERRNO_SUCCESS;
	}

	return DRMAA_ERRNO_INTERNAL_ERROR;
}

int
drmaa_get_next_attr_value(drmaa_attr_values_t *values, char *value, size_t value_len)
{
	if (!values || !value)
		return DRMAA_ERRNO_INVALID_ARGUMENT;

	if (values->index == values->size)
		return DRMAA_ERRNO_NO_MORE_ELEMENTS;

	if (values->index < values->size) {
		strlcpy(value, values->values[values->index], value_len);
		++values->index;
		return DRMAA_ERRNO_SUCCESS;
	}

	return DRMAA_ERRNO_INTERNAL_ERROR;
}

int
drmaa_get_next_job_id(drmaa_job_ids_t * values, char *value, size_t value_len)
{
	if (!values || !value)
		return DRMAA_ERRNO_INVALID_ARGUMENT;

	if (values->index == values->size)
		return DRMAA_ERRNO_NO_MORE_ELEMENTS;

	if (values->index < values->size) {
		strlcpy(value, values->values[values->index], value_len);
		++values->index;
		return DRMAA_ERRNO_SUCCESS;
	}

	return DRMAA_ERRNO_INTERNAL_ERROR;
}

void
drmaa_release_attr_names(drmaa_attr_names_t * values)
{
	int i;

	if (values != NULL) {
		if (values->attrs != NULL) {
			for (i = 0; i < values->size; i++)
				free(values->attrs[i]);
			free(values->attrs);
		}
		free(values);
	}
}

void
drmaa_release_attr_values(drmaa_attr_values_t *values)
{
	int i;

	if (values != NULL) {
		if (values->values != NULL) {
			for (i = 0; i < values->size; i++)
				free(values->values[i]);
			free(values->values);
		}
		free(values);
	}
}

void
drmaa_release_job_ids(drmaa_job_ids_t * values)
{
	int i;

	if (values != NULL) {
		if (values->values != NULL) {
			for (i = 0; i < values->size; i++)
				free(values->values[i]);
			free(values->values);
		}
		free(values);
	}
}

/* ------------------- init/exit routines ------------------- */
int
drmaa_init(const char *contact, char *error_diagnosis, size_t error_diag_len)
{

#ifdef DEBUG
	// we want to have unbuffered output in DEBUG mode,
	// even when we pipe it to a file / tee
	#ifdef WIN32
		setbuf(stdout, NULL);
		setbuf(stderr, NULL);
	#else
		setlinebuf(stdout);
		setlinebuf(stderr);
	#endif
#endif

#ifdef WIN32
	if (!session_lock_initialized) {
		MUTEX_SETUP(session_lock);
		session_lock_initialized = 1;
	}
#endif

	MUTEX_LOCK(session_lock);

	if (session_state == ACTIVE) {
		snprintf(error_diagnosis, error_diag_len, drmaa_strerror(DRMAA_ERRNO_ALREADY_ACTIVE_SESSION));
		MUTEX_UNLOCK(session_lock);
		return DRMAA_ERRNO_ALREADY_ACTIVE_SESSION;
	}

	// TODO: contact condor_status

	// Obtain base file directory path
	if (!get_base_dir()) {
		snprintf(error_diagnosis, error_diag_len, "Failed to determine base directory");
		MUTEX_UNLOCK(session_lock);
		return DRMAA_ERRNO_INTERNAL_ERROR;
	}

	// Create directory
	if (mkdir(file_dir, S_IXUSR | S_IRUSR | S_IWUSR) == -1 && errno != EEXIST) {
		snprintf(error_diagnosis, error_diag_len, "Failed to make base directory");
		MUTEX_UNLOCK(session_lock);
		return DRMAA_ERRNO_INTERNAL_ERROR;
	}

	// TODO: verify library has write, read, and delete access to 
	// all its directories

	// Obtain name of local schedd
	if (get_schedd_name() == -1) {
		snprintf(error_diagnosis, error_diag_len, "Failed to obtain name of local schedd");
		MUTEX_UNLOCK(session_lock);
		return DRMAA_ERRNO_INTERNAL_ERROR;
	}

	// Iniparser is not thread-safe
	MUTEX_SETUP(iniparser_lock);

	// Initialize other local data structures
	MUTEX_SETUP(job_list_lock);

	job_list = NULL;
	num_jobs = 0;

	session_state = ACTIVE;

	MUTEX_UNLOCK(session_lock);

	return DRMAA_ERRNO_SUCCESS;
}

int
drmaa_exit(char *error_diagnosis, size_t error_diag_len)
{
	CHECK_ACTIVE_SESSION();

	MUTEX_LOCK(session_lock);

	MUTEX_LOCK(job_list_lock);
	free_job_list();
	MUTEX_UNLOCK(job_list_lock);

	session_state = INACTIVE;

	MUTEX_UNLOCK(session_lock);

	return DRMAA_ERRNO_SUCCESS;
}

/* ------------------- job template routines ------------------- */
int
drmaa_allocate_job_template(drmaa_job_template_t ** jt, char *error_diagnosis, size_t error_diag_len)
{
	CHECK_ACTIVE_SESSION();

	if (!jt)
		return standard_drmaa_error(DRMAA_ERRNO_INVALID_ARGUMENT, error_diagnosis, error_diag_len);

	if ((*jt = create_job_template()) == NULL)
		return standard_drmaa_error(DRMAA_ERRNO_NO_MEMORY, error_diagnosis, error_diag_len);

	return DRMAA_ERRNO_SUCCESS;
}

int
drmaa_delete_job_template(drmaa_job_template_t * jt, char *error_diagnosis, size_t error_diag_len)
{
	CHECK_ACTIVE_SESSION();

	if (!jt)
		return standard_drmaa_error(DRMAA_ERRNO_INVALID_ARGUMENT, error_diagnosis, error_diag_len);

	destroy_job_template(jt);

	return DRMAA_ERRNO_SUCCESS;
}

int
drmaa_set_attribute(drmaa_job_template_t * jt, const char *name,
		    const char *value, char *error_diagnosis, size_t error_diag_len)
{
	int result = DRMAA_ERRNO_NO_MEMORY;
	job_attr_t *ja;

	CHECK_ACTIVE_SESSION();

	if (!is_valid_job_template(jt, error_diagnosis, error_diag_len) ||
	    !is_valid_attr_name(name, error_diagnosis, error_diag_len) ||
	    !is_scalar_attr(name, error_diagnosis, error_diag_len) ||
	    !is_supported_attr(name, error_diagnosis, error_diag_len))
		return DRMAA_ERRNO_INVALID_ARGUMENT;
	else if (attr_conflict(jt, name, error_diagnosis, error_diag_len))
		return DRMAA_ERRNO_CONFLICTING_ATTRIBUTE_VALUES;
	else if (!is_valid_attr_value(&result, name, value, error_diagnosis, error_diag_len))
		return result;

	if (contains_attr(jt, name, error_diagnosis, error_diag_len))
		rm_jt_attribute(jt, name);

	// make new job_attr_t and set it at the head of the jt's list
	if ((ja = create_job_attribute()) == NULL)
		return standard_drmaa_error(DRMAA_ERRNO_NO_MEMORY, error_diagnosis, error_diag_len);

	ja->next = jt->head;
	jt->head = ja;
	++jt->num_attr;

	// set job attribute's fields
	strlcpy(ja->name, name, sizeof(ja->name));

	if ((ja->val.value = malloc(strlen(value) + 1)) == NULL) {
		destroy_job_attribute(ja);
		return standard_drmaa_error(DRMAA_ERRNO_NO_MEMORY, error_diagnosis, error_diag_len);
	}

	ja->num_values = 1;
	strcpy(ja->val.value, value);
	return DRMAA_ERRNO_SUCCESS;
}

int
drmaa_get_attribute(drmaa_job_template_t * jt, const char *name, char *value,
		    size_t value_len, char *error_diagnosis, size_t error_diag_len)
{
	job_attr_t *ja;

	CHECK_ACTIVE_SESSION();

	if (!is_valid_job_template(jt, error_diagnosis, error_diag_len) ||
	    !is_valid_attr_name(name, error_diagnosis, error_diag_len) ||
	    !is_scalar_attr(name, error_diagnosis, error_diag_len) ||
	    !is_supported_attr(name, error_diagnosis, error_diag_len))
		return DRMAA_ERRNO_INVALID_ATTRIBUTE_VALUE;

	// look for attribute name
	if ((ja = find_attr(jt, name, error_diagnosis, error_diag_len)) == NULL)
		return DRMAA_ERRNO_INVALID_ATTRIBUTE_VALUE;

	// copy scalar value to output buffer
	strlcpy(value, ja->val.value, value_len);

	return DRMAA_ERRNO_SUCCESS;
}

int
drmaa_set_vector_attribute(drmaa_job_template_t * jt, const char *name,
			   const char *value[], char *error_diagnosis, size_t error_diag_len)
{
	int result;
	unsigned int index = 0;
	job_attr_t *ja;

	CHECK_ACTIVE_SESSION();

	if (!is_valid_job_template(jt, error_diagnosis, error_diag_len) ||
	    !is_valid_attr_name(name, error_diagnosis, error_diag_len) ||
	    !is_vector_attr(name, error_diagnosis, error_diag_len) ||
	    !is_supported_attr(name, error_diagnosis, error_diag_len))
		return DRMAA_ERRNO_INVALID_ARGUMENT;
	else if (attr_conflict(jt, name, error_diagnosis, error_diag_len))
		return DRMAA_ERRNO_CONFLICTING_ATTRIBUTE_VALUES;

	// verify values[] has at least one value
	if (value == NULL || value[0] == NULL)
		return standard_drmaa_error(DRMAA_ERRNO_INVALID_ARGUMENT, error_diagnosis, error_diag_len); 

	// validate all attribute values
	while (value[index] != NULL) {
		if (!is_valid_attr_value(&result, name, value[index], error_diagnosis, error_diag_len))
			return result;
		index++;
	}

	if (contains_attr(jt, name, error_diagnosis, error_diag_len)) {
		// remove old entry
		rm_jt_attribute(jt, name);
	}

	// make new job_attr_t and set it at the head of the jt's list
	if ((ja = create_job_attribute()) == NULL) {
		return standard_drmaa_error(DRMAA_ERRNO_NO_MEMORY, error_diagnosis, error_diag_len); 
	}

	ja->next = jt->head;
	jt->head = ja;
	++jt->num_attr;

	// set job attribute's fields
	strlcpy(ja->name, name, sizeof(ja->name));
	ja->num_values = index;

	// set job attribute's values, allocating space according to number of values
	if (ja->num_values == 1) {
		if ((ja->val.value = malloc(strlen(value[0]) + 1)) == NULL) {
			destroy_job_attribute(ja);
			return standard_drmaa_error(DRMAA_ERRNO_NO_MEMORY, error_diagnosis, error_diag_len); 
		}
		strcpy(ja->val.value, value[0]);
	} else {
		if ((ja->val.values = calloc(index, sizeof(char *))) == NULL) {
			destroy_job_attribute(ja);
			return standard_drmaa_error(DRMAA_ERRNO_NO_MEMORY, error_diagnosis, error_diag_len); 
		}

		index = 0;

		while (index < ja->num_values) {
			ja->val.values[index] = malloc(strlen(value[index]) + 1);

			if (ja->val.values[index] == NULL) {
				destroy_job_attribute(ja);
				return standard_drmaa_error(DRMAA_ERRNO_NO_MEMORY, error_diagnosis, error_diag_len); 
			} else {
				strcpy(ja->val.values[index], value[index]);
				++index;
			}
		}
	}

	return DRMAA_ERRNO_SUCCESS;
}

int
drmaa_get_vector_attribute(drmaa_job_template_t * jt, const char *name,
			   drmaa_attr_values_t **values, char *error_diagnosis, size_t error_diag_len)
{
	job_attr_t *ja;
	unsigned int index = 0;

	CHECK_ACTIVE_SESSION();

	if (!is_valid_job_template(jt, error_diagnosis, error_diag_len) ||
	    !is_valid_attr_name(name, error_diagnosis, error_diag_len) ||
	    !is_vector_attr(name, error_diagnosis, error_diag_len) ||
	    !is_supported_attr(name, error_diagnosis, error_diag_len))
		return DRMAA_ERRNO_INVALID_ATTRIBUTE_VALUE;

	// look for attribute
	if ((ja = find_attr(jt, name, error_diagnosis, error_diag_len)) == NULL)
		return DRMAA_ERRNO_INVALID_ATTRIBUTE_VALUE;

	// allocate memory for drmaa_attr_values_t
	if ((*values = create_dav(ja->num_values)) == NULL)
		return standard_drmaa_error(DRMAA_ERRNO_NO_MEMORY, error_diagnosis, error_diag_len); 

	// copy vector values into output buffer, allocating space for values
	if (ja->num_values == 1) {
		if (add_dav(*values, ja->val.value) == -1) {
			destroy_dav(*values);
			return standard_drmaa_error(DRMAA_ERRNO_NO_MEMORY, error_diagnosis, error_diag_len); 
		}
	} else {
		while (index < ja->num_values) {
			if (add_dav(*values, ja->val.values[index]) == -1) {
				destroy_dav(*values);
				return standard_drmaa_error(DRMAA_ERRNO_NO_MEMORY, error_diagnosis, error_diag_len); 
			}
			index++;
		}
	}

	return DRMAA_ERRNO_SUCCESS;
}

int
drmaa_get_attribute_names(drmaa_attr_names_t ** values, char *error_diagnosis, size_t error_diag_len)
{
	int i, j;

	CHECK_ACTIVE_SESSION();

	// allocate memory 
	if ((*values = malloc(sizeof(drmaa_attr_names_t))) == NULL)
		return standard_drmaa_error(DRMAA_ERRNO_NO_MEMORY, error_diagnosis, error_diag_len); 

	(*values)->index = 0;
	(*values)->size = NUM_SUPP_SCALAR_ATTR;

	if (((*values)->attrs = calloc(NUM_SUPP_SCALAR_ATTR, sizeof(char *))) == NULL) {
		free(*values);
		return standard_drmaa_error(DRMAA_ERRNO_NO_MEMORY, error_diagnosis, error_diag_len); 
	}

	for (i = 0; i < NUM_SUPP_SCALAR_ATTR; i++) {
		(*values)->attrs[i] = malloc(DRMAA_ATTR_BUFFER);

		if ((*values)->attrs[i] == NULL) {
			for (i--; i >= 0; i--)
				free((*values)->attrs[i]);
			free(*values);
			return standard_drmaa_error(DRMAA_ERRNO_NO_MEMORY, error_diagnosis, error_diag_len); 
		}
	}

	// copy attribute names into place, starting with required attributes
	j = 0;
	strlcpy((*values)->attrs[j++], DRMAA_REMOTE_COMMAND, DRMAA_ATTR_BUFFER);
	strlcpy((*values)->attrs[j++], DRMAA_JS_STATE, DRMAA_ATTR_BUFFER);
	strlcpy((*values)->attrs[j++], DRMAA_WD, DRMAA_ATTR_BUFFER);
	strlcpy((*values)->attrs[j++], DRMAA_JOB_CATEGORY, DRMAA_ATTR_BUFFER);
	strlcpy((*values)->attrs[j++], DRMAA_NATIVE_SPECIFICATION, DRMAA_ATTR_BUFFER);
	strlcpy((*values)->attrs[j++], DRMAA_BLOCK_EMAIL, DRMAA_ATTR_BUFFER);
	strlcpy((*values)->attrs[j++], DRMAA_START_TIME, DRMAA_ATTR_BUFFER);
	strlcpy((*values)->attrs[j++], DRMAA_JOB_NAME, DRMAA_ATTR_BUFFER);
	strlcpy((*values)->attrs[j++], DRMAA_INPUT_PATH, DRMAA_ATTR_BUFFER);
	strlcpy((*values)->attrs[j++], DRMAA_OUTPUT_PATH, DRMAA_ATTR_BUFFER);
	strlcpy((*values)->attrs[j++], DRMAA_ERROR_PATH, DRMAA_ATTR_BUFFER);
	strlcpy((*values)->attrs[j++], DRMAA_JOIN_FILES, DRMAA_ATTR_BUFFER);
	strlcpy((*values)->attrs[j++], DRMAA_TRANSFER_FILES, DRMAA_ATTR_BUFFER);

	// TODO: add optional scalar job attributes
	//strlcpy((*values)->attrs[13], DRMAA_DEADLINE_TIME, DRMAA_ATTR_BUFFER);
	//strlcpy((*values)->attrs[14], DRMAA_WCT_HLIMIT, DRMAA_ATTR_BUFFER);
	//strlcpy((*values)->attrs[15], DRMAA_WCT_SLIMIT, DRMAA_ATTR_BUFFER);
	//strlcpy((*values)->attrs[16], DRMAA_DURATION_HLIMIT, DRMAA_ATTR_BUFFER);
	//strlcpy((*values)->attrs[17], DRMAA_DURATION_SLIMIT, DRMAA_ATTR_BUFFER);

	return DRMAA_ERRNO_SUCCESS;
}

int
drmaa_get_vector_attribute_names(drmaa_attr_names_t ** values, char *error_diagnosis, size_t error_diag_len)
{
	int i;

	CHECK_ACTIVE_SESSION();

	// allocate memory
	if ((*values = malloc(sizeof(drmaa_attr_names_t))) == NULL) {
		return standard_drmaa_error(DRMAA_ERRNO_NO_MEMORY, error_diagnosis, error_diag_len); 
	}

	(*values)->index = 0;
	(*values)->size = NUM_SUPP_VECTOR_ATTR;

	if (((*values)->attrs = calloc(NUM_SUPP_VECTOR_ATTR, sizeof(char *))) == NULL) {
		free(*values);
		return standard_drmaa_error(DRMAA_ERRNO_NO_MEMORY, error_diagnosis, error_diag_len); 
	}
	
	for (i = 0; i < NUM_SUPP_VECTOR_ATTR; i++) {
		(*values)->attrs[i] = malloc(DRMAA_ATTR_BUFFER);
		if ((*values)->attrs[i] == NULL) {
			for (i--; i >= 0; i--)
				free((*values)->attrs[i]);	
			free(*values);
			return standard_drmaa_error(DRMAA_ERRNO_NO_MEMORY, error_diagnosis, error_diag_len); 
		}
	}

	// copy attribute names into place
	strlcpy((*values)->attrs[0], DRMAA_V_ARGV, DRMAA_ATTR_BUFFER);
	strlcpy((*values)->attrs[1], DRMAA_V_ENV, DRMAA_ATTR_BUFFER);
	strlcpy((*values)->attrs[2], DRMAA_V_EMAIL, DRMAA_ATTR_BUFFER);

	return DRMAA_ERRNO_SUCCESS;
}

/* ------------------- job submission routines ------------------- */
int
drmaa_run_job(char *job_id, size_t job_id_len, drmaa_job_template_t * jt, char *error_diagnosis, size_t error_diag_len)
{
	int result = DRMAA_ERRNO_TRY_LATER;
	bool isHoldJob = false;
	char *submit_file_name;
	condor_drmaa_job_info_t *job;

	// 1. Perform Initialization and Validation checks
	CHECK_ACTIVE_SESSION();

	if (!job_id) {
		snprintf(error_diagnosis, error_diag_len, "job_id is NULL"); 
		return DRMAA_ERRNO_INVALID_ARGUMENT;
	}

	if (!is_valid_job_template(jt, error_diagnosis, error_diag_len))
		return DRMAA_ERRNO_INVALID_ARGUMENT;

	if (job_id_len < MIN_JOBID_LEN) {
		snprintf(error_diagnosis, error_diag_len, "job_id_len must be a "
			 "minimum of %d characters", MIN_JOBID_LEN);
		return DRMAA_ERRNO_INVALID_ARGUMENT;
	}

	char* username = 0;
	// 2. Create submit file
	if ((result =
	     create_submit_file(&submit_file_name, jt, &isHoldJob, error_diagnosis,
				error_diag_len, 1, 1, 1, &username)) != DRMAA_ERRNO_SUCCESS)
	{
		if(username)
			free(username);
		return result;
	}

	// 3. Submit job
	result = submit_job(job_id, job_id_len, submit_file_name, error_diagnosis, error_diag_len, username);

	if(username)
		free(username);

#ifndef DEBUG
	remove(submit_file_name);
#endif
	free(submit_file_name);

	if (result != DRMAA_ERRNO_SUCCESS) {
		DEBUG_PRINT1("submit_job failed with result: %s\n", drmaa_strerror(result));
		return result;
	}

	// 4. Add job_id to list
	if ((job = create_job_info(job_id)) == NULL) {
		return standard_drmaa_error(DRMAA_ERRNO_NO_MEMORY, error_diagnosis, error_diag_len); 
	} else {
		if (isHoldJob)
			job->state = HELD;
		else
			job->state = SUBMITTED;

		job->next = NULL;

		MUTEX_LOCK(session_lock);
		MUTEX_LOCK(job_list_lock);

		// was drmaa_exit() called meanwhile?
		if (session_state == ACTIVE) {
			condor_drmaa_job_info_t *tmp;

			if (!job_list) {
				job_list = job;
			} else {
				tmp = job_list;
				while (tmp->next)
					tmp = tmp->next;
				tmp->next = job;
			}

			num_jobs++;
		} else {
			destroy_job_info(job);
		}

		MUTEX_UNLOCK(session_lock);
		MUTEX_UNLOCK(job_list_lock);
	}

	return DRMAA_ERRNO_SUCCESS;
}

int
drmaa_run_bulk_jobs(drmaa_job_ids_t ** jobids, drmaa_job_template_t * jt,
		    int start, int end, int incr, char *error_diagnosis, size_t error_diag_len)
{
	int result = DRMAA_ERRNO_INTERNAL_ERROR;
	int numjobs = -1;
	char *submit_file_name;
	char *act_job_id, *act_job_id_old;
	bool isHoldJob;
	int i;
	condor_drmaa_job_info_t *job;

	// Initialization and validation checks
	CHECK_ACTIVE_SESSION();

	if (!jobids)
		return standard_drmaa_error(DRMAA_ERRNO_INVALID_ARGUMENT, error_diagnosis, error_diag_len); 

	if (start == end)
		numjobs = 1;

	if (start < end) {
		numjobs = ((end - start) / incr) + 1;
		if (incr < 1) {
			snprintf(error_diagnosis, error_diag_len,
				 "Expected incr parameter with value greater than zero");
			return DRMAA_ERRNO_INVALID_ARGUMENT;
		}
	}

	if (start > end) {
		int tmp;

		numjobs = ((start - end) / incr) + 1;
		if (incr > -1) {
			snprintf(error_diagnosis, error_diag_len, "Expected incr parameter with value below zero");
			return DRMAA_ERRNO_INVALID_ARGUMENT;
		}

		tmp = start;
		start = end;
		end = tmp;

		incr = -incr;
	}

	if (!is_valid_job_template(jt, error_diagnosis, error_diag_len))
		return DRMAA_ERRNO_INVALID_ARGUMENT;

	// allocate space for jobids
	DEBUG_PRINT4("Allocating for %u jobs, from %u to %u with incr %u\n", numjobs, start, end, incr);
	*jobids = malloc(sizeof(drmaa_job_ids_t));
	if (!*jobids)
		return standard_drmaa_error(DRMAA_ERRNO_NO_MEMORY, error_diagnosis, error_diag_len); 

	(*jobids)->values = calloc(numjobs, sizeof(char *));
	if (!(*jobids)->values) {
		free(*jobids);
		return standard_drmaa_error(DRMAA_ERRNO_NO_MEMORY, error_diagnosis, error_diag_len); 
	}

	(*jobids)->size = numjobs;
	(*jobids)->index = 0;

	isHoldJob = false;

	char* username = 0;
	// 2.1 Create submit file
	if ((result = create_submit_file(&submit_file_name, jt,
		&isHoldJob, error_diagnosis, error_diag_len, start, end, incr, &username)) != DRMAA_ERRNO_SUCCESS) {
		free((*jobids)->values);
		free(*jobids);
		if(username)
			free(username);
		return result;
	}

	// 2.2 Submit job
	act_job_id = calloc(numjobs, MAX_JOBID_LEN);
	if (!act_job_id) {
		snprintf(error_diagnosis, error_diag_len, drmaa_strerror(DRMAA_ERRNO_NO_MEMORY));
		free((*jobids)->values);
		free(*jobids);
		free(submit_file_name);
		return DRMAA_ERRNO_NO_MEMORY;
	}

	result = submit_job(act_job_id, MAX_JOBID_LEN, submit_file_name, error_diagnosis, error_diag_len, username);

	if(username)
		free(username);

#ifndef DEBUG
	remove(submit_file_name);
#endif
	free(submit_file_name);

	if (result != DRMAA_ERRNO_SUCCESS) {
		free((*jobids)->values);
		free(*jobids);
		free(act_job_id);
		return result;
	}

	act_job_id_old = act_job_id;

	for (i = 0; i < numjobs; i++) {

		(*jobids)->values[i] = strdup(act_job_id);
		if (!(*jobids)->values[i]) {
			for (i--; i >= 0; i--)
				free((*jobids)->values[i]);

			free((*jobids)->values);
			free(*jobids);
			free(act_job_id_old);
			return standard_drmaa_error(DRMAA_ERRNO_NO_MEMORY, error_diagnosis, error_diag_len); 
		}

		if (i + 1 <  numjobs)
			act_job_id += strlen(act_job_id) + 1;

		DEBUG_PRINT2("Adding %s at position %u to run_bulk_jobs result\n", (*jobids)->values[i], i);

		if ((job = create_job_info((*jobids)->values[i])) == NULL) {
			for (i--; i >= 0; i--)
				free((*jobids)->values[i]);

			free((*jobids)->values);
			free(*jobids);
			free(act_job_id_old);
			return standard_drmaa_error(DRMAA_ERRNO_NO_MEMORY, error_diagnosis, error_diag_len); 
		} else {
			if (isHoldJob)
				job->state = HELD;
			else
				job->state = SUBMITTED;

			job->next = NULL;

			MUTEX_LOCK(session_lock);
			MUTEX_LOCK(job_list_lock);

			// was drmaa_exit() called meanwhile?
			if (session_state == ACTIVE) {
				condor_drmaa_job_info_t *tmp;

				if (!job_list) {
					job_list = job;
				} else {
					tmp = job_list;
					while (tmp->next)
						tmp = tmp->next;
					tmp->next = job;
				}

				num_jobs++;
			} else {
				destroy_job_info(job);
			}

			MUTEX_UNLOCK(session_lock);
			MUTEX_UNLOCK(job_list_lock);
		}
	}

	free(act_job_id_old);

	return DRMAA_ERRNO_SUCCESS;
}

//jobid format: <username>:<jobid>
void extract_username_from_jobid(const char* jobid, char* username, char* parsed_job_id)
{
	username[0] = '\0';
	char* saveptr = 0;
	char* duplicate = strdup(jobid);
	char* user_token = strtok_r(duplicate, ":", &saveptr);
	if(user_token != 0)
	{
		char* token = strtok_r(0, ":", &saveptr);
		if(token)
		{
			strcpy(username, user_token);
			strcpy(parsed_job_id, token);
		}
		else
			strcpy(parsed_job_id, duplicate);
	}
	fprintf(stderr,"User %s jobid %s\n",username, parsed_job_id);
	free(duplicate);
}

/* ------------------- job control routines ------------------- */
int
drmaa_control(const char *arg_jobid, int action, char *error_diagnosis, size_t error_diag_len)
{
	int result = DRMAA_ERRNO_INVALID_JOB;
	condor_drmaa_job_info_t *info;
	char **jobSet;
	int numCopies = 0;
	int recurseCount, deleteCount;
	int remote_ps;
	int statResult;

	
	// 1. Argument validation and library state check
	CHECK_ACTIVE_SESSION();

	if (!arg_jobid) {
		snprintf(error_diagnosis, error_diag_len, "jobid is NULL"); 
		return DRMAA_ERRNO_INVALID_ARGUMENT;
	}

	char jobid[MAX_JOBID_LEN];
	strcpy(jobid, arg_jobid);
	char username[MAX_JOBID_LEN];
	extract_username_from_jobid(arg_jobid, username, jobid);

	if ((!is_valid_job_id(jobid) && (strcmp(jobid, DRMAA_JOB_IDS_SESSION_ALL) != 0))) {
		snprintf(error_diagnosis, error_diag_len, "Invalid job id \"%s\"", jobid);
		return DRMAA_ERRNO_INVALID_ARGUMENT;
	}

	// Control on an empty session is always OK
	MUTEX_LOCK(job_list_lock);

	if (num_jobs == 0 && strcmp(jobid, DRMAA_JOB_IDS_SESSION_ALL) == 0) {
		MUTEX_UNLOCK(job_list_lock);
		return DRMAA_ERRNO_SUCCESS;
	}

	MUTEX_UNLOCK(job_list_lock);

	// for SESSION_ALL, copy all job identifiers and do a recursive control
	if (strcmp(jobid, DRMAA_JOB_IDS_SESSION_ALL) == 0) {

		// copy current set of jobs and do recursive wait
		// this saves us from MT issues where users might change the job list in between
		MUTEX_LOCK(job_list_lock);

		jobSet = calloc(num_jobs, sizeof(char *));

		for (info = job_list; info; info = info->next) {

			jobSet[numCopies] = malloc(MAX_JOBID_LEN);
			strlcpy(jobSet[numCopies], info->id, MAX_JOBID_LEN);

			numCopies++;
		}

		MUTEX_UNLOCK(job_list_lock);

		// do recursive calls on our copy

		DEBUG_PRINT0("Performing recursive drmaa_control calls for session jobs\n");

		result = DRMAA_ERRNO_SUCCESS;
		recurseCount = 0;

		while (recurseCount < numCopies && result == DRMAA_ERRNO_SUCCESS) {
			result = drmaa_control(jobSet[recurseCount], action, error_diagnosis, error_diag_len);

			DEBUG_PRINT2("Control operation for %s resulted in %u\n",
				     jobSet[recurseCount], result);

			// MT issue: someone removed the job meanwhile, ignore it and move on
			if (result == DRMAA_ERRNO_INVALID_JOB)
				result = DRMAA_ERRNO_SUCCESS;

			recurseCount++;
		}

		// cleanup
		deleteCount = 0;
		while (deleteCount < numCopies) {
			free(jobSet[deleteCount]);
			deleteCount++;
		}

		free(jobSet);

		return result;
	}

	// no SESSION_ALL

	// 2. Verify existence and status of the job
	MUTEX_LOCK(job_list_lock);

	info = get_job_info(jobid);

	statResult = get_job_status_logfile(jobid, &remote_ps, error_diagnosis, error_diag_len);

	if (!info || info->state == DISPOSED || statResult != DRMAA_ERRNO_SUCCESS) {
		MUTEX_UNLOCK(job_list_lock);
		return standard_drmaa_error(DRMAA_ERRNO_INVALID_JOB, error_diagnosis, error_diag_len); 
	}

	/* if someone controlled the job externally, our internal job state can be inconsistent */

	if (info->state == HELD) {

		if (action == DRMAA_CONTROL_HOLD) {
			MUTEX_UNLOCK(job_list_lock);
			return standard_drmaa_error(DRMAA_ERRNO_HOLD_INCONSISTENT_STATE, error_diagnosis, error_diag_len);
		} else if (action == DRMAA_CONTROL_SUSPEND) {
			MUTEX_UNLOCK(job_list_lock);
			return standard_drmaa_error(DRMAA_ERRNO_SUSPEND_INCONSISTENT_STATE, error_diagnosis, error_diag_len);
		} else if (action == DRMAA_CONTROL_RESUME) {
			MUTEX_UNLOCK(job_list_lock);
			return standard_drmaa_error(DRMAA_ERRNO_RESUME_INCONSISTENT_STATE, error_diagnosis, error_diag_len);
		}

	} else if (info->state == SUSPEND) {

		if (action == DRMAA_CONTROL_HOLD) {
			MUTEX_UNLOCK(job_list_lock);
			return standard_drmaa_error(DRMAA_ERRNO_HOLD_INCONSISTENT_STATE, error_diagnosis, error_diag_len);
		} else if (action == DRMAA_CONTROL_RELEASE) {
			MUTEX_UNLOCK(job_list_lock);
			return standard_drmaa_error(DRMAA_ERRNO_RELEASE_INCONSISTENT_STATE, error_diagnosis, error_diag_len);
		} else if (action == DRMAA_CONTROL_SUSPEND) {
			MUTEX_UNLOCK(job_list_lock);
			return standard_drmaa_error(DRMAA_ERRNO_SUSPEND_INCONSISTENT_STATE, error_diagnosis, error_diag_len);
		}

	} else if (info->state == FINISHED) {

		if (action == DRMAA_CONTROL_HOLD) {
			MUTEX_UNLOCK(job_list_lock);
			return standard_drmaa_error(DRMAA_ERRNO_HOLD_INCONSISTENT_STATE, error_diagnosis, error_diag_len);
		} else if (action == DRMAA_CONTROL_RELEASE) {
			MUTEX_UNLOCK(job_list_lock);
			return standard_drmaa_error(DRMAA_ERRNO_RELEASE_INCONSISTENT_STATE, error_diagnosis, error_diag_len);
		} else if (action == DRMAA_CONTROL_SUSPEND) {
			MUTEX_UNLOCK(job_list_lock);
			return standard_drmaa_error(DRMAA_ERRNO_SUSPEND_INCONSISTENT_STATE, error_diagnosis, error_diag_len);
		} else if (action == DRMAA_CONTROL_RESUME) {
			MUTEX_UNLOCK(job_list_lock);
			return standard_drmaa_error(DRMAA_ERRNO_RESUME_INCONSISTENT_STATE, error_diagnosis, error_diag_len);
		} else if (action == DRMAA_CONTROL_TERMINATE) {
			MUTEX_UNLOCK(job_list_lock);
			return standard_drmaa_error(DRMAA_ERRNO_INVALID_JOB, error_diagnosis, error_diag_len);
		}

	} else if (info->state == SUBMITTED || info->state == SUBMITTED_ASSUME_RUNNING) {

		// fake the state, to be consistent from DRMAA point of view
		if (info->state == SUBMITTED_ASSUME_RUNNING)
			remote_ps = DRMAA_PS_RUNNING;

		// if job is running, hold should be forbidden
		// if job is not running, suspend should be forbidden
		if (remote_ps == DRMAA_PS_RUNNING && action == DRMAA_CONTROL_HOLD) {
			MUTEX_UNLOCK(job_list_lock);
			return standard_drmaa_error(DRMAA_ERRNO_HOLD_INCONSISTENT_STATE, error_diagnosis, error_diag_len);
		} else if (remote_ps == DRMAA_PS_QUEUED_ACTIVE && action == DRMAA_CONTROL_SUSPEND) {
			MUTEX_UNLOCK(job_list_lock);
			return standard_drmaa_error(DRMAA_ERRNO_SUSPEND_INCONSISTENT_STATE, error_diagnosis, error_diag_len);
		} else if (action == DRMAA_CONTROL_RELEASE) {
			MUTEX_UNLOCK(job_list_lock);
			return standard_drmaa_error(DRMAA_ERRNO_RELEASE_INCONSISTENT_STATE, error_diagnosis, error_diag_len);
		} else if (action == DRMAA_CONTROL_RESUME) {
			MUTEX_UNLOCK(job_list_lock);
			return standard_drmaa_error(DRMAA_ERRNO_RESUME_INCONSISTENT_STATE, error_diagnosis, error_diag_len);
		}
	}

#define JOB_FINISHED(ps) (ps == DRMAA_PS_DONE || ps == DRMAA_PS_FAILED)

	switch (action) {
	case DRMAA_CONTROL_HOLD:
		result = hold_job(jobid, error_diagnosis, error_diag_len, username);

		if (result == DRMAA_ERRNO_SUCCESS) {

			mark_job(jobid, HELD);

#ifdef DRMAA_CONTROL_SYNC
			do {
				DEBUG_PRINT0("Waiting for job to be held.\n");
				statResult = get_job_status_logfile(jobid, &remote_ps, error_diagnosis, error_diag_len);
				if (statResult != DRMAA_ERRNO_SUCCESS)
					break;
				sleep_ms(25);
			} while (remote_ps != DRMAA_PS_USER_ON_HOLD && !JOB_FINISHED(remote_ps));

			result = statResult;
#endif
		}
		break;

	case DRMAA_CONTROL_RELEASE:
		result = release_job(jobid, error_diagnosis, error_diag_len, username);

		if (result == DRMAA_ERRNO_SUCCESS) {

			mark_job(jobid, SUBMITTED);

#ifdef DRMAA_CONTROL_SYNC
			do {
				DEBUG_PRINT0("Waiting for job to be running again.\n");
				statResult = get_job_status_logfile(jobid, &remote_ps, error_diagnosis, error_diag_len);
				if (statResult != DRMAA_ERRNO_SUCCESS)
					break;
				sleep_ms(25);
			} while (remote_ps == DRMAA_PS_USER_ON_HOLD);

			result = statResult;
#endif
		}
		break;

	case DRMAA_CONTROL_SUSPEND:
		result = hold_job(jobid, error_diagnosis, error_diag_len, username);

		if (result == DRMAA_ERRNO_SUCCESS) {

			mark_job(jobid, SUSPEND);

#ifdef DRMAA_CONTROL_SYNC
			do {
				DEBUG_PRINT0("Waiting for job to be suspended.\n");
				statResult = get_job_status_logfile(jobid, &remote_ps, error_diagnosis, error_diag_len);
				if (statResult != DRMAA_ERRNO_SUCCESS)
					break;
				sleep_ms(25);
			} while (remote_ps != DRMAA_PS_USER_SUSPENDED && !JOB_FINISHED(remote_ps));

			result = statResult;
#endif
		}
		break;

	case DRMAA_CONTROL_RESUME:
		result = release_job(jobid, error_diagnosis, error_diag_len, username);

		if (result == DRMAA_ERRNO_SUCCESS) {

			mark_job(jobid, SUBMITTED_ASSUME_RUNNING);

#ifdef DRMAA_CONTROL_SYNC
			do {
				DEBUG_PRINT0("Waiting for job to be running again.\n");
				statResult = get_job_status_logfile(jobid, &remote_ps, error_diagnosis, error_diag_len);
				if (statResult != DRMAA_ERRNO_SUCCESS)
					break;
				sleep_ms(25);
			} while (remote_ps == DRMAA_PS_USER_SUSPENDED);

			result = statResult;
#endif
		}
		break;

	case DRMAA_CONTROL_TERMINATE:
		result = terminate_job(jobid, error_diagnosis, error_diag_len, username);

		if (result == DRMAA_ERRNO_SUCCESS) {

			mark_job(jobid, FINISHED);

#ifdef DRMAA_CONTROL_SYNC
			do {
				DEBUG_PRINT0("Waiting for job to be terminated.\n");
				statResult = get_job_status_logfile(jobid, &remote_ps, error_diagnosis, error_diag_len);
				if (statResult != DRMAA_ERRNO_SUCCESS)
					break;
				sleep_ms(25);
			} while (!JOB_FINISHED(remote_ps));

			result = statResult;
#endif
		}

		break;

	default:
		// not in DRMAA 1.0, but will come
		snprintf(error_diagnosis, error_diag_len, "Unknown DRMAA control action");
		result = DRMAA_ERRNO_INVALID_ARGUMENT;
		break;
	}

	// XXX it would be good to release this lock earlier
	MUTEX_UNLOCK(job_list_lock);

	return result;
}

int
drmaa_synchronize(const char *job_ids[], signed long timeout, int dispose, char *error_diagnosis, size_t error_diag_len)
{
	int result = DRMAA_ERRNO_SUCCESS;
	int i;
	int sync_all_jobs = 0;
	time_t start;
	char **jobs_to_sync = NULL;

	// 1. Validation of Lib status and args
	CHECK_ACTIVE_SESSION();

	if (timeout < 0 && timeout != DRMAA_TIMEOUT_WAIT_FOREVER) {
		snprintf(error_diagnosis, error_diag_len, "Invalid wait timeout");
		return DRMAA_ERRNO_INVALID_ARGUMENT;
	} else if (job_ids == NULL || job_ids[0] == NULL) {
		snprintf(error_diagnosis, error_diag_len, "job_ids is NULL or empty");
		return DRMAA_ERRNO_INVALID_ARGUMENT;
	}

	for (i = 0; job_ids[i] != NULL; i++) {
		if (strcmp(job_ids[i], DRMAA_JOB_IDS_SESSION_ALL) == 0) {
			sync_all_jobs = 1;
			break;
		} else if (!is_valid_job_id(job_ids[i])) {
			snprintf(error_diagnosis, error_diag_len, "Invalid job id \"%s\"", job_ids[i]);
			return DRMAA_ERRNO_INVALID_ARGUMENT;
		}
	}

	if (!sync_all_jobs)
		DEBUG_PRINT1("drmaa_synchronize, %d jobs to sync with\n", i - 1);
	else
		DEBUG_PRINT0("drmaa_synchronize, sync with all jobs\n");

	MUTEX_LOCK(job_list_lock);

	// Verify special case: SESSION_ALL wait with empty session
	if (num_jobs == 0 && sync_all_jobs) {
		DEBUG_PRINT0("DRMAA_JOB_IDS_SESSION_ALL but empty session\n");
		MUTEX_UNLOCK(job_list_lock);
		return DRMAA_ERRNO_SUCCESS;
	}

	// B. Verify all synch-desired jobids are on job_info list
	// With SESSION_ALL, this is implicit

	if (!sync_all_jobs) {

		for (i = 0; job_ids[i]; i++) {
			condor_drmaa_job_info_t *info;

			if (!(info = get_job_info(job_ids[i])) || info->state == DISPOSED) {
				MUTEX_UNLOCK(job_list_lock);	
				return standard_drmaa_error(DRMAA_ERRNO_INVALID_JOB, error_diagnosis, error_diag_len);
			}
		}

		jobs_to_sync = calloc(i + 1, sizeof(char *));
		if (!jobs_to_sync) {
			MUTEX_UNLOCK(job_list_lock);
			return standard_drmaa_error(DRMAA_ERRNO_NO_MEMORY, error_diagnosis, error_diag_len);
		}

		for (i = 0; job_ids[i]; i++) {
			jobs_to_sync[i] = strdup(job_ids[i]);

			if (!jobs_to_sync[i]) {
				for (i--; i >= 0; i--)
					free(jobs_to_sync[i]);
				free(jobs_to_sync);
				MUTEX_UNLOCK(job_list_lock);
				return standard_drmaa_error(DRMAA_ERRNO_NO_MEMORY, error_diagnosis, error_diag_len);
			}
		}

	} else {
		condor_drmaa_job_info_t *job;

		jobs_to_sync = calloc(num_jobs + 1, sizeof(char *));
		if (!jobs_to_sync) {
			MUTEX_UNLOCK(job_list_lock);
			return standard_drmaa_error(DRMAA_ERRNO_NO_MEMORY, error_diagnosis, error_diag_len);
		}

		for (job = job_list; job; job = job->next, i++) {
			jobs_to_sync[i] = strdup(job->id);

			DEBUG_PRINT1("synchronizing with all, adding %s\n", job->id);

			if (!jobs_to_sync[i]) {
				for (i--; i >= 0; i--)
					free(jobs_to_sync[i]);
				free(jobs_to_sync);
				MUTEX_UNLOCK(job_list_lock);
				return standard_drmaa_error(DRMAA_ERRNO_NO_MEMORY, error_diagnosis, error_diag_len);
			}
		}

		assert(i == num_jobs);
	}

	MUTEX_UNLOCK(job_list_lock);

	start = time(NULL);

	for (i = 0; jobs_to_sync[i]; i++) {
		DEBUG_PRINT2("Now waiting for %s (%u)\n", jobs_to_sync[i], i);

		result = wait_job(jobs_to_sync[i], NULL, -1, dispose, 0, NULL, timeout,
				start, NULL, error_diagnosis, error_diag_len);

		if (result != DRMAA_ERRNO_SUCCESS) {
			DEBUG_PRINT2("wait_job failed in drmaa_synchronize with %d (%s)\n", result, drmaa_strerror(result));
			return result;
		}
	}

	return result;
}

int
drmaa_wait(const char *job_id, char *job_id_out, size_t job_id_out_len,
	   int *stat, signed long timeout, drmaa_attr_values_t **rusage, char *error_diagnosis, size_t error_diag_len)
{
	int result = DRMAA_ERRNO_INVALID_JOB;
	int getStat;
	char out_id[MAX_JOBID_LEN];

	CHECK_ACTIVE_SESSION();
	
	if (!job_id)
		return standard_drmaa_error(DRMAA_ERRNO_INVALID_ARGUMENT, error_diagnosis, error_diag_len);

	if (!is_valid_job_id(job_id) && strcmp(job_id, DRMAA_JOB_IDS_SESSION_ANY) != 0) {
		snprintf(error_diagnosis, error_diag_len, "Invalid job id \"%s\"", job_id);
		return DRMAA_ERRNO_INVALID_JOB;
	}

	/*    else if (rusage == NULL){
	 * snprintf(error_diagnosis, error_diag_len, "Invalid rusage value");
	 * return DRMAA_ERRNO_INVALID_ARGUMENT;
	 * }
	 */

	if (timeout < 0 && timeout != DRMAA_TIMEOUT_WAIT_FOREVER) {
		snprintf(error_diagnosis, error_diag_len, "Invalid timeout");
		return DRMAA_ERRNO_INVALID_ARGUMENT;
	}

	// Determine name of job_id to wait on
	//    if (strcmp(job_id, DRMAA_JOB_IDS_SESSION_ANY) == 0){
	// 1) condor_drmaa_job_info_t* last_job_to_complete?
	// 2) scan through all log files for any job that has completed?
	// 3) condor_drmaa_job_info_t* last_job_submitted?
	//      snprintf(error_diagnosis, error_diag_len, 
	//               "Feature not currently supported");
	//      return DRMAA_ERRNO_INVALID_JOB;
	//    }
	//    else 

	if (stat == NULL)
		getStat = false;
	else
		getStat = true;

	// we always want to know the job id, even if the caller is not interested
	result = wait_job(job_id, out_id, MAX_JOBID_LEN, true, getStat,
			  stat, timeout, time(NULL), rusage, error_diagnosis, error_diag_len);

	// return job id if the caller wants it
	if (result == DRMAA_ERRNO_SUCCESS && job_id_out != NULL) {

		if (job_id_out_len < strlen(out_id) + 1) {
			snprintf(error_diagnosis, error_diag_len, "job_id_out length is too small");
			return DRMAA_ERRNO_INVALID_ARGUMENT;
		}

		strlcpy(job_id_out, out_id, job_id_out_len);
	}

	return result;
}

int
drmaa_wifexited(int *exited, int stat, char *error_diagnosis, size_t error_diag_len)
{
	CHECK_ACTIVE_SESSION();

	if (!is_valid_stat(stat) || !exited)
		return standard_drmaa_error(DRMAA_ERRNO_INVALID_ARGUMENT, error_diagnosis, error_diag_len);

	// Did process terminate? 
	if (stat != STAT_UNKNOWN)
		*exited = 1;
	else
		*exited = 0;

	return DRMAA_ERRNO_SUCCESS;
}

int
drmaa_wexitstatus(int *exit_status, int stat, char *error_diagnosis, size_t error_diag_len)
{
	CHECK_ACTIVE_SESSION();

	if (!is_valid_stat(stat) || stat == STAT_UNKNOWN || !exit_status)
		return standard_drmaa_error(DRMAA_ERRNO_INVALID_ARGUMENT, error_diagnosis, error_diag_len);

	if (stat >= STAT_NOR_BASE)
		*exit_status = stat - STAT_NOR_BASE;
	else
		*exit_status = 0;

	return DRMAA_ERRNO_SUCCESS;
}

int
drmaa_wifsignaled(int *signaled, int stat, char *error_diagnosis, size_t error_diag_len)
{
	CHECK_ACTIVE_SESSION();

	if (!is_valid_stat(stat) || !signaled)
		return standard_drmaa_error(DRMAA_ERRNO_INVALID_ARGUMENT, error_diagnosis, error_diag_len);

	if (stat >= STAT_SIG_BASE && stat < STAT_NOR_BASE)
		*signaled = 1;
	else
		*signaled = 0;

	return DRMAA_ERRNO_SUCCESS;
}

int
drmaa_wtermsig(char *signal, size_t signal_len, int stat, char *error_diagnosis, size_t error_diag_len)
{
	CHECK_ACTIVE_SESSION();

	if (!is_valid_stat(stat) || stat < STAT_SIG_BASE || stat >= STAT_NOR_BASE) {
		snprintf(error_diagnosis, error_diag_len, "Invalid / non-signaled stat code");
		return DRMAA_ERRNO_INVALID_ARGUMENT;
	} else if (signal == NULL || signal_len <= MIN_SIGNAL_NM_LEN) {
		snprintf(error_diagnosis, error_diag_len, "signal buffer too small");
		return DRMAA_ERRNO_INVALID_ARGUMENT;
	}

	if (stat >= STAT_SIG_CORE_BASE)
		snprintf(signal, signal_len, "%s", signal_names[stat - STAT_SIG_CORE_BASE]);
	else
		snprintf(signal, signal_len, "%s", signal_names[stat - 1]);

	return DRMAA_ERRNO_SUCCESS;
}

int
drmaa_wcoredump(int *core_dumped, int stat, char *error_diagnosis, size_t error_diag_len)
{
	CHECK_ACTIVE_SESSION();

	if (!is_valid_stat(stat) || stat < STAT_SIG_BASE || stat >= STAT_NOR_BASE || !core_dumped)
		return standard_drmaa_error(DRMAA_ERRNO_INVALID_ARGUMENT, error_diagnosis, error_diag_len);

	if (stat >= STAT_SIG_CORE_BASE)
		*core_dumped = 1;
	else
		*core_dumped = 0;

	return DRMAA_ERRNO_SUCCESS;
}

int
drmaa_wifaborted(int *aborted, int stat, char *error_diagnosis, size_t error_diag_len)
{
	CHECK_ACTIVE_SESSION();

	if (!is_valid_stat(stat) || !aborted)
		return standard_drmaa_error(DRMAA_ERRNO_INVALID_ARGUMENT, error_diagnosis, error_diag_len);

	if (stat == STAT_ABORTED)
		*aborted = 1;
	else
		*aborted = 0;

	return DRMAA_ERRNO_SUCCESS;
}

int
drmaa_job_ps(const char *job_id, int *remote_ps, char *error_diagnosis, size_t error_diag_len)
{
	int result;
	condor_drmaa_job_info_t *info;

	CHECK_ACTIVE_SESSION();

	if (!job_id || !remote_ps)
		return standard_drmaa_error(DRMAA_ERRNO_INVALID_ARGUMENT, error_diagnosis, error_diag_len);

	MUTEX_LOCK(job_list_lock);

	info = get_job_info(job_id);

	// job unknown or being reaped
	if (!info || info->state == DISPOSED) {
		MUTEX_UNLOCK(job_list_lock);
		return standard_drmaa_error(DRMAA_ERRNO_INVALID_JOB, error_diagnosis, error_diag_len);
	}

	// first check the log file
	// this is more performant than condor_q
	// there might also be the case that condor_q reflects state later than the log file
	result = get_job_status_logfile(job_id, remote_ps, error_diagnosis, error_diag_len);

	if (result != DRMAA_ERRNO_INTERNAL_ERROR) {

		// both DRMAA_SUSPEND and DRMAA_HOLD lead to Condor hold
		if (*remote_ps == DRMAA_PS_USER_ON_HOLD && info->state == SUSPEND)
			*remote_ps = DRMAA_PS_USER_SUSPENDED;

		// in case of discrepancies between internal state and condor state, consult condor_q
		// one special case example: submission of holded job is not reflected in the log file
		if (info->state == HELD && *remote_ps == DRMAA_PS_QUEUED_ACTIVE)
			result = get_job_status_condorq(job_id, remote_ps, error_diagnosis, error_diag_len);
	}

	MUTEX_UNLOCK(job_list_lock);

	return result;
}

/* ------------------- auxiliary routines ------------------- */
const char *
drmaa_strerror(int drmaa_errno)
{
	static const char *result = "Unknown error";
	static int numErrors = sizeof(drmaa_err_msgs) / sizeof(char *);

	if (drmaa_errno >= 0 && drmaa_errno < numErrors)
		result = drmaa_err_msgs[drmaa_errno];

	return result;
}

int
drmaa_version(unsigned int *major, unsigned int *minor, char *error_diagnosis, size_t error_diag_len)
{
	if (!major || !minor)
		return standard_drmaa_error(DRMAA_ERRNO_INVALID_ARGUMENT, error_diagnosis, error_diag_len);

	*major = 1;
	*minor = 0;
	return DRMAA_ERRNO_SUCCESS;
}

int
drmaa_get_contact(char *contact, size_t contact_len, char *error_diagnosis, size_t error_diag_len)
{
	static const char *contact_str = "Condor";

	if (!contact || contact_len < strlen(contact_str) + 1)
		return standard_drmaa_error(DRMAA_ERRNO_INVALID_ARGUMENT, error_diagnosis, error_diag_len);

	strlcpy(contact, contact_str, contact_len);
	return DRMAA_ERRNO_SUCCESS;
}

int
drmaa_get_DRM_system(char *drm_system, size_t drm_system_len, char *error_diagnosis, size_t error_diag_len)
{
	static const char *drm_system_str = "Condor";

	if (!drm_system || drm_system_len < strlen(drm_system_str) + 1)
		return standard_drmaa_error(DRMAA_ERRNO_INVALID_ARGUMENT, error_diagnosis, error_diag_len);

	strlcpy(drm_system, drm_system_str, drm_system_len);
	return DRMAA_ERRNO_SUCCESS;
}

int
drmaa_get_DRMAA_implementation(char *impl, size_t impl_len, char *error_diagnosis, size_t error_diag_len)
{
	static const char *drmaa_implementation_str = "Condor";

	if (!impl || impl_len < strlen(drmaa_implementation_str) + 1)
		return standard_drmaa_error(DRMAA_ERRNO_INVALID_ARGUMENT, error_diagnosis, error_diag_len);

	strlcpy(impl, drmaa_implementation_str, impl_len);
	return DRMAA_ERRNO_SUCCESS;
}
