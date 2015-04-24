
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

#ifndef CONDOR_AUX_DRMAA_H
#define CONDOR_AUX_DRMAA_H

#ifdef HAVE_CONFIG_H
	#include <config.h>
#endif


#ifndef WIN32
  // we need this to get st_mtime in the stat structure
  #ifndef _POSIX_SOURCE
	#define _POSIX_SOURCE
  #endif

  #ifdef HAVE_PTHREAD_H
	#include <pthread.h>
  #endif

  #if HAVE_STDBOOL_H
    #include <stdbool.h>
  #else
    #if ! HAVE__BOOL
     #define _Bool signed char
    #endif
    # define bool _Bool
    # define false 0
    # define true 1
  #endif


  #define sleep_ms(x) usleep((x) * 1000)
  #define MUTEX_TYPE pthread_mutex_t
  #define MUTEX_SETUP(x) pthread_mutex_init(&(x), NULL)
  #define MUTEX_CLEANUP(x) pthread_mutex_destroy(&(x))
  #define MUTEX_LOCK(x) pthread_mutex_lock(&(x))
  #define MUTEX_UNLOCK(x) pthread_mutex_unlock(&(x))
#endif

#ifdef WIN32

	#define _WIN32_WINNT 0x0500
	#include <windows.h>
	#include <io.h>
	#include <direct.h>

	#define bool BOOL
	#define true TRUE
	#define false FALSE

	#define sleep_ms(x) Sleep(x)

	#define access _access
	#define R_OK 4
	#define W_OK 2
	#define X_OK 4
	#define F_OK 0

	#define mkdir(path,mode) (int)_mkdir(path)
	// these are dummy values - not used by mkdir
	#define S_IRUSR 3
	#define S_IWUSR 4
	#define S_IXUSR 5
	#define S_IRWXU 0
	#define S_IRWXG 1
	#define S_IRWXO 2
	#define S_ISDIR(mode) (((mode)&_S_IFDIR) == _S_IFDIR)
	#define S_ISREG(mode) (((mode)&_S_IFREG) == _S_IFREG)

	#define	SIGHUP		1	/* Hangup (POSIX).  */
	#define	SIGINT		2	/* Interrupt (ANSI).  */
	#define	SIGQUIT		3	/* Quit (POSIX).  */
	#define	SIGILL		4	/* Illegal instruction (ANSI).  */
	#define	SIGTRAP		5	/* Trace trap (POSIX).  */
	#define	SIGIOT		6	/* IOT trap (4.2 BSD).  */
	#define	SIGBUS		7	/* BUS error (4.2 BSD).  */
	#define	SIGFPE		8	/* Floating-point exception (ANSI).  */
	#define	SIGKILL		9	/* Kill, unblockable (POSIX).  */
	#define	SIGUSR1		10	/* User-defined signal 1 (POSIX).  */
	#define	SIGSEGV		11	/* Segmentation violation (ANSI).  */
	#define	SIGUSR2		12	/* User-defined signal 2 (POSIX).  */
	#define	SIGPIPE		13	/* Broken pipe (POSIX).  */
	#define	SIGALRM		14	/* Alarm clock (POSIX).  */
	#define	SIGTERM		15	/* Termination (ANSI).  */
	#define	SIGSTKFLT	16	/* Stack fault.  */
	#define	SIGCLD		SIGCHLD	/* Same as SIGCHLD (System V).  */
	#define	SIGCHLD		17	/* Child status has changed (POSIX).  */
	#define	SIGCONT		18	/* Continue (POSIX).  */
	#define	SIGSTOP		19	/* Stop, unblockable (POSIX).  */
	#define	SIGTSTP		20	/* Keyboard stop (POSIX).  */

	#define MUTEX_TYPE CRITICAL_SECTION
	#define MUTEX_SETUP(x) InitializeCriticalSection(&(x))
	#define MUTEX_CLEANUP(x) DeleteCriticalSection(&(x))
	#define MUTEX_LOCK(x) EnterCriticalSection(&(x))
	#define MUTEX_UNLOCK(x) LeaveCriticalSection(&(x))

#endif /* WIN32 */

