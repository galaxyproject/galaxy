
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
#include <stdarg.h>
#include <ctype.h>

// for strptime
#define __USE_XOPEN
#include <time.h>

#ifdef WIN32 
#pragma warning (disable: 4996)
#define _CRT_SECURE_NO_DEPRECATE  // for latest SDK compilers
#endif  

#include "auxDrmaa.h"
#include "drmaa_common.h"
#include "iniparser.h"

int
standard_drmaa_error(int drmaa_errno, char *error_diagnosis, size_t error_diag_len)
{       
        strlcpy(error_diagnosis, drmaa_strerror(drmaa_errno), error_diag_len);
        return drmaa_errno;
}

int
condor_drmaa_snprintf(char *buf, size_t n, const char *fmt, ...)
{
	va_list arglist;
	int ret;

	if (buf == NULL || n == 0)
		return -1;

	va_start(arglist, fmt);
#ifdef WIN32
	ret = _vsnprintf(buf, n, fmt, arglist);
#else
	ret = vsnprintf(buf, n, fmt, arglist);
#endif
	va_end(arglist);

	return ret;
}

// size is always sizeof(dst)
size_t
condor_drmaa_strlcpy(char *dst, const char *src, size_t size)
{
        size_t i, n = size;
        
        for (i = 0; n > 1 && src[i]; i++, n--)
                dst[i] = src[i];
                
        if (n)
                dst[i] = 0;
                
        while (src[i])
                i++;
                
        return i;
}       

// size is always sizeof(dst)
size_t
condor_drmaa_strlcat(char *dst, const char *src, size_t size)
{
        size_t i, j;
        size_t left, dlen;
        
        for (i = 0; i < size && dst[i]; i++)
                continue;
                
        dlen = i;
        left = size - i;
        
        for (j = 0; left > j + 1 && src[j]; j++, i++)
                dst[i] = src[j]; 
                
        if (left)
                dst[i] = 0;
                
        while (src[j])
                j++;
                
        return dlen + j;
}       

int
is_number(const char *str)
{
	int result = 1;
	size_t i;

	for (i = 0; i < strlen(str); i++) {
		if (!isdigit((int)str[i])) {
			result = 0;
			break;
		}
	}

	return (i > 0) ? result : 0;
}

job_attr_t *
create_job_attribute(void)
{
	job_attr_t *result = malloc(sizeof(job_attr_t));

	if (result != NULL) {
		result->num_values = 0;
		result->next = NULL;
	}

	return result;
}

void
destroy_job_attribute(job_attr_t * ja)
{
	unsigned int i;

	if (ja->num_values == 1) {
		if (ja->val.value)
			free(ja->val.value);
	} else if (ja->num_values > 1) {
		for (i = 0; i < ja->num_values; i++) {
			if (ja->val.values[i])
				free(ja->val.values[i]);
		}
	}
	free(ja);
}

condor_drmaa_job_info_t *
create_job_info(const char *job_id)
{
	condor_drmaa_job_info_t *result = NULL;

	if (strlen(job_id) + 1 <= MAX_JOBID_LEN) {
		result = malloc(sizeof(condor_drmaa_job_info_t));

		if (result != NULL) {
			strlcpy(result->id, job_id, sizeof(result->id));
			result->ref_count = 0;
			result->lastmodtime = 0;
			result->next = NULL;
		}
	}

	return result;
}

void
destroy_job_info(condor_drmaa_job_info_t * job_info)
{
	if (job_info != NULL)
		free(job_info);
}

void
rm_jt_attribute(drmaa_job_template_t * jt, const char *name)
{
	job_attr_t *cur = jt->head;
	job_attr_t *last = NULL;

	while (cur != NULL) {
		if (strcmp(cur->name, name) == 0) {
			if (last == NULL)
				jt->head = cur->next;
			else
				last->next = cur->next;
			destroy_job_attribute(cur);
			break;
		} else {
			last = cur;
			cur = cur->next;
		}
	}
}

int
is_valid_attr_name(const char *name, char *error_diagnosis, size_t error_diag_len)
{
	int result = 0;

	if (name == NULL)
		snprintf(error_diagnosis, error_diag_len, "Attribute name is NULL");
	else if ((strlen(name) + 1) > DRMAA_ATTR_BUFFER)
		snprintf(error_diagnosis, error_diag_len, "Attribute name exceeds DRMAA_ATTR_BUFFER");
	else if (strcmp(name, DRMAA_REMOTE_COMMAND) != 0 &&
		 strcmp(name, DRMAA_JS_STATE) != 0 &&
		 strcmp(name, DRMAA_WD) != 0 &&
		 strcmp(name, DRMAA_JOB_CATEGORY) != 0 &&
		 strcmp(name, DRMAA_NATIVE_SPECIFICATION) != 0 &&
		 strcmp(name, DRMAA_BLOCK_EMAIL) != 0 &&
		 strcmp(name, DRMAA_START_TIME) != 0 &&
		 strcmp(name, DRMAA_JOB_NAME) != 0 &&
		 strcmp(name, DRMAA_INPUT_PATH) != 0 &&
		 strcmp(name, DRMAA_OUTPUT_PATH) != 0 &&
		 strcmp(name, DRMAA_ERROR_PATH) != 0 &&
		 strcmp(name, DRMAA_JOIN_FILES) != 0 &&
		 strcmp(name, DRMAA_TRANSFER_FILES) != 0 &&
		 strcmp(name, DRMAA_DEADLINE_TIME) != 0 &&
		 strcmp(name, DRMAA_WCT_HLIMIT) != 0 &&
		 strcmp(name, DRMAA_WCT_SLIMIT) != 0 &&
		 strcmp(name, DRMAA_DURATION_HLIMIT) != 0 &&
		 strcmp(name, DRMAA_DURATION_SLIMIT) != 0 &&
		 strcmp(name, DRMAA_V_ARGV) != 0 && strcmp(name, DRMAA_V_ENV) != 0 && strcmp(name, DRMAA_V_EMAIL) != 0)
		snprintf(error_diagnosis, error_diag_len, "Unrecognized attribute name");
	else
		result = 1;

	return result;
}

bool
is_valid_attr_value(int *err_cd, const char *name, const char *value, char *error_diagnosis, size_t error_diag_len)
{
	bool result = false;
	int i_value;

	if (value == NULL) {
		snprintf(error_diagnosis, error_diag_len, "%s: no value specified", name);
		*err_cd = DRMAA_ERRNO_INVALID_ATTRIBUTE_VALUE;
	} else {
		// case for each attribute name
		// TODO: Include cases for validating all other JobAttrName value
		if (strcmp(name, DRMAA_BLOCK_EMAIL) == 0) {
			// must be 0 or 1
			if (!is_number(value)) {
				snprintf(error_diagnosis, error_diag_len, "%s: not a number", name);
				*err_cd = DRMAA_ERRNO_INVALID_ATTRIBUTE_VALUE;
			} else {
				i_value = atoi(value);
				if (i_value != 0 && i_value != 1) {
					snprintf(error_diagnosis, error_diag_len, "%s: must be a 0" " or 1", name);
					*err_cd = DRMAA_ERRNO_INVALID_ATTRIBUTE_VALUE;
				} else
					result = true;
			}
		} else if (strcmp(name, DRMAA_INPUT_PATH) == 0 ||
			   strcmp(name, DRMAA_OUTPUT_PATH) == 0 || strcmp(name, DRMAA_ERROR_PATH) == 0) {
			if (strstr(value, ":") == NULL) {
				snprintf(error_diagnosis, error_diag_len,
					 "Missing mandatory colon delimiter in path argument");
				*err_cd = DRMAA_ERRNO_INVALID_ATTRIBUTE_VALUE;
			} else
				result = true;
		} else {
			// TODO: add validation for all other supported attributes
			result = true;
		}
	}

	return result;
}

int
is_scalar_attr(const char *name, char *error_diagnosis, size_t error_diag_len)
{
	int result = 0;

	if (name == NULL)
		snprintf(error_diagnosis, error_diag_len, "Attribute name is NULL");
	else if (strcmp(name, DRMAA_REMOTE_COMMAND) == 0 ||
		 strcmp(name, DRMAA_JS_STATE) == 0 ||
		 strcmp(name, DRMAA_WD) == 0 ||
		 strcmp(name, DRMAA_JOB_CATEGORY) == 0 ||
		 strcmp(name, DRMAA_NATIVE_SPECIFICATION) == 0 ||
		 strcmp(name, DRMAA_BLOCK_EMAIL) == 0 ||
		 strcmp(name, DRMAA_START_TIME) == 0 ||
		 strcmp(name, DRMAA_JOB_NAME) == 0 ||
		 strcmp(name, DRMAA_INPUT_PATH) == 0 ||
		 strcmp(name, DRMAA_OUTPUT_PATH) == 0 ||
		 strcmp(name, DRMAA_ERROR_PATH) == 0 ||
		 strcmp(name, DRMAA_JOIN_FILES) == 0 ||
		 strcmp(name, DRMAA_TRANSFER_FILES) == 0 ||
		 strcmp(name, DRMAA_DEADLINE_TIME) == 0 ||
		 strcmp(name, DRMAA_WCT_HLIMIT) == 0 ||
		 strcmp(name, DRMAA_WCT_SLIMIT) == 0 ||
		 strcmp(name, DRMAA_DURATION_HLIMIT) == 0 || strcmp(name, DRMAA_DURATION_SLIMIT) == 0)
		result = 1;
	else
		snprintf(error_diagnosis, error_diag_len, "Attribute name does not specify a scalar value");

	return result;
}

