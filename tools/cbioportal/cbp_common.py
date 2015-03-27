#!/usr/bin/python
"""
Variables/functions used by cBioPortal scripts:
cbioportal_importer_tool.py
cbioportal_create_files.py
cbioportal_get_database_info.py
"""
import logging
import urllib2
import sys
import os
import csv
from optparse import OptionParser



portal_home_path = '/data/cbioportal.org' # path to cBioPortal source code top directory
galaxy_home = '/opt/installed/galaxy-dist' # path to location of galaxy install
webserver_directory = '/mnt/lustre1/cBioPortal/datasets' # path to directory hosted by nginx web server

# urls to request types of cancers and cancer studies available through cBioPortal webservice
type_of_cancer_url='http://localhost/cBioPortal/webservice.do?cmd=getTypesOfCancer'
cancer_studies_url='http://localhost/cBioPortal/webservice.do?cmd=getCancerStudies'


def get_logger(options):
	# check logger command line arg
	numericLevel = getattr(logging, options.log_level.upper(), None)
	log_format = '%(asctime)-15s %(levelname)s %(funcName)s %(lineno)s %(message)s'
	if not isinstance(numericLevel, int):
		raise ValueError('Invalid log level: %s' % options.log_level)
	# if log level is DEBUG give user lots of info
	if options.log_level == 'DEBUG':
	 	log_format = '%(asctime)-15s %(levelname)s  function: %(funcName)s:%(lineno)s  %(message)s'
	else: # else make logger *pretty* for user
		log_format = '%(message)s'
	
	# create logger object
	logger = logging.getLogger(__name__)
	logger.setLevel(numericLevel)
	# set up logger that writes to file
	log_file = logging.FileHandler(options.log_file)
	log_file.setLevel(numericLevel)
	log_file.setFormatter(logging.Formatter(log_format))
	# set up logger that writes to stdout
	log_stdout = logging.StreamHandler(sys.stdout)
	log_stdout.setLevel(numericLevel)
	log_stdout.setFormatter(logging.Formatter(log_format))
	# add to logger object
	logger.addHandler(log_file)
	logger.addHandler(log_stdout)
	return logger



def write_cbioportal_webservice_data(url, outfile, logger):
	"""send URL request to cBioPortal webservice, WRITE response to file."""
	try:
		logger.debug('Querying: %s and WRITING to %s' % (url, outfile))
		request = urllib2.urlopen(url)
	except urllib2.URLError as e:
		logger.error(e)
		print e
		sys.exit(-1)
	#request results should be tab delimited
	try:
		reader = csv.reader(request, delimiter='\t')
		with open(outfile, 'w') as outfile:
			outwriter = csv.writer(outfile, delimiter='\t')
			reader.next() # if we keep header it shows up in galaxy drop-down menu
			for line in reader:
				outwriter.writerow(line)
			logger.debug('Finished writing response to %s' % outfile)
	except csv.Error as e:
		logger.error(e)
		print e


def get_cbioportal_webservice_data(url, logger):
	"""send URL request to cBioPortal webservice, LOG response."""
	try:
		logger.debug('Querying: %s and LOGGING response' % url)
		request = urllib2.urlopen(url)
		for line in request:
			# getting errors about encoding... this seems to fix the issue
			line = line.decode('iso8859-1')
			line = line.encode('utf-8')
			logger.info(line)
		logger.debug('Finished writing response to log')
	except urllib2.URLError as e:
		logger.error(e)
		print e
		sys.exit(-1)

#all possible genetic alteration types
genetic_alteration_type_list = ['COPY_NUMBER_ALTERATION', 'SEGMENT', 'MRNA_EXPRESSION', 'MUTATION_EXTENDED', 'FUSION', 'METHYLATION', 'RPPA', 'CLINICAL'];

#all possible datatypes
datatype_list = ['DISCRETE', 'LOG-VALUE', 'SEGMENT', 'CONTINUOUS', 'CONTINUOUS_rnaseq', 'CONTINUOUS_microarray', 'Z-SCORE', 'Z-SCORE_rnaseq', 'Z-SCORE_microarray', 'MAF', 'FUSION', 'FREE-FORM', 'CONTINUOUS_hm27', 'CONTINUOUS_hm450'];

#column definitions for importing data into cBioPortal
copy_number_alteration_cols = ['Hugo_Symbol', 'Entrez_Gene_Id'];
segment_cols = ['ID', 'chrom', 'loc.start', 'loc.end', 'num.mark', 'seg.mean'];
mrna_expression_cols = ['Hugo_Symbol', 'Entrez_Gene_Id'];
#mutation_cols = []; #TODO: add bare min cols necessary for importing to CBP
fusion_cols = ['Hugo_Symbol', 'Entrez_Gene_Id', 'Center', 'Tumor_Sample_Barcode', 'Fusion', 'DNA support', 'RNA support', 'Method', 'Frame'];
methylation_cols = ['Hugo_Symbol', 'Entrez_Gene_Id'];
rppa_cols = ['Composite.Element.REF'];

#meta_study.txt file fields 
meta_study_fields = ['type_of_cancer', 'cancer_study_identifier', 'name', 'description', 'citation', 'pmid', 'short_name'];

#metadata file fields 
meta_file_fields = ['cancer_study_identifier', 'genetic_alteration_type', 'datatype', 'stable_id', 'show_profile_in_analysis_tab', 'profile_description', 'profile_name'];

#case list fields for importing case list files into cBioPortal
case_list_fields = ['cancer_study_identifier', 'stable_id', 'case_list_name', 'case_list_description', 'case_list_ids'];

#datatypes for which 'show_profile_in_analysis_tab' metadata field should be true
show_datatypes_list = ['DISCRETE', 'Z-SCORE', 'Z-SCORE_rnaseq', 'Z-SCORE_microarray', 'MAF', 'FUSION'];