#if defined(CONDOR_DRMAA_STANDALONE)

	/* We're compiling this outside of the rest of Condor */
	#include <stdio.h>
	#include <stdlib.h>
	#include <limits.h>
	#include <string.h>
	#include <sys/types.h>
	#include <sys/stat.h>
	#include <errno.h>
	#include <signal.h>
	#include <time.h>

	#ifndef WIN32
		#include <unistd.h>
		#include <sys/utsname.h>
	#endif
#else
	/* This is being built inside src/condor_drmaa */
	#include "condor_common.h"

	BEGIN_C_DECLS
#endif

#ifdef WIN32
  // use our own popen implementation on windows
  // (does not require a console to be attached)
  #define popen my_popen
  FILE *my_popen(const char *, const char *);
  #define pclose my_pclose
  int my_pclose(FILE *);

  // there is no fsync() in Windows, use native one
	#define fsync _commit

  // map pthread function to windows pendant
	#define pthread_self GetCurrentThreadId 
#endif

#include "drmaa.h"

// wrap snprintf to handle NULL arguments
#define snprintf condor_drmaa_snprintf

int condor_drmaa_snprintf(char *buf, size_t n, const char *fmt, ...);
#ifndef HAVE_STRLCPY
#  define strlcpy condor_drmaa_strlcpy
size_t condor_drmaa_strlcpy(char *dst, const char *src, size_t size);
#endif

#ifndef HAVE_STRLCAT
#  define strlcat condor_drmaa_strlcat
size_t condor_drmaa_strlcat(char *dst, const char *src, size_t size);
#endif

#define YES "Y"
#define NO "N"
#define SUCCESS 0
#define FAILURE 1
#define MIN_JOBID_LEN 10
#define SUBMIT_FILE_PREFIX "condor_drmaa_"
#define SUBMIT_FILE_EXTN ".sub"
#define LOG_FILE_PREFIX "condor_drmaa_"
#define LOG_FILE_EXTN ".log"
#define MAX_LOG_FILE_LINE_LEN 1000
#define MAX_FILE_NAME_LEN 1024
#define MAX_JOBID_LEN DRMAA_JOBNAME_BUFFER
#define SUBMIT_FILE_COL_SIZE 20	// size of column in submit file
#define SUBMIT_CMD "condor_submit"
#define SUBMIT_CMD_LEN 2000
#define HOLD_CMD "condor_hold -name"
#define HOLD_CMD_LEN 2000
#define QUEUE_CMD "condor_q -l -name"
#define QUEUE_CMD_LEN 2000
#define RELEASE_CMD "condor_release -name"
#define RELEASE_CMD_LEN 2000
#define TERMINATE_CMD "condor_rm -name"
#define TERMINATE_CMD_LEN 2000
#define MAX_READ_LEN 1024	// max # of bytes to read
#define JOBID_TOKENIZER "."
#define NUM_SUPP_SCALAR_ATTR 13	// # of supported scalar attributes
#define NUM_SUPP_VECTOR_ATTR 3
#define STAT_ABORTED -1
#define STAT_UNKNOWN 0		// 1 through 199 are signals
#define STAT_SIG_BASE 1
#define STAT_SIG_CORE_BASE 101
#define STAT_NOR_BASE 200
#define MIN_SIGNAL_NM_LEN 100
#define WAIT_SLP_TM 250	// # of miliseconds to wait if waited job active
#define DRMAA_CONFIG_FILE "/drmaa"
#define CATEGORY_SECTION_NAME "categories"

/* Session */
enum {
        ACTIVE,
        INACTIVE
};
int session_state;

/* Structures */
struct drmaa_attr_names_s {
	char **attrs;		// pointer to array of char*s
	int size;
	int index;		// holds which element of array we are currently on
};

struct drmaa_attr_values_s {
	char **values;		// pointer to array of char*s
	int size;		// number of values
	int index;		// current element
};

struct drmaa_job_ids_s {
	char **values;		// pointer to array of char*s
	int size;
	int index;
};

// used as a means of determining if job is finished
typedef enum {
	SUBMITTED,		// queued or running
	SUBMITTED_ASSUME_RUNNING, // after resuming, the job is internally queued,
			   	  // but assume it is already running
	HELD,			// _control() HOLD successful
	SUSPEND,		// DRMAA state SUSPEND is simulated
	FINISHED,		// successfully _synchronized() on and not disposed of
	DISPOSED
} job_state_t;

