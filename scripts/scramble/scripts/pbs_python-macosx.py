import os, sys, subprocess, tarfile, shutil

def unpack_prebuilt_torque():
    if not os.access( TORQUE_BINARY_ARCHIVE, os.F_OK ):
        print "unpack_prebuilt_torque(): No binary archive of Torque available for this platform - will build it now"
        build_torque()
    else:
        print "unpack_prebuilt_torque(): Found a previously built Torque binary archive for this platform."
        print "unpack_prebuilt_torque(): To force Torque to be rebuilt, remove the archive:"
        print " ", TORQUE_BINARY_ARCHIVE
        t = tarfile.open( TORQUE_BINARY_ARCHIVE, "r" )
        for fn in t.getnames():
            t.extract( fn )
        t.close()

def build_torque():
    # untar
    print "build_torque(): Unpacking Torque source archive from:"
    print " ", TORQUE_ARCHIVE
    t = tarfile.open( TORQUE_ARCHIVE, "r" )
    for fn in t.getnames():
        t.extract( fn )
    t.close()
    # patch
    file = os.path.join( "torque-%s" %TORQUE_VERSION, "src", "include", "libpbs.h" )
    print "build_torque(): Patching", file
    if not os.access( "%s.orig" %file, os.F_OK ):
        shutil.copyfile( file, "%s.orig" %file )
    i = open( "%s.orig" %file, "r" )
    o = open( file, "w" )
    for line in i.readlines():
        if line == "#define NCONNECTS 5\n":
            line = "#define NCONNECTS 50\n"
        print >>o, line,
    i.close()
    o.close()
    # configure
    print "build_torque(): Running Torque configure script"
    p = subprocess.Popen( args = CONFIGURE, shell = True, cwd = os.path.join( os.getcwd(), "torque-%s" %TORQUE_VERSION) )
    r = p.wait()
    if r != 0:
        print "build_torque(): Torque configure script failed"
        sys.exit( 1 )
    # compile
    print "build_torque(): Building Torque (make)"
    p = subprocess.Popen( args = "make", shell = True, cwd = os.path.join( os.getcwd(), "torque-%s" %TORQUE_VERSION) )
    r = p.wait()
    # libtool won't pass -arch to the linker, maybe it's an old libtool?  whatever, this works
    p = subprocess.Popen( args = "gcc -dynamiclib -undefined dynamic_lookup -o .libs/libtorque.0.0.0.dylib  .libs/dis.o .libs/discui_.o .libs/discul_.o .libs/disi10d_.o .libs/disi10l_.o .libs/disiui_.o .libs/disp10d_.o .libs/disp10l_.o .libs/disrcs.o .libs/disrd.o .libs/disrf.o .libs/disrfcs.o .libs/disrfst.o .libs/disrl_.o .libs/disrl.o .libs/disrsc.o .libs/disrsi_.o .libs/disrsi.o .libs/disrsl_.o .libs/disrsl.o .libs/disrss.o .libs/disrst.o .libs/disruc.o .libs/disrui.o .libs/disrul.o .libs/disrus.o .libs/diswcs.o .libs/diswf.o .libs/diswl_.o .libs/diswsi.o .libs/diswsl.o .libs/diswui_.o .libs/diswui.o .libs/diswul.o .libs/advise.o .libs/dec_attrl.o .libs/dec_attropl.o .libs/dec_Authen.o .libs/dec_CpyFil.o .libs/dec_JobCred.o .libs/dec_JobFile.o .libs/dec_JobId.o .libs/dec_JobObit.o .libs/dec_Manage.o .libs/dec_MoveJob.o .libs/dec_MsgJob.o .libs/dec_QueueJob.o .libs/dec_Reg.o .libs/dec_ReqExt.o .libs/dec_ReqHdr.o .libs/dec_Resc.o .libs/dec_rpyc.o .libs/dec_rpys.o .libs/dec_RunJob.o .libs/dec_Shut.o .libs/dec_Sig.o .libs/dec_Status.o .libs/dec_svrattrl.o .libs/dec_Track.o .libs/enc_attrl.o .libs/enc_attropl.o .libs/enc_CpyFil.o .libs/enc_JobCred.o .libs/enc_JobFile.o .libs/enc_JobId.o .libs/enc_JobObit.o .libs/enc_Manage.o .libs/enc_MoveJob.o .libs/enc_MsgJob.o .libs/enc_QueueJob.o .libs/enc_Reg.o .libs/enc_reply.o .libs/enc_ReqExt.o .libs/enc_ReqHdr.o .libs/enc_RunJob.o .libs/enc_Shut.o .libs/enc_Sig.o .libs/enc_Status.o .libs/enc_svrattrl.o .libs/enc_Track.o .libs/get_svrport.o .libs/nonblock.o .libs/PBS_attr.o .libs/pbsD_alterjo.o .libs/pbsD_asyrun.o .libs/PBS_data.o .libs/pbsD_connect.o .libs/pbsD_deljob.o .libs/pbsD_holdjob.o .libs/pbsD_locjob.o .libs/PBSD_manage2.o .libs/pbsD_manager.o .libs/pbsD_movejob.o .libs/PBSD_manager_caps.o .libs/PBSD_msg2.o .libs/pbsD_msgjob.o .libs/pbsD_orderjo.o .libs/PBSD_rdrpy.o .libs/pbsD_rerunjo.o .libs/pbsD_resc.o .libs/pbsD_rlsjob.o .libs/pbsD_runjob.o .libs/pbsD_selectj.o .libs/PBSD_sig2.o .libs/pbsD_sigjob.o .libs/pbsD_stagein.o .libs/pbsD_statjob.o .libs/pbsD_statnode.o .libs/pbsD_statque.o .libs/pbsD_statsrv.o .libs/PBSD_status2.o .libs/PBSD_status.o .libs/pbsD_submit.o .libs/PBSD_submit_caps.o .libs/pbsD_termin.o .libs/pbs_geterrmg.o .libs/pbs_statfree.o .libs/rpp.o .libs/tcp_dis.o .libs/tm.o .libs/list_link.o .libs/ck_job_name.o .libs/cnt2server.o .libs/cvtdate.o .libs/get_server.o .libs/locate_job.o .libs/parse_at.o .libs/parse_depend.o .libs/parse_destid.o .libs/parse_equal.o .libs/parse_jobid.o .libs/parse_stage.o .libs/prepare_path.o .libs/prt_job_err.o .libs/set_attr.o .libs/set_resource.o .libs/chk_file_sec.o .libs/log_event.o .libs/pbs_log.o .libs/pbs_messages.o .libs/setup_env.o .libs/get_hostaddr.o .libs/get_hostname.o .libs/md5.o .libs/net_client.o .libs/net_server.o .libs/net_set_clse.o .libs/rm.o .libs/port_forwarding.o  -lkvm -Wl,-syslibroot -Wl,/Developer/SDKs/MacOSX10.4u.sdk -install_name  /usr/local/lib/libtorque.0.dylib -compatibility_version 1 -current_version 1.0 -arch i386 -arch ppc", shell = True, cwd = os.getcwd()+"/torque-%s/src/lib/Libpbs" %TORQUE_VERSION )
    r = p.wait()
    p = subprocess.Popen( args = "make", shell = True, cwd = os.path.join( os.getcwd(), "torque-%s" %TORQUE_VERSION) )
    r = p.wait()
    if r != 0:
        print "build_torque(): Building Torque (make) failed"
        sys.exit( 1 )
    # install
    print "build_torque(): Installing Torque (make install_lib)"
    p = subprocess.Popen( args = "make DESTDIR=%s/torque install_lib" %os.getcwd(), shell = True, cwd = os.path.join( os.getcwd(), "torque-%s" %TORQUE_VERSION) )
    r = p.wait()
    if r != 0:
        print "build_torque(): Installing Torque (make install_lib) failed"
        sys.exit( 1 )
    # pack
    print "build_torque(): Creating binary Torque archive for future builds of pbs_python"
    t = tarfile.open( TORQUE_BINARY_ARCHIVE, "w:bz2" )
    t.add( "torque" )
    t.close()