int
is_vector_attr(const char *name, char *error_diagnosis, size_t error_diag_len)
{
	int result = 0;

	if (name == NULL)
		snprintf(error_diagnosis, error_diag_len, "Attribute name is empty");
	else if (strcmp(name, DRMAA_V_ARGV) == 0 || strcmp(name, DRMAA_V_ENV) == 0 || strcmp(name, DRMAA_V_EMAIL) == 0)
		result = 1;
	else
		snprintf(error_diagnosis, error_diag_len, "Attribute name does not specify a vector value");

	return result;
}

int
is_supported_attr(const char *name, char *error_diagnosis, size_t error_diag_len)
{
	int result = 0;

	if (name == NULL)
		snprintf(error_diagnosis, error_diag_len, "Attribute name is empty");
	else if (strcmp(name, DRMAA_REMOTE_COMMAND) == 0 ||
		 strcmp(name, DRMAA_JS_STATE) == 0 ||
		 strcmp(name, DRMAA_WD) == 0 ||
		 strcmp(name, DRMAA_JOB_CATEGORY) == 0 ||
		 strcmp(name, DRMAA_NATIVE_SPECIFICATION) == 0 ||
		 strcmp(name, DRMAA_BLOCK_EMAIL) == 0 ||
		 strcmp(name, DRMAA_START_TIME) == 0 ||
		 strcmp(name, DRMAA_JOB_NAME) == 0 ||
		 strcmp(name, DRMAA_INPUT_PATH) == 0 ||
		 strcmp(name, DRMAA_OUTPUT_PATH) == 0 ||
		 strcmp(name, DRMAA_ERROR_PATH) == 0 || strcmp(name, DRMAA_JOIN_FILES) == 0 ||
		 strcmp(name, DRMAA_TRANSFER_FILES) == 0 ||
		 /* strcmp(name, DRMAA_DEADLINE_TIME) == 0 || 
		  * strcmp(name, DRMAA_WCT_HLIMIT) == 0 || 
		  * strcmp(name, DRMAA_WCT_SLIMIT) == 0 || 
		  * strcmp(name, DRMAA_DURATION_HLIMIT) == 0 || 
		  * strcmp(name, DRMAA_DURATION_SLIMIT) == 0 || */
		 strcmp(name, DRMAA_V_ARGV) == 0 || strcmp(name, DRMAA_V_ENV) == 0 || strcmp(name, DRMAA_V_EMAIL) == 0)
		result = 1;
	else
		snprintf(error_diagnosis, error_diag_len, "Attribute %s is not currently supported", name);

	return result;
}

/*
 * void 
 * print_ja(const job_attr_t* ja)
 * {
 * int i;
 * 
 * printf("\tName: %s   # of Values: %d\n", ja->name, ja->num_values);
 * if (ja->num_values == 1)           
 * printf("\t\tValue 1: \"%s\"\n", ja->val.value);
 * else {
 * for(i=0; i < ja->num_values; i++)
 * printf("\t\tValue %d: \"%s\"\n", i, ja->val.values[i]);
 * }
 * }
 */

drmaa_job_template_t *
create_job_template(void)
{
	drmaa_job_template_t *jt = malloc(sizeof(drmaa_job_template_t));

	if (jt != NULL) {
		jt->num_attr = 0;
		jt->head = NULL;
	}

	return jt;
}

void
destroy_job_template(drmaa_job_template_t *jt)
{
        job_attr_t *cur_ja;
        job_attr_t *last_ja;

        cur_ja = jt->head;     
        while (cur_ja != NULL) {
                last_ja = cur_ja;
                cur_ja = cur_ja->next;
                destroy_job_attribute(last_ja);
        }
        free(jt);
}

int
is_valid_job_template(const drmaa_job_template_t * jt, char *error_diagnosis, size_t error_diag_len)
{
	int result = 0;

	if (jt == NULL)
		snprintf(error_diagnosis, error_diag_len, "Job template is NULL");
	else {
		result = 1;
		/*  // TODO
		 * cur = jt;
		 * while (cur != NULL){
		 * result = isValidJobAttribute(cur, drmaa_context_error_buf);
		 * if (result)
		 * cur = cur->next;
		 * else
		 * break;
		 * }
		 */
	}

	return result;
}

job_attr_t *
find_attr(const drmaa_job_template_t * jt, const char *name, char *error_diagnosis, size_t error_diag_len)
{
	job_attr_t *result = jt->head;
	int found_attr = 0;

	while (!found_attr && result != NULL) {
		if (strcmp(result->name, name) == 0)
			found_attr = 1;
		else
			result = result->next;
	}

	if (!found_attr) {
		result = NULL;
		snprintf(error_diagnosis, error_diag_len, "Unable to find %s in the job template", name);
	}

	return result;
}

bool
attr_conflict(const drmaa_job_template_t * jt, const char *name, char *error_diagnosis, size_t error_diag_len)
{
	return false;
}

bool
contains_attr(const drmaa_job_template_t * jt, const char *name, char *error_diagnosis, size_t error_diag_len)
{
	int result = 0;
	job_attr_t *cur = jt->head;

	while (!result && cur != NULL) {
		if (strcmp(cur->name, name) == 0) {
			result = 1;
			snprintf(error_diagnosis, error_diag_len, "Attribute %s already set in job template", name);
		} else
			cur = cur->next;
	}

	return result;
}

/*
 * void
 * print_jt(const drmaa_job_template_t* jt)
 * {
 * job_attr_t* ja;
 * int i;
 * 
 * if (jt == NULL)
 * printf("print_jt(): NULL job template\n");
 * else {
 * printf("print_jt(): Job Template has %d attribute(s)\n", jt->num_attr);
 * 
 * ja = jt->head;
 * i = 0;
 * while (ja != NULL){
 * printf("\tAttribute #%d", i);
 * print_ja(ja);
 * ja = ja->next;
 * i++;
 * }
 * }
 * }
 */

int
create_submit_file(char **submit_fn, const drmaa_job_template_t * jt,
		   bool * isHoldJob, char *error_diagnosis, size_t error_diag_len, int start, int end, int incr, char** username)
{
	FILE *fs;
	time_t now;
	job_attr_t *ja, *job_category = NULL;
	bool joinFiles, gotStartTime, lastHoldJobResult;
	char transfer_files[16] = "";
	int i;

	// Generate a unique file name
	if (generate_unique_file_name(submit_fn) != 0) {
		snprintf(error_diagnosis, error_diag_len, "Unable to generate submit file name (unique file name not available)");
		return DRMAA_ERRNO_TRY_LATER;
	}

	// Create the file
	if ((fs = fopen(*submit_fn, "w")) == NULL) {
		snprintf(error_diagnosis, error_diag_len, "Unable to create submission file (file creation for %s failed)", *submit_fn);
		free(*submit_fn);
		return DRMAA_ERRNO_TRY_LATER;
	}
	/*fprintf(stderr,"File %s\n",*submit_fn);*/


	if (chmod(*submit_fn, S_IRUSR | S_IWUSR)) {
		snprintf(error_diagnosis, error_diag_len, "Unable to create submission file (permission change failed)");
		fclose(fs);
		free(*submit_fn);
		return DRMAA_ERRNO_TRY_LATER;
	}

	// Write the job template into the file
	if (fprintf(fs, "#\n# Condor Submit file\n") < 1) {
		snprintf(error_diagnosis, error_diag_len, "Failed to write to submit file");
		fclose(fs);
		free(*submit_fn);
		return DRMAA_ERRNO_TRY_LATER;
	}

	now = time(NULL);
	fprintf(fs, "# Automatically generated by DRMAA library on %s", ctime(&now));
	fprintf(fs, "#\n\n");
	fprintf(fs, "%-*s= %s%s%s.$(Cluster).$(Process)%s\n",
		SUBMIT_FILE_COL_SIZE, "Log", file_dir, LOG_FILE_PREFIX, schedd_name, LOG_FILE_EXTN);
	fprintf(fs, "%-*s= %s\n", SUBMIT_FILE_COL_SIZE, "Universe", "vanilla");

	// go through the attributes and determine preconditions
	ja = jt->head;
	joinFiles = false;	// default according to spec
	gotStartTime = false;	// with start time set, job must be submitted on hold
	while (ja != NULL) {

		if (strcmp(ja->name, DRMAA_JOIN_FILES) == 0) {
			if (strcmp(ja->val.value, "y") == 0) {
				joinFiles = true;
				DEBUG_PRINT0("Join_files is set\n");
			}
		}

		if (strcmp(ja->name, DRMAA_JOB_CATEGORY) == 0) {
			job_category = ja;
		}

		if (strcmp(ja->name, DRMAA_TRANSFER_FILES) == 0) {
			strlcpy(transfer_files, ja->val.value, sizeof(transfer_files));
		}

		if (strcmp(ja->name, DRMAA_START_TIME) == 0) {
			gotStartTime = true;
		}

		ja = ja->next;
	}

	// go again through the attributes and create submit file
	for (i = start; i <= end; i += incr) {
		ja = jt->head;

		*isHoldJob = false;
		lastHoldJobResult = false;

		while (ja != NULL) {
			if (write_job_attr(fs, ja, joinFiles, gotStartTime, &lastHoldJobResult, transfer_files, i, username) != SUCCESS) {
				snprintf(error_diagnosis, error_diag_len, "Unable to write job attribute to file");
				fclose(fs);
				free(*submit_fn);
				return DRMAA_ERRNO_TRY_LATER;
			}
			
			if (lastHoldJobResult == true)
				*isHoldJob = true;
			ja = ja->next;
		}

		if (job_category != NULL) {
			MUTEX_LOCK(iniparser_lock);
			fprintf(fs, "%-*s\n", SUBMIT_FILE_COL_SIZE, get_category_options(job_category->val.value));
			MUTEX_UNLOCK(iniparser_lock);
		}

		fprintf(fs, "Queue 1\n");
	}

	fsync(fileno(fs));

	if (fclose(fs) != 0)
		return DRMAA_ERRNO_INTERNAL_ERROR;
	else
	{
	  if(chmod(*submit_fn, 0644) != 0) {
	    snprintf(error_diagnosis, error_diag_len, "Unable to set permissions for file %s\n",*submit_fn);
	    free(*submit_fn);
	    return DRMAA_ERRNO_INTERNAL_ERROR;
	  }
	  else
	    return DRMAA_ERRNO_SUCCESS;
	}
}