typedef struct condor_drmaa_job_info_s {
	job_state_t state;	// job's current state
	long lastmodtime;	// last recognized mtime of the according log file
	char id[MAX_JOBID_LEN];
	// <schedd name, job name on that schedd> (of fixed length) 
	struct condor_drmaa_job_info_s *next;	// next job_id
	int ref_count;
} condor_drmaa_job_info_t;

typedef struct job_attr_s {
	char name[DRMAA_ATTR_BUFFER];	// name of attribute
	union {
		char *value;	// if num_value = 1, attribute value held here
		char **values;	// if num_values > 1, attribute values held here
	} val;
	unsigned int num_values;	// the number of values pointed to by attr_value
	struct job_attr_s *next;	// next attribute in list
} job_attr_t;

struct drmaa_job_template_s {
	unsigned int num_attr;	// num attributes in this template
	job_attr_t *head;	// head of linked list of attributes
};

int standard_drmaa_error(int drmaa_errno, char *error_diagnosis, size_t error_diag_len);

/** Determines if a given string is a number.
    @param str the string to test
    @return true (upon success) or false
*/
int is_number(const char *str);

/** Allocates a new job_attr_t
    @return pointer to a new job template on the heap or NULL on failure.
*/
job_attr_t *create_job_attribute(void);

/** Deallocates a job_attr_t
    @param ja job attribute to deallocate
*/
void destroy_job_attribute(job_attr_t * ja);

/** Allocates a new condor_drmaa_job_info_t.  job_id must not be longer than MAX_JOBID_LEN.
    @return pointer to a new job info on the heap or NULL on failure
*/
condor_drmaa_job_info_t *create_job_info(const char *job_id);

/** Deallocates a condor_drmaa_job_info_t */
void destroy_job_info(condor_drmaa_job_info_t * job_info);

/** Determines if a given attribute name is valid.
    @param name attribute name
    @param drmaa_context_error_buf contains a context sensitive error upon
           fail returned
    @return true (upon success) or false
*/
int is_valid_attr_name(const char *name, char *error_diagnosis, size_t error_diag_len);

/** Determines if a given attribute value is 1) of the proper format and
    2) a valid value.  Assumes name is supported per is_supported_attr()
    @param err_cd set to DRMAA_ERRNO_INVALID_ATTRIBUTE_FORMAT, 
           DRMAA_ERRNO_INVALID_ATTRIBUTE_VALUE, or 
       DRMAA_ERRNO_CONFLICTING_ATTRIBUTE_VALUES in the appropriate case
    @param name attribute name
    @param value attribute value
    @param drmaa_context_error_buf contains a context sensitive error upon
           fail returned
    @return true (upon success) or false
*/
bool is_valid_attr_value(int *err_cd, const char *name, const char *value,
			 char *error_diagnosis, size_t error_diag_len);

/** Determines if a given attribute name represents a scalar attribute.
    Assumes that name is valid per is_valid_attr_name()
    @param name name of attribute
    @param error_diagnosis contains a context sensitive error upon failure
    @param error_diag_len length of error_diagnosis buffer
    @return true (upon succcess) or false
*/
int is_scalar_attr(const char *name, char *error_diagnosis, size_t error_diag_len);

/** Determines if a given attribute name represents a vectorr attribute.
    Assumes that an attribute name is valid per is_valid_attr_name().
    @param name name of attribute
    @param error_diagnosis contains a context sensitive error upon failure
    @param error_diag_len length of error_diagnosis buffer
    @return true or false
*/
int is_vector_attr(const char *name, char *error_diagnosis, size_t error_diag_len);

/** Determines if a given attribute name is supported by this DRMAA library.
    Assumes that name is valid per is_valid_attr_name()
    @param name name of attribute
    @param error_diagnosis contains a context sensitive error upon failure
    @param error_diag_len length of error_diagnosis buffer
    @return true (upon success) or false
*/
int is_supported_attr(const char *name, char *error_diagnosis, size_t error_diag_len);

