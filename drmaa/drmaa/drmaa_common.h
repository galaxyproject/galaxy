
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

#ifndef CONDOR_DRMAA_COMMON_H
#define CONDOR_DRMAA_COMMON_H

#include <stdarg.h>
#include "auxDrmaa.h"

#define SCHEDD_NAME_BUFSIZE 1024
extern char schedd_name[];

#define FILEDIR_BUFSIZE 1024
extern char file_dir[];

extern MUTEX_TYPE job_list_lock;
extern condor_drmaa_job_info_t *job_list;
extern int num_jobs;

extern MUTEX_TYPE iniparser_lock;
extern MUTEX_TYPE session_lock;
extern int session_lock_initialized;

#ifdef __GNUC__
void debug_print(const char *format, ...) __attribute__((format(printf, 1, 2)));
#else
void debug_print(const char *format, ...);
#endif

// conditional DEBUG macro is considered in debug_print()
// implementation
#define DEBUG_PRINT0(text) debug_print(text)
#define DEBUG_PRINT1(text,arg1) debug_print(text,arg1)
#define DEBUG_PRINT2(text,arg1,arg2) debug_print(text,arg1,arg2)
#define DEBUG_PRINT3(text,arg1,arg2,arg3) debug_print(text,arg1,arg2,arg3)
#define DEBUG_PRINT4(text,arg1,arg2,arg3,arg4) debug_print(text,arg1,arg2,arg3,arg4)
#define DEBUG_PRINT5(text,arg1,arg2,arg3,arg4,arg5) debug_print(text,arg1,arg2,arg3,arg4,arg5)

#endif /* CONDOR_DRMAA_COMMON_H */
