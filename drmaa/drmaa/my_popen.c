/***************************Copyright-DO-NOT-REMOVE-THIS-LINE**
  *
  * Condor Software Copyright Notice
  * Copyright (C) 1990-2004, Condor Team, Computer Sciences Department,
  * University of Wisconsin-Madison, WI.
  *
  * This source code is covered by the Condor Public License, which can
  * be found in the accompanying LICENSE.TXT file, or online at
  * www.condorproject.org.
  *
  * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
  * AND THE UNIVERSITY OF WISCONSIN-MADISON "AS IS" AND ANY EXPRESS OR
  * IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
  * WARRANTIES OF MERCHANTABILITY, OF SATISFACTORY QUALITY, AND FITNESS
  * FOR A PARTICULAR PURPOSE OR USE ARE DISCLAIMED. THE COPYRIGHT
  * HOLDERS AND CONTRIBUTORS AND THE UNIVERSITY OF WISCONSIN-MADISON
  * MAKE NO MAKE NO REPRESENTATION THAT THE SOFTWARE, MODIFICATIONS,
  * ENHANCEMENTS OR DERIVATIVE WORKS THEREOF, WILL NOT INFRINGE ANY
  * PATENT, COPYRIGHT, TRADEMARK, TRADE SECRET OR OTHER PROPRIETARY
  * RIGHT.
  *
  ****************************Copyright-DO-NOT-REMOVE-THIS-LINE**/

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef WIN32
#pragma warning (disable: 4996)
#define _CRT_SECURE_NO_DEPRECATE  // for latest SDK compilers

#include <windows.h>
#include <io.h>
typedef HANDLE child_handle_t;
#define INVALID_CHILD_HANDLE INVALID_HANDLE_VALUE;
#else
typedef pid_t child_handle_t;
#define INVALID_CHILD_HANDLE ((pid_t)-1)
#endif

/* We manage outstanding children with a simple linked list. */
struct popen_entry {
	FILE* fp;
	child_handle_t ch;
	struct popen_entry *next;
};
struct popen_entry *popen_entry_head = NULL;

static void add_child(FILE* fp, child_handle_t ch)
{
	struct popen_entry *pe = malloc(sizeof(struct popen_entry));
	pe->fp = fp;
	pe->ch = ch;
	pe->next = popen_entry_head;
	popen_entry_head = pe;
}

static child_handle_t remove_child(FILE* fp)
{
	struct popen_entry *pe = popen_entry_head;
	struct popen_entry **last_ptr = &popen_entry_head;
	while (pe != NULL) {
		if (pe->fp == fp) {
			child_handle_t ch = pe->ch;
			*last_ptr = pe->next;
			free(pe);
			return ch;
		}
		last_ptr = &(pe->next);
		pe = pe->next;
	}
	return INVALID_CHILD_HANDLE;
}

/*

  FILE *my_popenv(char *const args[]);

  This is a popen(3)-like function that intentionally avoids
  calling out to the shell in order to limit what can be done for
  security reasons. Please note that this does not intend to behave
  in the same way as a normal popen, it exists as a convenience. 
  
  This function is careful in how it waits for its children's
  status so that it doesn't reap status information for other
  processes which the calling code may want to reap.

  FIXME: The windows version of my_popenv() does not support
  arguments that contain double quotes or end in a backslash.
  This can be fixed by using the ArgList class to generate the
  command line.

  However, we do *NOT* "eat" SIGCHLD, since a) SIGCHLD is
  probably blocked when this method is invoked, b) there are cases
  where our attempt to eat SIGCHLD might result in eating too many of
  them, and that's really bad, c) to try to do this right would be
  very complicated code in here and, d) the worst thing that happens
  is our caller gets and extra SIGCHLD, which, in the case of
  DaemonCore, just results in a D_FULLDEBUG and nothing more.  the
  potential harm of doing this wrong far outweighs the harm of this
  extra dprintf()... Derek Wright <wright@cs.wisc.edu> 2004-05-27

*/

#ifdef WIN32

/* Windows versions of my_popen / my_pclose */

