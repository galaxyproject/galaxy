#!/usr/bin/python
#
# Copyright (c) 2011, Pacific Biosciences of California, Inc.
#
# All rights reserved.
#
#Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:
#    * Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
#    * Neither the name of Pacific Biosciences nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.
#
#THIS SOFTWARE IS PROVIDED BY PACIFIC BIOSCIENCES AND ITS CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
#WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL PACIFIC BIOSCIENCES OR ITS CONTRIBUTORS BE LIABLE FOR ANY
#DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
#LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
import sys
import os
import subprocess

QUAKE_EXE = os.path.join( os.path.dirname(os.path.abspath(sys.argv[0])), 'quake.py' )
cmdLine = sys.argv
cmdLine.pop(0)

#
# horribly not robust, but it was a pain to rewrite everything with
# optparse
#
j = -1
cut = 0
for i,arg in enumerate(cmdLine):
    if '--default_cutoff' in arg:
        j = i
        cut = int(arg.split('=')[1])
if j>=0:
    cmdLine = cmdLine[:j] + cmdLine[j+1:]

j = -1
output=''
for i,arg in enumerate(cmdLine):
    if '--output' in arg:
        j = i
        output = arg.split('=')[1]
if j>=0:
    cmdLine = cmdLine[:j] + cmdLine[j+1:]

def backticks( cmd, merge_stderr=True ):
    """
    Simulates the perl backticks (``) command with error-handling support
    Returns ( command output as sequence of strings, error code, error message )
    """
    if merge_stderr:
        _stderr = subprocess.STDOUT
    else:
        _stderr = subprocess.PIPE

    p = subprocess.Popen( cmd, shell=True, stdin=subprocess.PIPE,
                          stdout=subprocess.PIPE, stderr=_stderr,
                          close_fds=True )

    out = [ l[:-1] for l in p.stdout.readlines() ]

    p.stdout.close()
    if not merge_stderr:
        p.stderr.close()

    # need to allow process to terminate
    p.wait()

    errCode = p.returncode and p.returncode or 0
    if p.returncode>0:
        errorMessage = os.linesep.join(out)
        output = []
    else:
        errorMessage = ''
        output = out

    return output, errCode, errorMessage

def to_stdout():
    def toCorFastq(f):
        stem, ext = os.path.splitext( os.path.basename(f) )
        dir = os.path.dirname(f)
        corFastq = os.path.join(dir,'%s.cor%s' % (stem,ext) )
        if not os.path.exists(corFastq):
            print >>sys.stderr, "Can't find path %s" % corFastq
            sys.exit(1)
        return corFastq
    if '-r' in cmdLine:
        fastqFile = cmdLine[ cmdLine.index('-r')+1 ]
        corFastq = toCorFastq(fastqFile)
        infile = open( corFastq, 'r' )
        for line in infile:
            sys.stdout.write( line )
        infile.close()
    else:
        fofnFile = cmdLine[ cmdLine.index('-f')+1 ]
        infile = open(fofnFile,'r')
        for line in infile:
            line = line.strip()
            if len(line)>0:
                fastqFiles = line.split()
                break
        infile.close()
        outs = output.split(',')
        for o,f in zip(outs,fastqFiles):
            cf = toCorFastq(f)
            os.system( 'cp %s %s' % ( cf, o ) )

def run():
    cmd = '%s %s' % ( QUAKE_EXE, " ".join(cmdLine) )
    output, errCode, errMsg = backticks( cmd )

    if errCode==0:
        to_stdout()
    else:
        # if Quake exits with an error in cutoff determination we  
        # can force correction if requested
        if 'cutoff.txt' in errMsg and cut>0:
            outfile = open( 'cutoff.txt', 'w' )
            print >>outfile, str(cut)
            outfile.close()
            cmd = '%s --no_count --no_cut %s' % ( QUAKE_EXE, " ".join(cmdLine) )
            output, errCode, errMsg = backticks( cmd )
        if errCode==0:
            to_stdout()
        else:
            print >>sys.stderr, errMsg
            sys.exit(1)

if __name__=='__main__': run()