int
generate_unique_file_name(char **fname)
{
#ifdef WIN32
	char tmpPath[MAX_PATH];
	*fname = (char*)malloc(sizeof(char)*MAX_PATH);

	if (0==GetTempPath(MAX_PATH, tmpPath))
		return -1;
	if (0==GetTempFileName(tmpPath, SUBMIT_FILE_PREFIX, 0, *fname))
		return -1;
#else
	char tmpFile[1024];

	snprintf(tmpFile, sizeof(tmpFile), "%s%ssubmit.XXXXXXX", file_dir, SUBMIT_FILE_PREFIX);

	/* XXX possible race condition, mkstemp() would be better */
	mktemp(tmpFile);

	*fname = (char *)malloc(strlen(tmpFile) + 1);
	if (!*fname)
		return -1;

	strcpy(*fname, tmpFile);
#endif
	return 0;
}

char *
parse_ts(const char *partialTs)
{
#ifdef HAVE_STRPTIME
	// TODO: this demands a lot more work to the optional parts of the string 
	char *result;
	const time_t now = time(NULL);
	struct tm dateWithCentury;

	localtime_r(&now, &dateWithCentury);

	if ((result = malloc(1024)) == NULL)
		return NULL;

	if (strptime(partialTs, "%C%y/%m/%d %H:%M:%S %z", &dateWithCentury) == NULL) {
		DEBUG_PRINT1("Conversion of DRMAA timestamp %s to epoch seconds failed", partialTs);
		return NULL;
	}

	if (strftime(result, 1024 - 1, "%s", &dateWithCentury) == 0) {
		time_t convValue = mktime(&dateWithCentury);

		DEBUG_PRINT1("Conversion of parsed DRMAA timestamp (%s) to epoch failed\n", ctime(&convValue));
		return NULL;
	}

	DEBUG_PRINT2("DRMAA timestamp %s results in epoch time %s\n", partialTs, result);
	return result;
#else
	// TODO: implement conversion from DRMAA timestamp to seconds since epoch
	return strdup("0");
#endif
}

char *
get_category_options(const char *categoryName)
{
	if (0 == access(SYSCONFDIR DRMAA_CONFIG_FILE, R_OK)) {
		dictionary *cats;
		char keyname[1024];
		char *catval;

		cats = iniparser_new(SYSCONFDIR DRMAA_CONFIG_FILE);

		snprintf(keyname, sizeof(keyname), "%s:%s", CATEGORY_SECTION_NAME, categoryName);

		catval = iniparser_getstring(cats, keyname, "");

		if (strcmp(catval, "") == 0) {
			DEBUG_PRINT0
			    ("Could not find category entry in DRMAA config file, ignoring JT job category value\n");
			return "";
		} else {
			// we have a value
			DEBUG_PRINT2
			    ("Using additional submit file entry %s, according to category %s\n", catval, categoryName);
			return catval;
		}
	} else {
		DEBUG_PRINT0("DRMAA configuration file not available, ignoring JT job category value\n");
		return "";
	}
}

char *
substitute_placeholders(const char *orig, int index)
{
	char *result = NULL, *tmp, *loc;
	int i, j;

	/* Test if orig contains any placeholders */
	if (strstr(orig, DRMAA_PLACEHOLDER_INCR) == NULL &&
	    strstr(orig, DRMAA_PLACEHOLDER_HD) == NULL && strstr(orig, DRMAA_PLACEHOLDER_WD) == NULL) {

		result = strdup(orig);
	} else {
		/* XXX ugly */
		result = malloc(strlen(orig) + 1024);
		tmp = strdup(orig);

		/* $drmaa_incr_ph$ */
		if ((loc = strstr(tmp, DRMAA_PLACEHOLDER_INCR)) != NULL) {
			char buf[64];

			for (i = 0; tmp + i != loc; i++) {
				result[i] = tmp[i];
			}
			result[i] = '\0';

			snprintf(buf, sizeof(buf), "%d", index);

			strcat(result, buf);

			j = i + strlen(buf);
			i += strlen(DRMAA_PLACEHOLDER_INCR);

			for (; tmp[i] != '\0'; i++, j++) {
				result[j] = tmp[i];
			}
			result[j] = '\0';

			free(tmp);
			tmp = strdup(result);
		}

		/* $drmaa_hd_ph$ */
		if ((loc = strstr(tmp, DRMAA_PLACEHOLDER_HD)) != NULL) {
			for (i = 0; &tmp[i] != loc; i++) {
				result[i] = tmp[i];
			}
			result[i] = '\0';

			strcat(result, "$ENV(HOME)");	/* TODO: UNIX vs Windows */
			j = i + strlen("$ENV(HOME)");
			i += strlen(DRMAA_PLACEHOLDER_HD);

			for (; tmp[i] != '\0'; i++, j++) {
				result[j] = tmp[i];
			}
			result[j] = '\0';

			free(tmp);
			tmp = strdup(result);
		}

		/* $drmaa_wd_ph$ */
		// XXX there's no way get execution directory in Condor (???)

		free(tmp);
	}

	return result;
}

int extract_username(char* native_specification_string, char** username)
{
	(*username) = 0;
	int return_val = -1;
	//create duplicate for parsing
	char* duplicate = strdup(native_specification_string);
	//set to 0
	size_t total_length = strlen(native_specification_string);
	memset(native_specification_string, 0, total_length);
	size_t curr_length = 0;
	//separate lines 
	char* line_save = 0;
	char* line = strtok_r(duplicate, "\n", &line_save); 
	while(line != 0)
	{
		size_t line_length = strlen(line);
		char* user_line = strstr(line, "submit_as_user");
		if(user_line)
		{
			char* user_save = 0;
			char* token = strtok_r(user_line, "=", &user_save);
			if(token)	//non-null first token : submit_as_user
			{
				if((token = strtok_r(0,"=",&user_save)))	//non-null: second token: username
				{
					(*username) = strdup(token);
					return_val = 1;
				}
			}
		}
		else
		{
			memcpy(native_specification_string+curr_length, line, line_length);
			curr_length += (line_length + 1); //1 for new line
			native_specification_string[curr_length-1] = '\n';
		}
		line = strtok_r(0, "\n", &line_save); 
	}
	if(curr_length > 0)
		native_specification_string[curr_length] = '\0';
	free(duplicate);
	return return_val;
}

