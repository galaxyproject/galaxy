
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

/* Global variables used throughout the drmaa library */

#include <stdarg.h>
#include "auxDrmaa.h"
#include "drmaa_common.h"

#ifdef WIN32
MUTEX_TYPE session_lock;
int session_lock_initialized = 0;
#else
MUTEX_TYPE session_lock = PTHREAD_MUTEX_INITIALIZER;
int session_lock_initialized = 1;
#endif

int session_state = INACTIVE;

// The following are touched by: 
//   1) drmaa_run_jobs() - to add a job
//   2) drmaa_run_bulk_jobs() - to add a job
//   3) drmaa_control() - verifying job_id validity
//   4) drmaa_job_ps() - verifying job_id validity
//   5) drmaa_synchronize() / drmaa_wait() - to copy jobs to internal lists and
//      increment reference counters
MUTEX_TYPE job_list_lock;
condor_drmaa_job_info_t *job_list = NULL;
int num_jobs = 0;

// iniparser is not thread-safe
MUTEX_TYPE iniparser_lock;

char schedd_name[1024] = "";
char file_dir[1024] = "";

#ifdef DEBUG
void
debug_print(const char *format, ...)
{
	va_list ap;

	fprintf(stderr, "DEBUG: ");
	va_start(ap, format);
	vfprintf(stderr, format, ap);
	va_end(ap);
}
#else
void
debug_print(const char *format, ...)
{
}
#endif