/*
  Utility function to build a command line suitable for Create_Process.
  We quote each argument in order to handle spaces in args. The pointer
  returned from this function should be free()d when no longer needed.
  This function fails (returns NULL) if any argument contains double
  quotes or ends in a backslash.
*/
static char*
build_cmdline(char *const args[])
{
	const char *arg;
	int i, arg_count;
	char *cmdline;
	int cmdline_size;
	const char *srcp;
	char *dstp;
	int illegal = 0;

	if (args == NULL)
		return NULL;

	/* first pass: determine size */
	arg_count = 0;
	cmdline_size = 0;
	for (i = 0; (arg = args[i]) != NULL; i++) {
		/* update size (add 3 for quotes and space/null) */
		cmdline_size += 3 + strlen(args[i]);
		arg_count++;
	}
	if (arg_count == 0)
		return NULL;

	/* second pass: build the string */
	cmdline = (char *)malloc(cmdline_size);
	dstp = cmdline;
	for (i = 0; i < arg_count; i++) {
		*(dstp++) = '\"';
		srcp = args[i];
		while (*srcp != '\0') {
			if (*(srcp) == '\"') {
				illegal = 1;
			}
			*(dstp++) = *(srcp++);
		}
		if (*(dstp - 1) == '\\') {
			illegal = 1;
		}
		*(dstp++) = '\"';
		*(dstp++) = ' ';
	}
	*(dstp - 1) = '\0';

	if (illegal) {
		/*
		  bail out it any arg had a double quote or backslash as the last character
		  this should be moved over to using the ArgList class in V6.7
		*/
		free(cmdline);
		return NULL;
	}

	return cmdline;
}

FILE *
my_popen(const char *const_cmd, const char *mode)
{
	BOOL read_mode;
	SECURITY_ATTRIBUTES saPipe;
	HANDLE hReadPipe, hWritePipe;
	HANDLE hParentPipe, hChildPipe;
	STARTUPINFO si;
	PROCESS_INFORMATION pi;
	char *cmd;
	BOOL result;
	int fd;
	FILE *retval;

	if (!mode)
		return NULL;
	read_mode = mode[0] == 'r';

	// use SECURITY_ATTRIBUTES to mark pipe handles as inheritable
	saPipe.nLength = sizeof(SECURITY_ATTRIBUTES);
	saPipe.lpSecurityDescriptor = NULL;
	saPipe.bInheritHandle = TRUE;

	// create the pipe (and mark the parent's end as uninheritable)
	if (CreatePipe(&hReadPipe, &hWritePipe, &saPipe, 0) == 0) {
		//dprintf(D_ALWAYS, "my_popen: CreatePipe failed\n");
		return NULL;
	}
	if (read_mode) {
		hParentPipe = hReadPipe;
		hChildPipe = hWritePipe;
	}
	else {
		hParentPipe = hWritePipe;
		hChildPipe = hReadPipe;
	}
	SetHandleInformation(hParentPipe, HANDLE_FLAG_INHERIT, 0);

	// initialize PROCESS_INFORMATION
	memset(&pi, 0, sizeof(PROCESS_INFORMATION));

	// initialize STARTUPINFO to set standard handles
	memset(&si, 0, sizeof(STARTUPINFO));
	si.cb = sizeof(STARTUPINFO);
	if (read_mode) {
		si.hStdOutput = hChildPipe;
		si.hStdError = hChildPipe;
		si.hStdInput = GetStdHandle(STD_INPUT_HANDLE);
	}
	else {
		si.hStdInput = hChildPipe;
		si.hStdOutput = GetStdHandle(STD_OUTPUT_HANDLE);
		si.hStdError = GetStdHandle(STD_ERROR_HANDLE);
	}
	si.dwFlags = STARTF_USESTDHANDLES;

	// make call to CreateProcess
	cmd = strdup(const_cmd);
	result = CreateProcess(NULL,
		cmd,	// command line
		NULL,	// process SA
		NULL,	// primary thread SA
		TRUE,	// inherit handles 
		0,		// creation flags
		NULL,	// use our environment
		NULL,	// use our CWD
		&si,	// STARTUPINFO
		&pi);	// receive PROCESS_INFORMATION
	free(cmd);
	if (result == 0) {
		CloseHandle(hParentPipe);
		CloseHandle(hChildPipe);
		//dprintf(D_ALWAYS, "my_popen: CreateProcess failed\n");
		return NULL;
	}

	// don't care about child's primary thread handle
	// or child's ends of the pipes
	CloseHandle(pi.hThread);
	CloseHandle(hChildPipe);

	// convert pipe handle specified in mode into a FILE pointer
	fd = _open_osfhandle((long)hParentPipe, 0);
	if (fd == -1) {
		CloseHandle(hParentPipe);
		CloseHandle(pi.hProcess);
		//dprintf(D_ALWAYS, "my_popen: _open_osfhandle failed\n");
		return NULL;
	}
	retval = _fdopen(fd, mode);
	if (retval == NULL) {
		CloseHandle(hParentPipe);
		CloseHandle(pi.hProcess);
		//dprintf(D_ALWAYS, "my_popen: _fdopen failed\n");
		return NULL;
	}

	// save child's process handle (for pclose)
	add_child(retval, pi.hProcess);

	return retval;
}

