#!/usr/bin/python
"""
This script is a python Galaxy wrapper around the cBioPortal
importer tool to be used with the corresponding .xml file.
The importer tool allows for validating a study (checks metadata files),
importing a study (inserting into MySQL database), annotating a MAF file
(using annotation MySQL database), normalizing a mRNA expression file (Z-Score),
and removing a study (from the MySQL database)
"""
import subprocess
import sys
import os
import shutil
from optparse import OptionParser
import cbp_common

os.environ['PORTAL_HOME'] = cbp_common.portal_home_path # env var needs to be set for importer tool 
importer_tool_path = cbp_common.portal_home_path + '/importer/target' # path to importer tool jar file
#classpath = importer_tool_path + '/*' # 'CLASSPATH' must include importer jar file
classpath = '*' # 'CLASSPATH' must include importer jar file

# '$PORTAL_HOME/core/src/main/java/org/mskcc/cbio/portal/scripts')
portal_importer_tool_command = 'java -cp "%s" -Xmx6g org.mskcc.cbio.importer.PortalImporterTool ' % classpath
# each part of tool has different command line args
validate_command = portal_importer_tool_command + '-v \'%s\''
import_command = portal_importer_tool_command + '-i %s' 
annotation_command = portal_importer_tool_command + '-a %s:%s'
normalize_command = portal_importer_tool_command + '-n %s:%s:%s:%s'
remove_cancer_study_command = portal_importer_tool_command + '-d %s'
# importing segment data using main importer tool doesn't work, so call class directly
import_segment_data_command = 'java -cp "%s" org.mskcc.cbio.portal.scripts.ImportCopyNumberSegmentData --meta %s --data %s'



