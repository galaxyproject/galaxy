#!/usr/bin/env python

"""
Script to query cBioPortal database using webservice.do and write response to a loc file.
"""
import os
from optparse import OptionParser
import cbp_common


def main():
	parser = OptionParser()
	parser.add_option("--input", dest="input", help="cBioPortal table to query")
	#parser.add_option("--output", dest="output", help="output file containing results of cBioPortal database query")
	parser.add_option("--log_level", dest="log_level", default="INFO", help="log level (default is INFO)")
	parser.add_option("--log_file", dest="log_file", default="/tmp/cbioportal_get_database_info.log", help="log file (default is /tmp/cbioportal_get_database_info.log)")
	(options, args) = parser.parse_args()

	# get logger from cbp_common
	logger = cbp_common.get_logger(options)

	# table name is passed from Galaxy tool
	table_name = options.input

	logger.debug('getting data from %s table in cBioPortal database...' % table_name)
	if table_name == 'type_of_cancer':
		url = cbp_common.type_of_cancer_url
		# refresh the data in the type_of_cancer.loc file
		#cbp_common.write_cbioportal_webservice_data(url, os.path.join(cbp_common.galaxy_home, 'tool-data/cbioportal_type_of_cancer.loc'), logger)
	elif table_name == 'cancer_studies':
		url = cbp_common.cancer_studies_url
	
	# query cBioPortal's webservice, get data, and write to .loc file
	cbp_common.get_cbioportal_webservice_data(url, logger)
	logger.debug('finished calling cBioPortal webservice')
	

if __name__ == '__main__':
	main() 
