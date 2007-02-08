from base.twilltestcase import TwillTestCase
import pdb, sys, os, random
from datetime import datetime
from time import localtime, strftime, sleep

import pkg_resources
pkg_resources.require('twill')
pkg_resources.require('sqlalchemy>=0.2')
import twill
import twill.commands as tc
from twill import execute_file
from sqlalchemy import *

import sys, os, sets, random, pdb


class UcscTests(TwillTestCase):

    def test_00_first(self): # will run first due to its name
        """Simultaneous_Loads: Clearing history"""
        self.clear_history()

    def test_10_simultaneous_loads(self):
        """Simultaneous_Loads: loading"""

        #grant rights to pentaho
        rights = [	"dataset",	"dataset_id_seq",	"event",	"event_id_seq",	"galaxy_session",		\
			"galaxy_session_id_seq",	"galaxy_session_to_history",	"galaxy_session_to_history_id_seq",	\
			"galaxy_user",	"galaxy_user_id_seq",	"history",	"history_id_seq",	"job",	"job_id_seq",	\
			"job_parameter",	"job_parameter_id_seq",	"job_to_input_dataset",	"job_to_input_dataset_id_seq",	\
			"job_to_output_dataset",	"job_to_output_dataset_id_seq"						\
		]
        for right in rights : 
	    print "psql -q -h lonnie  -d jbhe_tests -c \"grant all on %s to pentaho\"  " % right 
	    os.system( "psql -q -h lonnie  -d jbhe_tests -c \"grant all on %s to pentaho\"  " % right )


	#tools' params
	testdir = "/home/jbhe/galaxy_2.2/test-data/"
	loaddir = "/home/jbhe/galaxy_2.2/test-data/load_test/"
	filenames_temp = os.listdir(loaddir)
	filenames = []
	users = []
	tools = []
	ii = 0 
	n = 0 
	while n < 40 : 
	   for filename in filenames_temp : 
              if filename.rfind("script") != -1: 
	         fpin  = open( loaddir + filename) 
	         fpout = open( loaddir + "load_test.twill." + str(ii), "w" )
	         filenames.append(loaddir + "load_test.twill." + str(ii) )
	         users.append("test"+str(ii)+"@bx.psu.edu")
	         tools.append(filename )
	         lines = fpin.read()
	         lines = lines.replace("test0", str(loaddir+"test"+str(ii)))
	         lines = lines.replace("localhost:9999", "lonnie.bx.psu.edu:9005")
	         lines = lines.replace('file_data\t"test-data/', str('file_data\t"'+testdir) )
	         fpout.write(lines)
	         fpin.close()
	         fpout.close()
	         ii = ii + 1
           n = n + 1 
	print filenames
   
	   
	#prepare users' cookie, parameters, and so on
	i=0
	while i < ii :
	   #---------clear cookie and create user-------------
	   tc.clear_cookies()
	   params_user = dict( email = "test"+str(i)+"@bx.psu.edu", password="12345678", confirm ="12345678",)
           print "\nCreating user(", params_user["email"], ") and login ...\n"
	   self.go2myurl("/user/create")
           self.submit_form(1, button="Create", **params_user)
	   #---------create history and save cookie---------
           print "Save user(", params_user["email"], ")...\n"
           self.go2myurl("/history_rename")
           params_user = dict( name =  "test"+str(i) )
           self.submit_form(button="history_rename_btn",**params_user)
	   tc.save_cookies(loaddir + "test"+str(i)+".jar") 
           i = i + 1
     

	#multiple users: Load test
	hosts     = ["kenny",	"butters",	"cartman",	"tweek",	"craig"] 
#	hosts_cmd = [""] 
	hosts_cmd = [" ls & ", " ls & ", " ls & ", " ls & ", " ls & "] 
	i = 0
	j = 0
	while i < ii :
	   hosts_cmd[j] = hosts_cmd[j] + str("twill-sh %s & " % filenames[i] ) 
	   j = j + 1
	   if j ==len(hosts): j = 0
#           if i < 20 : k = 0
#           else : k = random.randint(0, len(filenames)-1)
#           hosts_cmd[-1] = hosts_cmd[-1] + str("twill-sh %s & " % filenames[k] )
#           del filenames[k]
#	   j = j + 1
#           if j == 80 : 
#              hosts_cmd.append("")
#              j = 0
	   i = i + 1

	os.system( "echo 'Test begins!' > %sjob.log " % loaddir)  
	h = 0
        while h < len(hosts) : 