int
write_job_attr(FILE *fs, const job_attr_t * ja, bool joinFiles, bool gotStartTime, bool *isHoldJob, const char *transfer_files, int index, char** username)
{
	int result = FAILURE;
	int num_bw = -1;
	char *sub_ph;

	*isHoldJob = false;

	if (strcmp(ja->name, DRMAA_REMOTE_COMMAND) == 0) {
		num_bw = fprintf(fs, "%-*s= %s\n", SUBMIT_FILE_COL_SIZE, "Executable", ja->val.value);
	}

	// startTime is implemented with periodic_release feature
	// therefore the startTime case sets HOLD anyway, and we must
	// ignore the user wish here
	else if (strcmp(ja->name, DRMAA_JS_STATE) == 0 && !gotStartTime) {
		if (strcmp(ja->val.value, DRMAA_SUBMISSION_STATE_HOLD) == 0 || gotStartTime) {
			num_bw = fprintf(fs, "%-*s= True\n", SUBMIT_FILE_COL_SIZE, "Hold");
			*isHoldJob = true;
			DEBUG_PRINT0("This is a hold job\n");
		} else {
			num_bw = fprintf(fs, "%-*s= False\n", SUBMIT_FILE_COL_SIZE, "Hold");
		}
	} else if (strcmp(ja->name, DRMAA_WD) == 0) {
		sub_ph = substitute_placeholders(ja->val.value, index);
		num_bw = fprintf(fs, "%-*s= %s\n", SUBMIT_FILE_COL_SIZE, "Initialdir", sub_ph);
		free(sub_ph);
	} else if (strcmp(ja->name, DRMAA_NATIVE_SPECIFICATION) == 0) {
		extract_username(ja->val.value, username);
		num_bw = fprintf(fs, "%-*s\n", SUBMIT_FILE_COL_SIZE, ja->val.value);
	} else if (strcmp(ja->name, DRMAA_BLOCK_EMAIL) == 0) {
		if (strcmp(ja->val.value, "1") == 0)
			num_bw = fprintf(fs, "%-*s= Never\n", SUBMIT_FILE_COL_SIZE, "Notification");
	} else if (strcmp(ja->name, DRMAA_START_TIME) == 0) {
		sub_ph = parse_ts(ja->val.value);
		if (sub_ph != NULL) {
			num_bw =
			    fprintf(fs, "%-*s=(CurrentTime > %s)\n", SUBMIT_FILE_COL_SIZE, "PeriodicRelease", sub_ph);
			num_bw = fprintf(fs, "%-*s= True\n", SUBMIT_FILE_COL_SIZE, "Hold");
			free(sub_ph);
		}
	} else if (strcmp(ja->name, DRMAA_JOB_NAME) == 0) {
		num_bw = fprintf(fs, "%-*s= \"%s\"\n", SUBMIT_FILE_COL_SIZE, "+JobName", ja->val.value);
	} 
#define REMOVE_COLON(sub_ph)						\
	int length = strlen(sub_ph);					\
	int offset = strstr(sub_ph, ":") - sub_ph;			\
	int new_length = length-(offset+1);				\
	memmove(sub_ph, sub_ph+offset+1, new_length);			\
	sub_ph[new_length] = '\0';
	
	else if (strcmp(ja->name, DRMAA_INPUT_PATH) == 0) {
		sub_ph = substitute_placeholders(ja->val.value, index);
		// take string behind colon, which is mandatory in the argument
		REMOVE_COLON(sub_ph);
		num_bw = fprintf(fs, "%-*s= %s\n", SUBMIT_FILE_COL_SIZE, "Input", sub_ph);

		if (strchr(transfer_files, 'i'))
			num_bw = fprintf(fs, "transfer_input_files=%s\n", sub_ph);

		free(sub_ph);
	} else if (strcmp(ja->name, DRMAA_OUTPUT_PATH) == 0) {
		sub_ph = substitute_placeholders(ja->val.value, index);
		// take string behind colon, which is mandatory in the argument
		// BAD BUG: doing strcpy over overlapping memory regions is a terrible idea
		/*strcpy(sub_ph, strstr(sub_ph, ":") + sizeof(char));*/
		//FIX : use memmove
		REMOVE_COLON(sub_ph);
		num_bw = fprintf(fs, "%-*s= %s\n", SUBMIT_FILE_COL_SIZE, "Output", sub_ph);
		// set error path to the same value in case of join_files
		// there is no explicit solution in Condor               
		if (joinFiles) {
			num_bw = fprintf(fs, "%-*s= %s\n", SUBMIT_FILE_COL_SIZE, "Error", sub_ph);
		}
		free(sub_ph);
	}
	// consider users error atrribute only when join_files is not present
	else if (strcmp(ja->name, DRMAA_ERROR_PATH) == 0 && !joinFiles) {
		sub_ph = substitute_placeholders(ja->val.value, index);
		// take string behind colon, which is mandatory in the argument
		REMOVE_COLON(sub_ph);
		num_bw = fprintf(fs, "%-*s= %s\n", SUBMIT_FILE_COL_SIZE, "Error", sub_ph);
		free(sub_ph);
	}

	/*
	 * // TODO
	 * #define DRMAA_DEADLINE_TIME "drmaa_deadline_time"
	 * #define DRMAA_WCT_HLIMIT "drmaa_wct_hlimit"
	 * #define DRMAA_WCT_SLIMIT "drmaa_wct_slimit"
	 * #define DRMAA_DURATION_HLIMIT "drmaa_durartion_hlimit"
	 * #define DRMAA_DURATION_SLIMIT "drmaa_durartion_slimit"
	 */
	else if (strcmp(ja->name, DRMAA_TRANSFER_FILES) == 0) {
		if (strlen(ja->val.value) > 0) {
			/* XXX output and error transfer cannot be controled when we enable this */
			fprintf(fs, "%-*s= IF_NEEDED\n", SUBMIT_FILE_COL_SIZE, "should_transfer_files");
			fprintf(fs, "%-*s= ON_EXIT\n", SUBMIT_FILE_COL_SIZE, "when_to_transfer_output");
		}
		num_bw = 0;
	} else if (strcmp(ja->name, DRMAA_V_ARGV) == 0) {
		fprintf(fs, "%-*s= ", SUBMIT_FILE_COL_SIZE, "Arguments");
		num_bw = write_v_job_attr(fs, ja);
	} else if (strcmp(ja->name, DRMAA_V_ENV) == 0) {
		fprintf(fs, "%-*s= ", SUBMIT_FILE_COL_SIZE, "Environment");
		num_bw = write_v_job_attr(fs, ja);
	} else if (strcmp(ja->name, DRMAA_JOIN_FILES) == 0) {
		// attribute is considered in INPUT_PATH, ERROR_PATH, OUTPUT_PATH
		num_bw = 0;
	} else if (strcmp(ja->name, DRMAA_JOB_CATEGORY) == 0) {
		// attribute is considered outside, so it is always written at the end of file
		num_bw = 0;
	} else if (strcmp(ja->name, DRMAA_V_EMAIL) == 0) {
		fprintf(fs, "%-*s= ", SUBMIT_FILE_COL_SIZE, "Notify_user");
		num_bw = write_v_job_attr(fs, ja);
	}

	if (num_bw >= 0)
		result = SUCCESS;
	else {
		DEBUG_PRINT1("Cannot write job attribute to submit file, name \"%s\" is unknown\n", ja->name);
	}
	return result;
}

int
write_v_job_attr(FILE *fs, const job_attr_t * ja)
{
	unsigned i;
	int result = 0;

	if (ja->num_values == 1)
		result = fprintf(fs, "%s\n", ja->val.value);
	else {
		for (i = 0; i < ja->num_values; i++) {
			if ((result += fprintf(fs, "%s", ja->val.values[i]) < 0))
				break;

			// Space DRMAA_V_ENV values
			if (strcmp(ja->name, DRMAA_V_ENV) == 0 && (i + 1) < ja->num_values)
				fprintf(fs, ";");	// TODO: Unix vs. Windows

			fprintf(fs, " ");
		}
		result += fprintf(fs, "\n");
	}

	return result;
}

int
submit_job(char *job_id, size_t job_id_len, const char *submit_file_name, char *error_diagnosis, size_t error_diag_len, char* username)
{
	FILE *fs;
	char buffer[MAX_READ_LEN] = "";
	char last_buffer[MAX_READ_LEN] = "error reading output from condor_submit";
	char cmd[SUBMIT_CMD_LEN];
	char cluster_num[MAX_JOBID_LEN];
	char job_num[MAX_JOBID_LEN];
	int got_jobs;

	// Prepare command
#ifdef WIN32
	sprintf(cmd, "%s %s", SUBMIT_CMD, submit_file_name);
#else
	if(username)
	{
	  /*fprintf(stderr,"Running as user %s\n",username);*/
	  sprintf(cmd, "sudo -E -u %s /opt/condor/bin/condor_submit %s 2>&1", username, submit_file_name);
	}
	else
	  sprintf(cmd, "%s %s 2>&1", SUBMIT_CMD, submit_file_name);
#endif

	// Submit to condor
	fs = popen(cmd, "r");
	if (fs == NULL) {
		snprintf(error_diagnosis, error_diag_len, "Unable to perform condor_submit call");
		return DRMAA_ERRNO_NO_MEMORY;
	} else if (fs == (FILE *)-1) {
		snprintf(error_diagnosis, error_diag_len, "Submit call failed");
		return DRMAA_ERRNO_DRM_COMMUNICATION_FAILURE;
	}

	got_jobs = 0;

	// Parse output - look for "<X> job<s> submitted to cluster <#>" line
	for (;;) {

		do {
			if (fgets(buffer, MAX_READ_LEN, fs) == NULL) {
				pclose(fs);

				if (got_jobs > 0)
					return DRMAA_ERRNO_SUCCESS;

				strlcpy(error_diagnosis, last_buffer, error_diag_len);
				return DRMAA_ERRNO_DENIED_BY_DRM;
			}

			strcpy(last_buffer, buffer);

			if (strstr(buffer, "ERROR: ") != NULL) {
				DEBUG_PRINT1("condor_submit wrote error message: %s\n", buffer);
				pclose(fs);
				strlcpy(error_diagnosis, buffer, error_diag_len);
				// XXX maybe some other error
				return DRMAA_ERRNO_INVALID_ATTRIBUTE_VALUE;
			}

		} while (strstr(buffer, "submitted to cluster") == NULL);

		// TODO: May have warnings.  If warnings, remove job, copy warnings
		// into error_diag, and return error

		// Parse job number and cluster number
		sscanf(buffer, "%s job(s) submitted to cluster %s", job_num, cluster_num);
		cluster_num[strlen(cluster_num) - 1] = '\0';	// squash trailing period

		got_jobs++;

		// Verify job_id_len is large enough
		if ((strlen(schedd_name) + strlen(cluster_num) + strlen(job_num)
		     + 1 + (2 * strlen(JOBID_TOKENIZER))) > job_id_len) {
			pclose(fs);
			snprintf(error_diagnosis, error_diag_len, "job_id is too small");
			return DRMAA_ERRNO_INVALID_ARGUMENT;
		}

		// Fill job_id with <schedd name.cluster id.job id>
		sprintf(job_id, "%s%s%s%s0", schedd_name, JOBID_TOKENIZER, cluster_num, JOBID_TOKENIZER);
		job_id += strlen(job_id) + 1;
	}

	return DRMAA_ERRNO_SUCCESS;
}