# change back to the build dir
if os.path.dirname( sys.argv[0] ) != "":
    os.chdir( os.path.dirname( sys.argv[0] ) )

# find setuptools
scramble_lib = os.path.join( "..", "..", "..", "lib" )
sys.path.append( scramble_lib )
try:
    from setuptools import *
    import pkg_resources
except:
    from ez_setup import use_setuptools
    use_setuptools( download_delay=8, to_dir=scramble_lib )
    from setuptools import *
    import pkg_resources

# get the tag
if os.access( ".galaxy_tag", os.F_OK ):
    tagfile = open( ".galaxy_tag", "r" )
    tag = tagfile.readline().strip()
else:
    tag = None

TORQUE_VERSION = ( tag.split( "_" ) )[1]
TORQUE_ARCHIVE = os.path.abspath( os.path.join( "..", "..", "..", "archives", "torque-%s.tar.gz" %TORQUE_VERSION ) )
TORQUE_BINARY_ARCHIVE = os.path.abspath( os.path.join( "..", "..", "..", "archives", "torque-%s-%s.tar.bz2" %( TORQUE_VERSION, pkg_resources.get_platform() ) ) )
CONFIGURE  = "CFLAGS='-O -g -isysroot /Developer/SDKs/MacOSX10.4u.sdk -arch i386 -arch ppc' "
CONFIGURE += "LDFLAGS='-Wl,-syslibroot,/Developer/SDKs/MacOSX10.4u.sdk -arch i386 -arch ppc' "
CONFIGURE += "./configure --prefix=/usr/local --disable-dependency-tracking --without-tcl --without-tk"

# clean, in case you're running this by hand from a dirty module source dir
for dir in [ "build", "dist", "torque-%s" %TORQUE_VERSION ]:
    if os.access( dir, os.F_OK ):
        print "scramble_it.py: removing dir:", dir
        shutil.rmtree( dir )

# build/unpack Torque
unpack_prebuilt_torque()

print "scramble_it(): Running pbs_python configure script"
p = subprocess.Popen( args = "sh configure --with-pbsdir=torque/usr/local/lib", shell = True )
r = p.wait()
if r != 0:
    print "scramble_it(): pbs_python configure script failed"
    sys.exit( 1 )

# version string in 2.9.4 setup.py is wrong
file = "setup.py"
print "scramble_it(): Patching", file
if not os.access( "%s.orig" %file, os.F_OK ):
    shutil.copyfile( file, "%s.orig" %file )
i = open( "%s.orig" %file, "r" )
o = open( file, "w" )
for line in i.readlines():
    if line == "	version = '2.9.0',\n":
        line = "	version = '2.9.4',\n"
    print >>o, line,
i.close()
o.close()

# tag
me = sys.argv[0]
sys.argv = [ me ]
if tag is not None:
    sys.argv.append( "egg_info" )
    sys.argv.append( "--tag-build=%s" %tag )
sys.argv.append( "bdist_egg" )

# go
execfile( "setup.py", globals(), locals() )