#           h = random.randint(0, len(hosts)-1)
	   print      "ssh -q %s ' %s ' >> %sjob.log " % (hosts[h], hosts_cmd[h], loaddir)  
#	   os.system( "ssh -q %s ' %s ' >> %sjob.log " % (hosts[h], hosts_cmd[h], loaddir) )
	   os.system( "ssh -q %s ' %s ' " % (hosts[h], hosts_cmd[h]) )
	   h = h + 1

        self.wait(maxiter=2000)
#	sleep(40*n)


    def test_20_simultaneous_loads(self):
        """Simultaneous_Loads: checking"""
	sleep(10)
        self.wait(maxiter=2000)


	#put statistics of the jobs to database "jbhe_tests_stat"
	loaddir = "/home/jbhe/galaxy_2.2/test-data/load_test/"
	filenames_temp = os.listdir(loaddir)
	i=0
	for filename in filenames_temp : 
           if filename.rfind("jar") != -1: i = i + 1 
        sqlstr = "create table job_stat(revision varchar(15), num_users int, total_users int, activity varchar(63), avg_life float, date timestamp with time zone ); "
	sqlstr = sqlstr + "insert into job_stat SELECT 1345, num_users, %s, tool_id, EXTRACT (EPOCH FROM avg_lifetime) AS avg_life_in_secs, update_time " % str(i) 
	sqlstr = sqlstr + "FROM ( SELECT count(history_id) AS num_users, tool_id, avg(lifetime) AS avg_lifetime, max(update_time) as update_time "
	sqlstr = sqlstr + "FROM ( SELECT history_id,  tool_id, (update_time - create_time) AS lifetime, update_time FROM job ORDER BY tool_id ) AS foo "
	sqlstr = sqlstr + "WHERE foo.lifetime != '00:00:00' GROUP BY tool_id ORDER BY tool_id ) AS bar; "
	sqlstr = sqlstr + "copy job_stat to '/home/jbhe/galaxy_2.2/test-data/load_test/job_stat.txt' "
	os.system( "psql -q -h lonnie  -d jbhe_tests -c \"%s\"  " % sqlstr )
	sqlstr = "copy job_stat from '/home/jbhe/galaxy_2.2/test-data/load_test/job_stat.txt' "
	os.system( "psql -q -h lonnie  -d jbhe_tests_stat -c \"%s\"  " % sqlstr )

	

	#tools' params
	filenames_temp = os.listdir(loaddir)
	filenames_data = []
	filenames_data_prop = []
	ii = 0 
	for filename in filenames_temp : 
           if filename.rfind("script") != -1: 
	      fpin = open( loaddir + filename) 
	      filenames_data.append(filename.replace("script", "dat"))
	      filenames_data_prop.append( fpin.readline().replace("#", "") )
	      fpin.close()
	      ii = ii + 1
	print filenames_data
	print filenames_data_prop
   
	   
	#check data name and content
	i=0
	while i < ii :
	   tc.clear_cookies()
	   tc.load_cookies(loaddir + "test"+str(i)+".jar") 
	   print "login user(test"+str(i)+"@bx.psu.edu) and check"
	   print i, filenames_data[i]
	   self.switch_history()
	   self.wait(maxiter=2000)
           self.check_data(filenames_data[i])
	   self.check_data_prop( filenames_data_prop[i])
           i = i + 1
	tc.clear_cookies()

	#remove temporary twill scripts and cookies
	filenames_temp = os.listdir(loaddir)
	i=0
	for filename in filenames_temp : 
           if filename.rfind("twills") != -1 or filename.rfind("jar") != -1: 
	      os.remove( loaddir + filename )
	      i = i + 1 








#	path = loaddir
#	if os.path.exists("load_test.job") : 
#	   os.remove("test-data/load_test/load_test.job")
#	fp = open("test-data/load_test/load_test.job", "w") 
#          stime = localtime()
#	   create_time = datetime(stime[0], stime[1], stime[2], stime[3], stime[4] ,stime[5])
#          stime = localtime()
#	   update_time = datetime(stime[0], stime[1], stime[2], stime[3], stime[4] ,stime[5])
#	   fp.write("%s\t%s\t%s\t%s\t%s\n" % ( str(i), str(users[i]), str(create_time), str(update_time), str(tools[i]) ) )