int
is_valid_stat(const int stat)
{
	return stat >= STAT_ABORTED;
}

int
is_valid_job_id(const char *job_id)
{
	return (job_id != NULL && strlen(job_id) >= MIN_JOBID_LEN && strlen(job_id) + 1 < MAX_JOBID_LEN);
}

FILE *
open_log_file(const char *job_id)
{
	char filename[MAX_FILE_NAME_LEN];
	snprintf(filename, sizeof(filename), "%s%s%s%s", file_dir, LOG_FILE_PREFIX, job_id, LOG_FILE_EXTN);
	return fopen(filename, "r");
}

/*
 * FILE*
 * open_newest_log_file()
 * {
 * int firstRun=0;
 * time_t newest_time;
 * char newest_name[MAX_FILE_NAME_LEN];
 * char cur_name[MAX_FILE_NAME_LEN];
 * DIR *dir;
 * struct dirent *ent;
 * struct stat finfo;
 * 
 * // open log directory
 * char log_path[MAX_FILE_NAME_LEN];
 * snprintf(log_path, MAX_FILE_NAME_LEN-1, "%s%s", file_dir, LOG_FILE_DIR);
 * dir=opendir(log_path);
 * 
 * // find newest file in log directory
 * while (0!=(ent=readdir(dir)))
 * {
 * if (0!=strcmp(ent->d_name, ".") && 0!=strcmp(ent->d_name, "..")) {
 * snprintf(cur_name,MAX_FILE_NAME_LEN,"%s%s%s",file_dir, LOG_FILE_DIR, ent->d_name);
 * if (0!=stat(cur_name,&finfo)) {
 * return DRMAA_ERRNO_INTERNAL_ERROR;
 * }
 * // ensure that we use the first valid file as default
 * if (firstRun && finfo.st_mtime > 0) 
 * {
 * newest_time = finfo.st_mtime;
 * strncpy(newest_name,cur_name,MAX_FILE_NAME_LEN-1);
 * firstRun=1;
 * }
 * else if(difftime(newest_time, finfo.st_mtime) > 0)
 * {
 * newest_time = finfo.st_mtime;
 * strncpy(newest_name,cur_name,MAX_FILE_NAME_LEN-1);
 * }
 * }
 * }
 * closedir(dir);
 * // open it
 * char log_file_nm[MAX_FILE_NAME_LEN];
 * snprintf(log_file_nm, MAX_FILE_NAME_LEN-1, "%s%s%s", file_dir,
 * LOG_FILE_DIR, newest_name);
 * return fopen(log_file_nm, "r");
 * }
 */

int
rm_log_file(const char *job_id)
{
	char filename[MAX_FILE_NAME_LEN];
	snprintf(filename, sizeof(filename), "%s%s%s%s", file_dir, LOG_FILE_PREFIX, job_id, LOG_FILE_EXTN);
#ifndef DEBUG
	return remove(filename);
#else
	return remove(filename);
#endif
}

static time_t
parse_time(const char *line)
{
#ifdef HAVE_STRPTIME
	time_t now;
	struct tm t;
	const char *p;

        now = time(NULL);
        localtime_r(&now, &t);

	/* 000 (34374.000.000) 07/10 15:19:02 Job submitted from host: <150.254.166.137:56958> */
	if (!(p = strchr(line, ')')))
		return 0;
	p++;

	strptime(p, "%m/%e %H:%M:%S", &t);

	return mktime(&t);
#else
	return (time_t) 0;
#endif
}

int
scan_file(FILE *logFS, int get_stat_rusage, int *stat, drmaa_attr_values_t **rusage)
{
	char line[MAX_LOG_FILE_LINE_LEN], r_val[MAX_LOG_FILE_LINE_LEN];
	char *termStr = NULL;
	int found_job_term = 0;
	int job_exit_val = 0;
	int got_core_file = 0;
	time_t end_time = 0, start_time = 0, submission_time = 0;

	while (!found_job_term && fgets(line, sizeof(line), logFS) != NULL) {

		if (strstr(line, "Job submitted from host") && !submission_time)
			submission_time = parse_time(line);

		if (strstr(line, "Job executing on host") && !start_time)
			start_time = parse_time(line);

		if (strstr(line, "Job terminated") != NULL) {
			found_job_term = 1;

			//DEBUG_PRINT1("Job term line: %s\n", line);

			if (get_stat_rusage) {

				// scan further for status info
				sleep_ms(50);	// wait for further I/O

				if (fgets(line, sizeof(line), logFS) != NULL) {

					if (strstr(line, "Normal termination") != NULL) {
						end_time = parse_time(line);

						sscanf(line, "%*s Normal termination (return "
						       "value %d)", &job_exit_val);

						if (job_exit_val > -1)
							*stat = STAT_NOR_BASE + job_exit_val;
						else
							*stat = STAT_NOR_BASE;
					} else if ((termStr = strstr(line, "Abnormal termination (signal"))
						   != NULL) {

						end_time = parse_time(line);

						sscanf(termStr, "Abnormal termination (signal %d)",
						       &job_exit_val);
						*stat = condor_sig_to_drmaa(job_exit_val);
						// check next line for reference to core file
						fgets(line, sizeof(line), logFS);
						if (strstr(line, "Corefile in:") != NULL)
							got_core_file = 1;
					} else
						*stat = STAT_UNKNOWN;	// really "abnormal term"
				}

				if (got_core_file)
					*stat = *stat + STAT_SIG_CORE_BASE - 1;

				DEBUG_PRINT1("Resulting stat value is %u\n", *stat);

				// scan further for rusage data
				if (rusage != NULL) {
					char buf[128];


					sleep_ms(50);	// wait for further I/O

					*rusage = create_dav();

					while (fgets(line, sizeof(line), logFS) != NULL) {
						if (strstr(line, "Run Bytes Sent By Job") != NULL) {
							sscanf(line, "%s - Run Bytes Sent By Job", r_val);
							snprintf(buf, sizeof(buf), "run_bytes_sent=%s", r_val);
							add_dav(*rusage, buf);
							break;
						}

						// TODO: other rusage values
					}

					if (submission_time) {
						snprintf(buf, sizeof(buf), "submission_time=%u", (unsigned int)submission_time);
						add_dav(*rusage, buf);
					}

					if (submission_time && start_time) {
						snprintf(buf, sizeof(buf), "start_time=%u", (unsigned int)start_time);
						add_dav(*rusage, buf);
					}

					if (submission_time && start_time && end_time) {
						snprintf(buf, sizeof(buf), "end_time=%u", (unsigned int)end_time);
						add_dav(*rusage, buf);
					}

					DEBUG_PRINT3("RUsage data: submission_time=%d, start_time=%d, end_time=%d\n", (int)submission_time, (int)start_time, (int)end_time);
				}
			}

		} else if ((strstr(line, "Job not properly linked for Condor")
			    != NULL) || (strstr(line, "aborted") != NULL)) {
			found_job_term = 1;
			if (get_stat_rusage)
				*stat = STAT_ABORTED;
		}
	}

	return found_job_term;
}

FILE *
open_next_mod_log_file(condor_drmaa_job_info_t *list, char *job_id, time_t time_limit, int *firstpass)
{
	struct stat finfo;
	char filename[MAX_FILE_NAME_LEN];
	condor_drmaa_job_info_t *cur, *tmp, *result = NULL;
	time_t actTime;


	job_id[0] = 0;

	cur = list;

	// check if there are some files that have never been scanned so far
	// if so, then start with them and do not bother sleeping until all are
	// scanned at least once
	*firstpass = 0;

	for (tmp = list; tmp; tmp = tmp->next) {
		if (tmp->lastmodtime == 0) {

			DEBUG_PRINT1("File %s not scanned yet...\n", cur->id);
			cur = tmp;
			*firstpass = 1;
			break;
		}
	}

	for (;;) {

		// determine mtime of current log file
		snprintf(filename, sizeof(filename), "%s%s%s%s", file_dir, LOG_FILE_PREFIX,
			 cur->id, LOG_FILE_EXTN);

		// DEBUG_PRINT2("(%p) Checking stat of %s\n", pthread_self(),filename);
		if (0 != stat(filename, &finfo)) {
			strlcpy(job_id, cur->id, MAX_JOBID_LEN);
			return NULL;
		}

		// check if modification time is newer than the last check time
		if (cur->lastmodtime < finfo.st_mtime) {
			// DEBUG_PRINT2("(%p) Found modified %s\n", pthread_self(),filename);
			// return this file for further inspection
			cur->lastmodtime = (long)finfo.st_mtime;
			result = cur;
			break;
		}

		time(&actTime);
		if (time_limit != 0 &&  actTime >= time_limit) {
			DEBUG_PRINT2("Timed out in open_next_mod_log_file(), current time %s, time limit %s \n",ctime(&actTime), ctime(&time_limit));
			return (FILE *)-1;
		}

		MUTEX_LOCK(session_lock);
		
		// someone called drmaa_exit() meanwhile, exit with time out error
		if (session_state == INACTIVE) {
			DEBUG_PRINT1("Somebody called drmaa_exit() during drmaa_wait(), returning wait timeout for %s\n",filename);
			MUTEX_UNLOCK(session_lock);
			return (FILE *)-1;
		}

		MUTEX_UNLOCK(session_lock);

		cur = cur->next;
		if (!cur)
			cur = list;

		// UGLY HACK: slow down rate at which we spin
		sleep_ms(25);
	}

	DEBUG_PRINT1("Searching for finish message in %s\n", filename);

	assert(result);
	strlcpy(job_id, result->id, MAX_JOBID_LEN);
	return fopen(filename, "r");
}