FILE *my_popenv(char *const args[], const char *mode)
{
	char *cmdline;
	FILE *fp;

	cmdline = build_cmdline(args);
	if (cmdline == NULL) {
		//dprintf(D_ALWAYS, "mypopenv: invalid args\n");
		return NULL;
	}
	fp = my_popen(cmdline, mode);
	free(cmdline);

	return fp;
}

int
my_pclose(FILE *fp)
{
	HANDLE hChildProcess;
	DWORD result;

	hChildProcess = remove_child(fp);

	fclose(fp);

	result = WaitForSingleObject(hChildProcess, INFINITE);
	if (result != WAIT_OBJECT_0) {
		//dprintf(D_FULLDEBUG, "my_pclose: WaitForSingleObject failed\n");
		return -1;
	}
	if (!GetExitCodeProcess(hChildProcess, &result)) {
		//dprintf(D_FULLDEBUG, "my_pclose: GetExitCodeProcess failed\n");
		return -1;
	}
	CloseHandle(hChildProcess);

	return result;
}


#else

/* UNIX versions of my_popen(v) / my_pclose */

static int	READ_END = 0;
static int	WRITE_END = 1;

FILE *
my_popenv( char *const args[], const char * mode )
{
	int	pipe_d[2];
	int	parent_reads;
	uid_t	euid;
	gid_t	egid;
	pid_t	pid;
	FILE*	retp;

		/* Figure out who reads and who writes on the pipe */
	parent_reads = mode[0] == 'r';

		/* Create the pipe */
	if( pipe(pipe_d) < 0 ) {
		return NULL;
	}

		/* Create a new process */
	if( (pid=fork()) < 0 ) {
			/* Clean up file descriptors */
		close( pipe_d[0] );
		close( pipe_d[1] );
		return NULL;
	}

		/* The child */
	if( pid == 0 ) {

		if( parent_reads ) {
				/* Close stdin, dup pipe to stdout */
			close( pipe_d[READ_END] );
			if( pipe_d[WRITE_END] != 1 ) {
				dup2( pipe_d[WRITE_END], 1 );
				close( pipe_d[WRITE_END] );
			}
		} else {
				/* Close stdout, dup pipe to stdin */
			close( pipe_d[WRITE_END] );
			if( pipe_d[READ_END] != 0 ) {
				dup2( pipe_d[READ_END], 0 );
				close( pipe_d[READ_END] );
			}
		}
			/* to be safe, we want to switch our real uid/gid to our
			   effective uid/gid (shedding any privledges we've got).
			   we also want to drop any supplimental groups we're in.
			   we want to run this popen()'ed thing as our effective
			   uid/gid, dropping the real uid/gid.  all of these calls
			   will fail if we don't have a ruid of 0 (root), but
			   that's harmless.  also, note that we have to stash our
			   effective uid, then switch our euid to 0 to be able to
			   set our real uid/gid
			*/
		euid = geteuid();
		egid = getegid();
		seteuid( 0 );
		setgroups( 1, &egid );
		setgid( egid );
		setuid( euid );

		execvp(args[0], args);
		_exit( ENOEXEC );		/* This isn't safe ... */
	}

		/* The parent */
	if( parent_reads ) {
		close( pipe_d[WRITE_END] );
		retp = fdopen(pipe_d[READ_END],mode);
	} else {
		close( pipe_d[READ_END] );
		retp = fdopen(pipe_d[WRITE_END],mode);
	}
	add_child(retp, pid);
	return retp;
}