/** Prints the given job attributes.
    Used in debugging.
*/
/*void print_ja(const job_attr_t* ja); */

/** Allocates a new drmaa_job_template_t
    @return the job template or NULL upon failure
*/
drmaa_job_template_t *create_job_template(void);

void destroy_job_template(drmaa_job_template_t *jt);

/** Determines if a given job template is valid.
    @param jt job template
    @param drmaa_context_error_buf contains a context sensitive error upon
           fail returned
    @return true (upon success) or false
*/
int is_valid_job_template(const drmaa_job_template_t * jt, char *error_diagnosis, size_t error_diag_len);

/** Searches a given job template for the job attribute corresponding to name. 
    The first one found is returned.  If none is found, NULL is returned.
    jt is assumed to be valid per is_valid_job_template() and name is 
    assumed to be valid per is_supported_attr()
    @param jt job template
    @param name name of job attribute
    @param drmaa_context_error_buf contains a context sensitive error upon
           fail returned
    @return a pointer to the job attribute or NULL
*/
job_attr_t *find_attr(const drmaa_job_template_t * jt, const char *name, char *error_diagnosis, size_t error_diag_len);

/** Determines if the change of the given attribute leads to a conflict
    with already specified values.
    Assumes that jt is valid per is_valid_job_template() and that name is 
    supported per is_supported_attr()
    @param jt job template
    @param name attribute name
    @param error_diagnosis contains a context sensitive error upon failure
    @param error_diag_len length of error buffer
    @return true (upon success) or false
*/
bool attr_conflict(const drmaa_job_template_t * jt, const char *name, char *error_diagnosis, size_t error_diag_len);

/** Removes an attribute with a given name from the given job template.
    Assumes that jt is valid per is_valid_job_template() and that name is 
    supported per is_supported_attr()
    @param jt job template
    @param name attribute name
*/
void rm_jt_attribute(drmaa_job_template_t * jt, const char *name);

/** Determines if a given attribute is already set in a given job template.
    Assumes that jt is valid per is_valid_job_template() and that name is 
    supported per is_supported_attr()
    @param jt job template
    @param name attribute name
    @param error_diagnosis contains a context sensitive error upon failure
    @param error_diag_len length of error buffer
    @return true (upon success) or false
*/
bool contains_attr(const drmaa_job_template_t * jt, const char *name, char *error_diagnosis, size_t error_diag_len);

/** Prints a given job template.  Useful in debugging. */
/*void print_jt(const drmaa_job_template_t* jt); */

/** Creates a Condor submit file for the given job template
    @param submit_fn submit file name allocated and returned upon SUCCESS
    @param jt job template Must be valid per is_valid_job_template()
    @param error_diagnosis contains a context sensitive error upon
           fail returned
    @param error_diag_len length of the error buffer
    @return one of the following error codes:
            DRMAA_ERRNO_SUCCESS
        DRMAA_ERRNO_TRY_LATER
        DRMAA_ERRNO_NO_MEMORY
*/
int create_submit_file(char **submit_fn, const drmaa_job_template_t * jt,
		       bool * isHoldJob, char *error_diagnosis, size_t error_diag_len, int start, int end, int incr, char** username);

/** Generates a unique file name.
    @param fname allocated and filled with the unique file name on success
    @return SUCCESS or FAILURE
*/
int generate_unique_file_name(char **fname);

/** Write a given job attribute to the opened submit file file stream.
    Assumes that ja is valid.
    @return SUCCESS or FAILURE
*/
int write_job_attr(FILE *fs, const job_attr_t * ja, bool joinFiles, bool gotStartTime, bool *isHoldJob, const char *transfer_files, int index, char** username);

/** Handles the DRMAA placeholders:
      $drmaa_incr_ph$
      $drmaa_hd_ph$
      $drmaa_wd_ph$
    @return newly allocated string with substituted placeholders
 */
char *substitute_placeholders(const char *orig, int index);

/** Writes a given vector job attribute to the opened submit file file stream.
    Assumes that ja is valid.
    @return number of characters written or negative if an error occurred
*/
int write_v_job_attr(FILE *fs, const job_attr_t * ja);