int
wait_job(const char *job_id, char *job_id_out, size_t job_id_out_len,
	 const int dispose, const int get_stat_rusage,
	 int *stat, signed long timeout, const time_t start,
	 drmaa_attr_values_t **rusage, char *error_diagnosis, size_t error_diag_len)
{
	int result;
	int time_up = 0, found_job_term = 0, waited_jobs = 0;
	FILE *logFS;
	char waited_job_id[MAX_JOBID_LEN] = "";
	condor_drmaa_job_info_t *cur, *waited_list;
	int wait_for_any;
	int firstpass;

	DEBUG_PRINT1("-> wait_job(%s)\n", job_id);

	wait_for_any = !strcmp(job_id, DRMAA_JOB_IDS_SESSION_ANY);

	if (get_stat_rusage && rusage != NULL)
		*rusage = NULL;

	// Initialize
	MUTEX_LOCK(job_list_lock);

	if (wait_for_any) {
		int jobs_in_session = 0;

		for (cur = job_list; cur; cur = cur->next) {
			if (cur->state != DISPOSED)
				jobs_in_session++;
		}

		if (jobs_in_session == 0) {
			MUTEX_UNLOCK(job_list_lock);
			snprintf(error_diagnosis, error_diag_len, "DRMAA_JOB_IDS_SESSION_ANY for empty session");
			return DRMAA_ERRNO_INVALID_JOB;
		}

		// Make our internal copy of jobs to wait for and increment
		// reference counters in the source list. This way we can
		// be sure that nobody removes the log file in the meantime
		// and we don't have to lock the job list while waiting.
		waited_list = copy_job_list(job_list);
		waited_jobs = jobs_in_session;

	} else {

		// return error if job was already reaped
		if (!(cur = get_job_info(job_id)) || cur->state == DISPOSED) {
			MUTEX_UNLOCK(job_list_lock);
			return standard_drmaa_error(DRMAA_ERRNO_INVALID_JOB, error_diagnosis, error_diag_len);
		}

		waited_list = copy_job(cur);
		waited_jobs = 1;
	}

	MUTEX_UNLOCK(job_list_lock);

	logFS = NULL;
	firstpass = 1;

	// Scan for completion event within timeframe
	for (;;) {

		if (!wait_for_any) {

			// open once, then just rewind
			if (!logFS) {
				logFS = open_log_file(job_id);
				strlcpy(waited_job_id, job_id, sizeof(waited_job_id));
			} else
				rewind(logFS);

		} else {

			// just scan once through all log files, one by one
			if (timeout == DRMAA_TIMEOUT_NO_WAIT) {
				condor_drmaa_job_info_t *p;
				int i;

				waited_jobs--;

				for (i = 0, p = waited_list; i != waited_jobs; p = p->next, i++)
					continue;

				assert(p);

				if (logFS)
					fclose(logFS);
				logFS = open_log_file(p->id);
				strlcpy(waited_job_id, p->id, sizeof(waited_job_id));

			} else {
				time_t t;

				if (timeout == DRMAA_TIMEOUT_WAIT_FOREVER)
					t = 0;
				else
					t = start + timeout;

				if (logFS)
					fclose(logFS);
				logFS = open_next_mod_log_file(waited_list, waited_job_id, t, &firstpass);
			}
		}

		// timed out while searching for next file to open
		if (logFS == (FILE *)-1)
			break;

		// log file was removed, should never happen
		if (logFS == NULL) {
			snprintf(error_diagnosis, error_diag_len, "Log file was removed unexpectedly");
			result = DRMAA_ERRNO_INTERNAL_ERROR;
			goto cleanup;
		}

		found_job_term = scan_file(logFS, get_stat_rusage, stat, rusage);

		// check if time is up
		if (timeout != DRMAA_TIMEOUT_WAIT_FOREVER && timeout != DRMAA_TIMEOUT_NO_WAIT && difftime(time(NULL), start) >= timeout) {
			DEBUG_PRINT1("Wait timeout detected after scanning file for %s\n",waited_job_id);
			time_up = 1;
		}

		// break if we scanned all files and we should not wait, or time is up, or we found something
		if (!waited_jobs || time_up || found_job_term)
			break;

		MUTEX_LOCK(session_lock);

		// someone called drmaa_exit() meanwhile
		if (session_state == INACTIVE) {
			MUTEX_UNLOCK(session_lock);
			break;
		}

		MUTEX_UNLOCK(session_lock);

		// do not sleep until we scan all the files for the first time
		// this will also not sleep if NO_WAIT is used
		if (firstpass && wait_for_any)
			continue;

		if (timeout != DRMAA_TIMEOUT_WAIT_FOREVER && timeout != DRMAA_TIMEOUT_NO_WAIT)
			DEBUG_PRINT2("Sleeping until next check cycle, %6.0f from %lu seconds timeout elapsed\n",difftime(time(NULL), start), timeout );
		else
			DEBUG_PRINT0("Sleeping until next check cycle");
		sleep_ms(WAIT_SLP_TM);
	}

	// close that last file
	if (logFS && logFS != (FILE *)-1) {
		fclose(logFS);
		logFS = NULL;
	}

	// prepare stuff to return appropriately
	if (found_job_term) {
		result = DRMAA_ERRNO_SUCCESS;

		if (job_id_out != NULL) {

			// user wants to know the name of the ended job
			if (wait_for_any) {
				DEBUG_PRINT1("Got %s while waiting for any job\n", waited_job_id);
				strlcpy(job_id_out, waited_job_id, job_id_out_len);

			} else {
				assert(!strcmp(job_id, waited_job_id));
				strlcpy(job_id_out, job_id, job_id_out_len);
			}
		}

	} else {

		// not found job term
		if (get_stat_rusage)
			*stat = STAT_UNKNOWN;

		snprintf(error_diagnosis, error_diag_len, drmaa_strerror(DRMAA_ERRNO_EXIT_TIMEOUT));
		result = DRMAA_ERRNO_EXIT_TIMEOUT;
	}

cleanup: 

	// unreference all jobs we were waiting for
	// and free internal list
	MUTEX_LOCK(job_list_lock);

	for (cur = waited_list; cur; cur = cur->next) {
		DEBUG_PRINT1("Unreferencing job %s\n", cur->id);

		// this will decrease reference counter and may remove job info
		// if another thread marked it as DISPOSED but couldn't remove it
		// because of our reference
		rm_job(cur->id);
	}

	if (found_job_term && dispose) {

		// if nobody before us marked the job as DISPOSED, mark it so,
		// unreference and remove if possible
		if (mark_job(waited_job_id, DISPOSED) != DISPOSED) {

			DEBUG_PRINT1("Marking job %s as DISPOSED\n", waited_job_id);
			rm_job(waited_job_id);
		}
	}

	free_list(&waited_list);

	MUTEX_UNLOCK(job_list_lock);

	DEBUG_PRINT1("<- wait_job(%s)\n", job_id);

	return result;
}

drmaa_attr_values_t *
create_dav(void)
{
	drmaa_attr_values_t *dav = malloc(sizeof(drmaa_attr_values_t));

	if (dav) {
		dav->values = NULL;
		dav->index = 0;
		dav->size = 0;
	}

	return dav;
}

int add_dav(drmaa_attr_values_t *dav, const char *val)
{
	char *v;
	char **ptr;

	if (!dav)
		return -1;

	v = strdup(val);
	if (!v)
		return -1;

	ptr = realloc(dav->values, (dav->size + 1) * sizeof(char **));
	if (!ptr) {
		free(v);
		return -1;
	}

	dav->values = ptr;

	dav->values[dav->size] = v;
	dav->size++;

	return 0;
}

void destroy_dav(drmaa_attr_values_t *dav)
{
	int i;

	if (!dav)
		return;

	for (i = 0; i < dav->size; i++) {
		if (dav->values[i])
			free(dav->values[i]);
	}

	free(dav->values);
	free(dav);
}

int
get_job_status(const char *jobid)
{
	condor_drmaa_job_info_t *cur;
	int result = -1;

	for (cur = job_list; cur; cur = cur->next) {

		if (strcmp(cur->id, jobid) == 0) {
			result = cur->state;
			break;
		}
	}

	DEBUG_PRINT2("Job status for \"%s\" is %d\n", jobid, result);
	return result;
}

condor_drmaa_job_info_t *
get_job_info(const char *jobid)
{
	condor_drmaa_job_info_t *cur;
	
	for (cur = job_list; cur; cur = cur->next) {

		if (!strcmp(jobid, cur->id))
			return cur;
	}

	return NULL;
}

condor_drmaa_job_info_t *
copy_job(condor_drmaa_job_info_t *job)
{
	condor_drmaa_job_info_t *res;

	res = create_job_info(job->id);
	res->state = job->state;

	job->ref_count++;

	return res;
}

condor_drmaa_job_info_t *
copy_job_list(condor_drmaa_job_info_t *list)
{
	condor_drmaa_job_info_t *res, *last, *tmp;

	res = NULL;
	last = NULL;

	for (;list; list = list->next) {

		if (list->state == DISPOSED)
			continue;

		// increment reference counter in the source so nobody removes it (and log file most importantly)
		list->ref_count++;
		//DEBUG_PRINT3("Referencing job %s (%d -> %d)\n", list->id, list->ref_count - 1, list->ref_count);

		tmp = create_job_info(list->id);
		tmp->state = list->state;

		if (last)
			last->next = tmp;
		else
			res = tmp;

		last = tmp;
	}

	return res;
}