int
my_pclose(FILE *fp)
{
	int			status;
	pid_t			pid;

		/* Pop the child off our list */
	pid = remove_child(fp);

		/* Close the pipe */
	(void)fclose( fp );

		/* Wait for child process to exit and get its status */
	while( waitpid(pid,&status,0) < 0 ) {
		if( errno != EINTR ) {
			status = -1;
			break;
		}
	}

		/* Now return status from child process */
	return status;
}

pid_t ChildPid = 0;

/*
  This is similar to the UNIX system(3) call, except it doesn't invoke
  a shell.  This is much more of a fork/exec/wait call.  Perhaps you
  should think of it as the "spawn" call on old MS-DOG systems.

  It shares the child handling with my_popen(), which is why it's in
  the same source file.  See the comments for it for more details.

  Returns:
    -1: failure
    >0: Pid of child (wait == false)
    0: Success (wait == true)
*/
#define MAXARGS	32
int
my_spawnl( const char* cmd, ... )
{
	int		rval;
	int		argno = 0;

    va_list va;
	const char * argv[MAXARGS + 1];

	/* Convert the args list into an argv array */
    va_start( va, cmd );
	for( argno = 0;  argno < MAXARGS;  argno++ ) {
		const char	*p;
		p = va_arg( va, const char * );
		argv[argno] = p;
		if ( ! p ) {
			break;
		}
	}
	argv[MAXARGS] = NULL;
    va_end( va );

	/* Invoke the real spawnl to do the work */
    rval = my_spawnv( cmd, (char *const*) argv );

	/* Done */
	return rval;
}

/*
  This is similar to the UNIX system(3) call, except it doesn't invoke
  a shell.  This is much more of a fork/exec/wait call.  Perhaps you
  should think of it as the "spawn" call on old MS-DOG systems.

  It shares the child handling with my_popen(), which is why it's in
  the same source file.  See the comments for it for more details.

  Returns:
    -1: failure
    >0 == Return status of child
*/
int
my_spawnv( const char* cmd, char *const argv[] )
{
	int					status;
	uid_t euid;
	gid_t egid;

		/* Use ChildPid as a simple semaphore-like lock */
	if ( ChildPid ) {
		return -1;
	}

		/* Create a new process */
	ChildPid = fork();
	if( ChildPid < 0 ) {
		ChildPid = 0;
		return -1;
	}

		/* Child: create an ARGV array, exec the binary */
	if( ChildPid == 0 ) {
			/* to be safe, we want to switch our real uid/gid to our
			   effective uid/gid (shedding any privledges we've got).
			   we also want to drop any supplimental groups we're in.
			   the whole point of my_spawn*() is that we want to run
			   something as our effective uid/gid, and we want to do
			   it safely.  all of these calls will fail if we don't
			   have a ruid of 0 (root), but that's harmless.  also,
			   note that we have to stash our effective uid, then
			   switch our euid to 0 to be able to set our real uid/gid 
			*/
		euid = geteuid();
		egid = getegid();
		seteuid( 0 );
		setgroups( 1, &egid );
		setgid( egid );
		setuid( euid );

			/* Now it's safe to exec whatever we were given */
		execv( cmd, argv );
		_exit( ENOEXEC );		/* This isn't safe ... */
	}

		/* Wait for child process to exit and get its status */
	while( waitpid(ChildPid,&status,0) < 0 ) {
		if( errno != EINTR ) {
			status = -1;
			break;
		}
	}

		/* Now return status from child process */
	ChildPid = 0;
	return status;
}

#endif // ndef WIN32

/*
  This is a system(3)-like function that does not call out to
  the shell. It is implemented on top of my_popenv().

  FIXME: The windows version of my_systemv() does not support
  arguments that contain double quotes or end in a backslash.
  This can be fixed by using the ArgList class to generate the
  command line.
*/

int
my_systemv(char *const args[])
{
	FILE *fp;

	fp = my_popenv(args, "w");
	if (fp == NULL)
		return -1;

	return my_pclose(fp);
}