/** Submits a job to condor using the given submit file.
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
int submit_job(char *job_id, size_t job_id_len, const char *submit_file_name,
	       char *error_diagnosis, size_t error_diag_len, char* username);

/** Determines if stat represents a valid stat code
    @return true or false
*/
int is_valid_stat(const int stat);

/** Determines if a given job id is valid
    @return true or false
*/
int is_valid_job_id(const char *job_id);

/** Given a valid job_id, open's its log file for reading only.
    @return pointer to file stream or NULL
*/
FILE *open_log_file(const char *job_id);

/** Removes the log file of the given job id
    @return true upon success, false on failure
*/
int rm_log_file(const char *job_id);

/** Waits for a given job_id to complete by monitoring the log file
    @param dispose If true, deletes log file
    @return DRMAA_ERRNO_s very similar to drmaa_wait()
 */
int wait_job(const char *job_id, char *job_id_out,
	     size_t job_id_out_len, const int dispose,
	     const int get_stat_rusage, int *stat, signed long timeout,
	     const time_t start, drmaa_attr_values_t **rusage, char *error_diagnosis, size_t error_diag_len);

/** Creates a drmaa_attr_values_t
    @return the drmaa_attr_values_t or NULL (upon failure)
*/
drmaa_attr_values_t *create_dav();

int add_dav(drmaa_attr_values_t *dav, const char *val);

void destroy_dav(drmaa_attr_values_t *dav);

/** Removes a given job id from the job_info_list.  Method acquires
    and releases job_info_list_lock.
    @return true (upon success) or false 
*/
int rm_job(const char *job_id);

/** Change the status of a given job on the info list.  This
    method acquires and releases the info_job_list lock itself.  If the 
    jobid is not found in the info_jobs_list, the function returns false.
    @return true (upon success) or false
*/
int mark_job(const char *job_id, int state);

/** Determines the library's base directory, allocates the required memory
    for buf, and copies the full path name there.  A successful result contains
    a trailing forward slash or backslash, depanding upon the system.
    @return true (on success) or false otherwise
*/
int get_base_dir(void);

/** Places the given jobid on hold.  Assumes job is in proper state already.
    @return drmaa error code appropriate for drmaa_control()
*/
int hold_job(const char *jobid, char *error_diagnosis, size_t error_diag_len, char* username);

/** Releases the given jobid, which is assumed to be already on hold.
    @return drmaa error code appropriate for drmaa_control()
*/
int release_job(const char *jobid, char *error_diagnosis, size_t error_diag_len, char* username);

/** Terminates the given valid jobid by calling condor_rm.  Does not 
    remove the jobid from the library's internal data structures.
    @return drmaa error code appropriate for drmaa_control()
*/
int terminate_job(const char *jobid, char *error_diagnosis, size_t error_diag_len, char* username);

/** Obtains the name of the local schedd.  Sets the "schedd_name" global
    variable upon success.  
    @return 0 (upon success) or -1
*/
int get_schedd_name(void);

/** Parses a DRMMA-compliant partial timestamp and returns a string with epoch value
*/
char *parse_ts(const char *partialTs);

/** Returns a DRMAA-compliant job status code for the given job. Assumes that
    the job ID is valid
*/
int get_job_status_condorq(const char *jobid, int *remote_ps, char *error_diagnosis, size_t error_diag_len);

int get_job_status_logfile(const char *job_id, int *remote_ps, char *error_diagnosis, size_t error_diag_len);

/** Returns current internal status of the given job.
*/
int get_job_status(const char *jobid);

condor_drmaa_job_info_t *get_job_info(const char *jobid);
condor_drmaa_job_info_t *copy_job(condor_drmaa_job_info_t *src);
condor_drmaa_job_info_t *copy_job_list(condor_drmaa_job_info_t *src);
int free_job_list(void);
int free_list(condor_drmaa_job_info_t **list);

/** Converts a Condor log file signal number to this DRMAA
    implementation's number.
    @return signal number or 0 if no matching signal found
*/
int condor_sig_to_drmaa(const int condor_sig);

char *get_category_options(const char *categoryName);

#if !defined(CONDOR_DRMAA_STANDALONE)
	END_C_DECLS
#endif

#endif /* CONDOR_AUX_DRMAA_H */