int
free_job_list(void)
{
	condor_drmaa_job_info_t *cur, *tmp;

	for (cur = job_list; cur;) {
		tmp = cur;
		cur = cur->next;

		if (tmp->ref_count > 0)
			continue;

		rm_log_file(tmp->id);
		destroy_job_info(tmp);

		num_jobs--;
		assert(num_jobs >= 0);
	}

	if (num_jobs == 0)
		job_list = NULL;

	return num_jobs;
}

int
free_list(condor_drmaa_job_info_t **list)
{
	condor_drmaa_job_info_t *cur, *tmp;

	for (cur = *list; cur;) {
		tmp = cur;
		cur = cur->next;

		destroy_job_info(tmp);
	}

	*list = NULL;

	return 0;
}

int
rm_job(const char *job_id)
{
	condor_drmaa_job_info_t *cur, *last;

	for (last = cur = job_list; cur; cur = cur->next) {

		if (strcmp(cur->id, job_id) == 0) {

			cur->ref_count--;

			if (cur->ref_count >= 0) {
				DEBUG_PRINT3("Not removing job %s yet (ref_count: %d -> %d)\n", job_id, cur->ref_count + 1, cur->ref_count);
				return 0;
			}

			// if job wasn't marked as DISPOSED, then we're just unreferencing it
			// the last thread using it will reap job info
			if (cur->state != DISPOSED) {
				last = cur;
				continue;
			}

			DEBUG_PRINT5("Removing job info for %s (%p, %p, %p, %u)\n",
				     job_id, job_list, cur, cur->next, num_jobs);

			if (cur == job_list)
				job_list = cur->next;
			else
				last->next = cur->next;

			rm_log_file(job_id);
			destroy_job_info(cur);

			num_jobs--;
			assert(num_jobs >= 0);

			if (num_jobs == 0)
				job_list = NULL;
			return 0;
		}

		last = cur;
	}

	return -1;
}

int
mark_job(const char *job_id, int state)
{
	condor_drmaa_job_info_t *cur;
	int previous_state;

	for (cur = job_list; cur; cur = cur->next) {

		if (strcmp(cur->id, job_id) == 0) {
			previous_state = cur->state;
			cur->state = state;
			return previous_state;
		}
	}

	return -1;
}