def restart_services(options, logger):
	"""Update type_of_cancer.loc file with newest data and restart tomcat service
	To update the .loc file, we recreate with the newest data by querying cBioPortal's webservice feature
	and writing the results to the type_of_cancer.loc file.

	Tomcat service needs to be restarted to propagate changes in cBioPortal database to the web application.
	"""
	#logger.debug('recreating .loc files with newest data...')
	# query cBioPortal's webservice, get data, and write to .loc file
	#cbp_common.write_cbioportal_webservice_data(cbp_common.type_of_cancer_url, os.path.join(cbp_common.galaxy_home, 'tool-data/cbioportal_type_of_cancer.loc'), logger)
	#logger.debug('finished calling cBioPortal webservice, .loc files updated')

	# call commands to restart tomcat service
	logger.debug('restarting tomcat service...')
	#restart_tomcat = subprocess.Popen('sudo /etc/init.d/tomcat6 restart', shell=True, stderr=subprocess.PIPE)
	tomcat_stop = subprocess.Popen('sudo /etc/init.d/tomcat6 stop', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	for line in tomcat_stop.stdout:
		logger.info(line)
	tomcat_stop.wait()

	tomcat_start = subprocess.Popen('sudo /etc/init.d/tomcat6 start', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	for line in tomcat_start.stdout:
		logger.info(line)
	tomcat_start.wait()
	

def main():
	"""Read in command line args, execute specified option for cBioPortal importer tool, restart tomcat
	
	There are 5 command line arguments to use with the tool:
	(1) validate (-v)	input: path to study directory
				output: validates the study
	(2) import (-i)		input: path to study directory; (optional):t/f skip study if already exists; t/f force overwrite of study
				output: info about success of import for data in study directory
	(3) annotate (-a) 	input: MAF file to be annotated; (optional) name of output file 
				output: annotated MAF file
	(4) normalize (-n)	input: GISTIC copy number data; expression data; name of output file; suffix for normal samples
				output: Z-score normalized expression data file
	(5) remove study (-d)	input: study identifier string of study to remove from cBioPortal database
				output: info about success of study removal
	"""
	parser = OptionParser()
	parser.add_option("--log_level", dest="log_level", default="DEBUG", help="set logger level (default is warning)")
	parser.add_option("--log_file", dest="log_file", default="/tmp/cbioportal_importer_tool.log.txt", help="log file name")
	parser.add_option("--tool", dest="tool", help="directory with cancer study to validate")
	### validation tool command line args
	parser.add_option("--validate_directory", dest="validate_directory", help="directory with cancer study to validate")
	### import tool command line args
	parser.add_option("--import_directory", dest="import_directory", help="directory with cancer study to import")
	parser.add_option("--import_overwrite", dest="import_overwrite", default="NO", help="Overwrite study data? (default = NO)")
	### annotate tool command line args
	parser.add_option("--annotate_maf", dest="annotate_maf", help="MAF file to annotate")
	parser.add_option("--annotate_output_file", dest="annotate_output_file", help="filename of MAF annotation output")
	### normalize tool command line args
	parser.add_option("--normalize_cna_file", dest="normalize_cna_file", help="CNA file to use for normalization")
	parser.add_option("--normalize_expression_file", dest="normalize_expression_file", help="expression file to use for normalization")
	parser.add_option("--normalize_output_file", dest="normalize_output_file", help="filename to use for normalization output")
	parser.add_option("--normalize_suffix", dest="normalize_suffix", default="-11", help="suffix used by normal sample TCGA barcodes [default='-11']")
	### delete cancer study tool command line args
	parser.add_option("--remove_cancer_study", dest="remove_cancer_study", help="cancer study identifer of cancer study to delete")
	(options, args) = parser.parse_args()
	

	# get logger from cbp_common
	logger = cbp_common.get_logger(options)

	# main work of program done here
	#with open(options.log_file, 'wb') as log_file:
	
	# validates files in a study directory
	if options.tool == 'validate':
		logger.info('validating cancer study...')
		command_string = validate_command % options.validate_directory
	
	# imports data in a study directory into cBioPortal MySQL database
	elif options.tool == 'import':
		logger.info('importing cancer study...')
		# if user doesn't want to accidently overwrite a study...
		if options.import_overwrite == 'NO':
			logger.debug('not forcing any overwriting...')
			# append flag to not overwrite a study (default)
			command_string = (import_command + ':t:f') % options.import_directory
		# if user wants to overwrite a study...
		elif options.import_overwrite == 'YES':
			logger.info('forcing overwrite of study in database...')
			# append flag to force an overwrite of study
			command_string = (import_command + ':f:t') % options.import_directory
	
	# annotates a MAF file using mutationassessor.org and Oncotator 
	elif options.tool == 'annotate':
		logger.info('annotating MAF...')
		# by default, annotation tool creates new MAF in dir of importer tool but we want in MAF dir, so we build new filename/path
		maf_path, maf_name = os.path.split(os.path.abspath(options.annotate_maf)) # tool likes an absolute path
		
		if options.annotate_output_file == '': # if no custom filename was supplied
			# build new filename by adding '_annotated' before file extension
			basename, extension = os.path.splitext(maf_name)
			new_maf_filename = basename + '_annotated' + extension
			command_string = annotation_command % (options.annotate_maf, os.path.join(maf_path, new_maf_filename))
		else:
			# otherwise we use supplied filename as new MAF filename
			command_string = annotation_command % (options.annotate_maf, os.path.join(maf_path, options.annotate_output_file))
	
	# normalizes mRNA expression data using GISTIC CNA data and an expression file
	elif options.tool == 'normalize':
		logger.info('normalizing expression data...')
		# we want to put output file in same dir as expression file (not default: importer tool dir)
		normalized_path, normalized_file = os.path.split(options.normalize_output_file)
		# if user doesn't specify a path for output file
		if normalized_path == '': 			
			expression_path, expression_file = os.path.split(options.normalize_expression_file) # we will use path of expression file
			options.normalize_output_file = os.path.join(expression_path, options.normalize_output_file) # add expression file's path to output file
		command_string = normalize_command % (options.normalize_cna_file, options.normalize_expression_file, options.normalize_output_file, options.normalize_suffix)
	
	# removes a study from the cBioPortal MySQL database
	elif options.tool == 'remove_cancer_study':
		logger.info('removing cancer study...')
		command_string = remove_cancer_study_command % options.remove_cancer_study
	else:
		logger.info('not a valid option')
		sys.exit(-1)
	
	logger.debug('executing command:  %s\n' % command_string)
	
	# execute command as new process
	process = subprocess.Popen(command_string, shell=True, stdout=subprocess.PIPE, stderr=sys.stdout, cwd=importer_tool_path)
	for line in process.stdout:
		logger.info(line)
	# wait until process has finished
	return_code = process.wait()
	
			
	### segment data must be imported with a separate class, and cancer study MUST already exist in database 
	if options.tool == 'import':
		for file in os.listdir(options.import_directory):
			#look through all metadata files 
			if file.startswith('meta_') and file != 'meta_study.txt': 
				with open(os.path.join(options.import_directory, file), 'r') as metafile:
					meta_fields = {}
					#get metadata key/value mapping
					for line in metafile:
						key, val = line.split(':', 1)
						meta_fields[key.strip()] = val.strip()
					#if we have segment data, we would like to import it?
					if meta_fields['genetic_alteration_type'] == 'SEGMENT':
						logger.debug('found a metadata file with genetic_alteration_type == SEGMENT')
						prefix, basename = file.split('meta_')
						#check to make sure we have a data file to go with our metadata
						for file in os.listdir(options.import_directory):
							if file == 'data_' + basename:
								logger.debug('found segment data and matching metadata file')
								#command_string = import_segment_data_command % (classpath, metafile, file)
								command_string = import_segment_data_command % (classpath, os.path.join(options.import_directory, 'meta_' + basename), os.path.join(options.import_directory, file))
								logger.debug('importing segment data with command: %s' % command_string)
								#segment_output = subprocess.Popen(command_string, shell=True, stdout=log_file, stderr=sys.stdout, cwd=importer_tool_path)
								segment_output = subprocess.Popen(command_string, shell=True, stdout=subprocess.PIPE, stderr=sys.stdout, cwd=importer_tool_path)
								for line in segment_output.stdout:
									logger.info(line)
								segment_output.wait()
								logger.debug('finished uploading segment data')
								# copy segment file to directory hosted by webserver
								logger.debug('copying %s to %s' % (file, cbp_common.webserver_directory))
								shutil.copy2(os.path.join(options.import_directory, file), cbp_common.webserver_directory)
								logger.debug('finished copying seg file')
	# update .loc files, restart galaxy, restart tomcat
	if options.tool == 'import' or options.tool == 'remove_cancer_study':
		restart_services(options, logger)
	sys.exit(0)

if __name__ == '__main__':
	main()