int
get_base_dir(void)
{
	char *dir;
	struct stat s;

	// ala condor_c++_util/directory.C's temp_dir_path()
	dir = getenv("TEMP");
	if (!dir)
		dir = getenv("TMP");
	if (!dir)
		dir = getenv("SPOOL");
	if (dir) {
		dir = strdup(dir);
	} else {
#ifdef WIN32
		dir = strdup("c:\\Temp\\");
#else
		dir = strdup("/tmp/");
#endif
		if (stat(dir, &s) != 0 || !S_ISDIR(s.st_mode)) {
			free(dir);
#ifdef WIN32
			dir = strdup("c:\\");
#else
			dir = strdup("/");
#endif
		}
	}

#ifdef WIN32
	if (dir[strlen(dir) - 1] == '\\') {
#else
	if (dir[strlen(dir) - 1] == '/') {
#endif
		strlcpy(file_dir, dir, FILEDIR_BUFSIZE);
	} else {
		strlcpy(file_dir, dir, FILEDIR_BUFSIZE);
#ifdef WIN32
		strlcat(file_dir, "\\", FILEDIR_BUFSIZE);
#else
		strlcat(file_dir, "/", FILEDIR_BUFSIZE);
#endif
	}

	free(dir);
	return 1;
}

#define PRINT_COMMAND(cmd_array, username, command, schedd_name, clu_proc, redirect)						\
    if(username == 0 || username[0] == '\0')	/*0-length string*/								\
	snprintf(cmd_array, sizeof(cmd_array), "%s %s %s%s", command, schedd_name, clu_proc, redirect);				\
    else															\
	snprintf(cmd_array, sizeof(cmd_array), "sudo -E -u %s /opt/condor/bin/%s %s %s%s", username, command, schedd_name, clu_proc, redirect);

int
hold_job(const char *jobid, char *error_diagnosis, size_t error_diag_len, char* username)
{
	char cmd[HOLD_CMD_LEN];
	char clu_proc[MAX_JOBID_LEN], buf[MAX_READ_LEN];
	FILE *fs;
	const char *redirect;

#ifdef WIN32
	redirect = "";
#else
	redirect = " 2>&1";
#endif

	// prepare command: "condor_hold -name scheddname cluster.process"
	if (strstr(jobid, schedd_name) != jobid) {
		snprintf(error_diagnosis, error_diag_len, "Unexpected job id format");
		return DRMAA_ERRNO_INVALID_JOB;
	}

	strcpy(clu_proc, jobid + strlen(schedd_name) + 1);	// 1 for schedd.clu.proc
	PRINT_COMMAND(cmd, username, HOLD_CMD, schedd_name, clu_proc, redirect);

	// execute command
	fs = popen(cmd, "r");
	if (fs == NULL) {
		snprintf(error_diagnosis, error_diag_len, "Unable to perform hold call");
		return DRMAA_ERRNO_NO_MEMORY;
	} else if (fs == (FILE *)-1) {
		snprintf(error_diagnosis, error_diag_len, "Hold call failed");
		return DRMAA_ERRNO_DRM_COMMUNICATION_FAILURE;
	}

	// Parse the last line of output for success/failure
	buf[0] = '\0';
	while (fgets(buf, MAX_READ_LEN, fs) != NULL)
		continue;

	pclose(fs);

	// "Job $cluster.$proc held"
	// "Job $cluster.$proc already held"
	// "Job $cluster.$proc not found"
	// "condor_hold: Can't find address for schedd $scheddname"
	if (strstr(buf, "Job") != NULL) {

		if (strstr(buf, "not found") != NULL) {
			return standard_drmaa_error(DRMAA_ERRNO_INVALID_JOB, error_diagnosis, error_diag_len);
		} else if (strstr(buf, "held") != NULL) {
			return DRMAA_ERRNO_SUCCESS;
		} else {
			return standard_drmaa_error(DRMAA_ERRNO_HOLD_INCONSISTENT_STATE, error_diagnosis, error_diag_len);
		}

	} else {
		snprintf(error_diagnosis, error_diag_len, "%s", buf);
		return DRMAA_ERRNO_DRM_COMMUNICATION_FAILURE;
	}
}

int
release_job(const char *jobid, char *error_diagnosis, size_t error_diag_len, char* username)
{
	char cmd[RELEASE_CMD_LEN];
	char clu_proc[MAX_JOBID_LEN], buf[MAX_READ_LEN];
	FILE *fs;
	const char *redirect;

#ifdef WIN32
	redirect = "";
#else
	redirect = " 2>&1";
#endif

	// prepare command: "condor_release -name schedddname cluster.process"
	if (strstr(jobid, schedd_name) != jobid) {
		snprintf(error_diagnosis, error_diag_len, "Unexpected job id format");
		return DRMAA_ERRNO_INVALID_JOB;
	}

	// 1 for schedd.clu.proc
	snprintf(clu_proc, sizeof(clu_proc), "%s", jobid + strlen(schedd_name) + 1);
	PRINT_COMMAND(cmd, username, RELEASE_CMD, schedd_name, clu_proc, redirect);

	// execute command
	DEBUG_PRINT1("Performing release operation: %s\n", cmd);

	fs = popen(cmd, "r");
	if (fs == NULL) {
		snprintf(error_diagnosis, error_diag_len, "Unable to perform release call");
		return DRMAA_ERRNO_NO_MEMORY;
	} else if (fs == (FILE *)-1) {
		snprintf(error_diagnosis, error_diag_len, "Release call failed");
		return DRMAA_ERRNO_DRM_COMMUNICATION_FAILURE;
	}

	// Parse the last line of output for success/failure
	buf[0] = '\0';
	while (fgets(buf, MAX_READ_LEN, fs) != NULL)
		continue;

	pclose(fs);

	// condor_release: unknown host schedd
	// Invalid cluster # from 0.0.
	// Warning: unrecognized ".0" skipped
	// Job 1.0 not found
	// Job 939091.0 released
	// Job 939091.0 not held to be released

	if (strstr(buf, "Job") != NULL) {

		if (strstr(buf, "not found") != NULL)
			return standard_drmaa_error(DRMAA_ERRNO_INVALID_JOB, error_diagnosis, error_diag_len);
		else if (strstr(buf, "not held to be released") != NULL) {
			return standard_drmaa_error(DRMAA_ERRNO_RELEASE_INCONSISTENT_STATE, error_diagnosis, error_diag_len);
		} else
			return DRMAA_ERRNO_SUCCESS;

	} else {
		snprintf(error_diagnosis, error_diag_len, "%s", buf);
		return DRMAA_ERRNO_DRM_COMMUNICATION_FAILURE;
	}
}

int
terminate_job(const char *jobid, char *error_diagnosis, size_t error_diag_len, char* username)
{
	char cmd[TERMINATE_CMD_LEN];
	char clu_proc[MAX_JOBID_LEN], buf[MAX_READ_LEN];
	FILE *fs;
	const char *redirect;

#ifdef WIN32
	redirect = "";
#else
	redirect = " 2>&1";
#endif

	// prepare command: "condor_rm -name schedddname cluster.process"
	if (strstr(jobid, schedd_name) != jobid) {
		snprintf(error_diagnosis, error_diag_len, "Unexpected job id format");
		return DRMAA_ERRNO_INVALID_JOB;
	}

	// 1 for schedd.clu.proc
	snprintf(clu_proc, sizeof(clu_proc), "%s", jobid + strlen(schedd_name) + 1);
	PRINT_COMMAND(cmd, username, TERMINATE_CMD, schedd_name, clu_proc, redirect);

	// execute command
	fs = popen(cmd, "r");
	if (fs == NULL) {
		snprintf(error_diagnosis, error_diag_len, "Unable to perform terminate call");
		return DRMAA_ERRNO_NO_MEMORY;
	} else if (fs == (FILE *)-1) {
		snprintf(error_diagnosis, error_diag_len, "Terminate call failed");
		return DRMAA_ERRNO_DRM_COMMUNICATION_FAILURE;
	}

	// Parse the last line of output for success/failure
	buf[0] = '\0';
	while (fgets(buf, MAX_READ_LEN, fs) != NULL)
		continue;

	pclose(fs);

	// Job 939609.0 marked for removal
	// Job 939609.0 not found
	// condor_rm: Can't find address for schedd $scheddname
	if (strstr(buf, "Job") != NULL) {

		if (strstr(buf, "not found") != NULL)
			return standard_drmaa_error(DRMAA_ERRNO_INVALID_JOB, error_diagnosis, error_diag_len);
		else if (strstr(buf, "marked for removal") != NULL)
			return DRMAA_ERRNO_SUCCESS;
		else
			return standard_drmaa_error(DRMAA_ERRNO_INTERNAL_ERROR, error_diagnosis, error_diag_len);

	} else {
		snprintf(error_diagnosis, error_diag_len, "%s", buf);
		return DRMAA_ERRNO_DRM_COMMUNICATION_FAILURE;
	}
}

int
get_schedd_name(void)
{
#ifdef WIN32
	char tmp[1024];
	DWORD bufsize = sizeof(tmp);

	if (GetComputerNameEx(ComputerNameDnsFullyQualified, tmp, &bufsize)) {
		strlcpy(schedd_name, tmp, SCHEDD_NAME_BUFSIZE);
		return 0;
	}
#else
	struct utsname host_info;

	if (uname(&host_info) == 0) {
		strlcpy(schedd_name, host_info.nodename, SCHEDD_NAME_BUFSIZE);
		return 0;
	}
#endif

	return -1;
}

int
get_job_status_logfile(const char *job_id, int *remote_ps, char *error_diagnosis, size_t error_diag_len)
{
	FILE *logFS;
	char line[MAX_LOG_FILE_LINE_LEN];
	char state[128] = "";

	logFS = open_log_file(job_id);

	if (logFS == NULL) {
		snprintf(error_diagnosis, error_diag_len, "Unable to open log file");
		return DRMAA_ERRNO_INTERNAL_ERROR;
	}

	// scan through entire file for last occurrance of one of following
	while (fgets(line, sizeof(line), logFS) != NULL) {

		if (strstr(line, "Job terminated") != NULL) {
			strcpy(state, "term");
			break;
		} else if (strstr(line, "Job was aborted by the user") != NULL) {
			strcpy(state, "fail");
			break;
		} else if (strstr(line, "Job reconnection failed") != NULL) {
			strcpy(state, "reschedule");
			break;
		} else if (strstr(line, "Job submitted from host") != NULL || strstr(line, "Job was released") != NULL)
			strcpy(state, "q_active");
		else if (strstr(line, "Job was held") != NULL)
			strcpy(state, "user_hold");
		else if (strstr(line, "Job executing on host") != NULL)
			strcpy(state, "running");
	}

	fclose(logFS);

	DEBUG_PRINT1("Determined state \"%s\" from logfile\n", state);

	if (strcmp(state, "term") == 0)
		*remote_ps = DRMAA_PS_DONE;
	else if (strcmp(state, "fail") == 0)
		*remote_ps = DRMAA_PS_FAILED;
	else if (strcmp(state, "reschedule") == 0) {
		*remote_ps = DRMAA_PS_UNDETERMINED;
		snprintf(error_diagnosis, error_diag_len, "Submission and execution host are disconnected, job status unknown, maybe it was rescheduled");
		return DRMAA_ERRNO_INTERNAL_ERROR;
	} else if (strcmp(state, "q_active") == 0) {
		if (get_job_status(job_id) == SUBMITTED_ASSUME_RUNNING)
			*remote_ps = DRMAA_PS_RUNNING;
		else
			*remote_ps = DRMAA_PS_QUEUED_ACTIVE;
	} else if (strcmp(state, "user_hold") == 0) {
		if (get_job_status(job_id) == SUSPEND)
			*remote_ps = DRMAA_PS_USER_SUSPENDED;
		else
			*remote_ps = DRMAA_PS_USER_ON_HOLD;
	} else if (strcmp(state, "running") == 0)
		*remote_ps = DRMAA_PS_RUNNING;
	else
		*remote_ps = DRMAA_PS_UNDETERMINED;

	return DRMAA_ERRNO_SUCCESS;
}

int
get_job_status_condorq(const char *jobid, int *remotePs, char *error_diagnosis, size_t error_diag_len)
{
	char cmd[QUEUE_CMD_LEN];
	char clu_proc[MAX_JOBID_LEN], buf[MAX_READ_LEN];
	FILE *fs;
	unsigned int condorStatVal;
	const char *redirect;

#ifdef WIN32
	redirect = "";
#else
	redirect = " 2>&1";
#endif

	// prepare command: "condor_q -l -name scheddname cluster.process"
	if (strstr(jobid, schedd_name) != jobid) {
		snprintf(error_diagnosis, error_diag_len, "Unexpected job id format");
		return DRMAA_ERRNO_INVALID_JOB;
	}

	strcpy(clu_proc, jobid + strlen(schedd_name) + 1);	// 1 for schedd.clu.proc
	snprintf(cmd, sizeof(cmd), "%s %s %s%s", QUEUE_CMD, schedd_name, clu_proc, redirect);

	DEBUG_PRINT1("Asking for job status with \"%s\"\n", cmd);

	// execute command
	fs = popen(cmd, "r");
	if (fs == NULL) {
		snprintf(error_diagnosis, error_diag_len, "Unable to perform condor_q call");
		return DRMAA_ERRNO_NO_MEMORY;
	} else if (fs == (FILE *)-1) {
		snprintf(error_diagnosis, error_diag_len, "condor_q call failed");
		return DRMAA_ERRNO_DRM_COMMUNICATION_FAILURE;
	}

	// Parse output for success/failure
	condorStatVal = 255;
	while (fgets(buf, MAX_READ_LEN, fs) != NULL) {

		// "JobStatus = x"
		if (sscanf(buf, "JobStatus = %u", &condorStatVal) != 0) {

			DEBUG_PRINT1("Condor status for job is %u\n", condorStatVal);

			pclose(fs);

			switch (condorStatVal) {
			case 1:
				// Idle
				*remotePs = DRMAA_PS_QUEUED_ACTIVE;
				break;
			case 2:
				// Running
				*remotePs = DRMAA_PS_RUNNING;
				break;
			case 3:
				// Removed
				// TODO is this right ?
				*remotePs = DRMAA_PS_FAILED;
				break;
			case 4:
				// Completed
				*remotePs = DRMAA_PS_DONE;
				break;
			case 5:
				// Held
				*remotePs = DRMAA_PS_USER_ON_HOLD;
				break;
			default:
				// this is strange
				strlcpy(error_diagnosis, "Unknown Condor job status for given job", error_diag_len);
				return DRMAA_ERRNO_INTERNAL_ERROR;
			}

			return DRMAA_ERRNO_SUCCESS;
		}
	}

	// nothing found  
	strlcpy(error_diagnosis, "Could not find job status for given job", error_diag_len);
	pclose(fs);
	return DRMAA_ERRNO_INVALID_JOB;
}

/** Converts a Condor log file signal number to this DRMAA
    implementation's number.
    @return signal number or 0 if no matching signal found
*/
int
condor_sig_to_drmaa(const int condor_sig)
{
	int result = 0;

#if !defined(WIN32)
	switch (condor_sig) {
	case SIGHUP:
		result = 1;
		break;
	case SIGINT:
		result = 2;
		break;
	case SIGQUIT:
		result = 3;
		break;
	case SIGILL:
		result = 4;
		break;
	case SIGABRT:
		result = 5;
		break;
	case SIGFPE:
		result = 6;
		break;
	case SIGKILL:
		result = 7;
		break;
	case SIGSEGV:
		result = 8;
		break;
	case SIGPIPE:
		result = 9;
		break;
	case SIGALRM:
		result = 10;
		break;
	case SIGTERM:
		result = 11;
		break;
	case SIGUSR1:
		result = 12;
		break;
	case SIGUSR2:
		result = 13;
		break;
	case SIGCHLD:
		result = 14;
		break;
	case SIGCONT:
		result = 15;
		break;
	case SIGSTOP:
		result = 16;
		break;
	case SIGTSTP:
		result = 17;
		break;
	case SIGTTIN:
		result = 18;
		break;
	case SIGTTOU:
		result = 19;
		break;
	}
#endif

	if (result == 0) {
		DEBUG_PRINT1("Could not resolve signal number %u from logfile to POSIX signal name.\n", condor_sig);
	}

	return result;
}
