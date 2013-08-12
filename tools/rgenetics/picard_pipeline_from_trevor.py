                                                                     
                                                                     
                                                                     
                                             
#!/usr/bin/env python
#Write and submit LSF file to perform alignment, recalibrate & clean bam, generate sequencing metrics, and call variants and indels.
#Modify default= values in the Options handling section to suit your environment
#v0.1 Aug 2010 by Trevor Pugh 

import os
import sys
import time

##################
#Options handling#
##################
from optparse import OptionParser, OptionGroup
def parse_options():
	usage = '%prog <fastq file> <output directory> [options] \nSplits fastq files by barcode, performs BWA alignment, calls indels/variants using GATK, and generates Picard metrics.\nFiles output to /output directory/fastq filename base/'

	parser = OptionParser(usage=usage)
	parser.add_option('-i', '--indexes', dest='indexes', default=None, help='PCR primer sequences used in this library OR index numbers [requires --index-table], separated by commas. e.g. ACTGAC,CATGTG,GTACCT or 1,2,3')
	parser.add_option('-t', '--threads', dest='threads', default=4, help='Number of threads for bwa to use for multi-threading mode during initial alignment. Default: %default')
	parser.add_option('--overwrite', dest='overwrite', default=False, action='store_true', help='Set to overwrite existing output directory, if it exists.')

	group = OptionGroup(parser, 'Programs')
	group.add_option('--javaPath', dest='javaPath', default='/source/jdk1.6.0_18/bin/java', help='Path to Java executable and associated options. Default: %default')
	group.add_option('--bwaPath', dest='bwaPath', default='/solexa/solexa_data/HPCGG/bin/bwa-0.5.8a/bwa', help='Path to bwa executable. Default: %default')
	group.add_option('--gatkPath', dest='gatkPath', default='/solexa/solexa_data/HPCGG/bin/GenomeAnalysisTK-1.0.4013/GenomeAnalysisTK.jar', help='Path to GATK jar file. Default: %default')
	group.add_option('--picardPath', dest='picardPath', default='/solexa/solexa_data/HPCGG/bin/picard-tools-1.29', help='Path to picard directory. Default: %default')
	group.add_option('--RscriptPath', dest='RscriptPath', default='/source/R-2.11.0/bin/Rscript', help='Path to Rscript executable. Default: %default.')
	parser.add_option_group(group)

	group2 = OptionGroup(parser, 'References')
	group2.add_option('--genome-ref', dest='refGenome_fasta', default='/solexa/solexa_data/HPCGG/Genomes/Human/Homo_sapiens_assembly19.fasta', help='Genome reference file in fasta format. Default: %default')
	group2.add_option('--bait-intervals', dest='bait_intervals', default='/solexa/solexa_data/HPCGG/references/ssCardioBait_hg19.interval_list', help='Interval_list file containing genome coordinates for each bait or probe. Default: %default')
	group2.add_option('--target-intervals', dest='target_intervals', default='/solexa/solexa_data/HPCGG/references/ssCardioROI_hg19.interval_list', help='Interval_list file containing genome coordinates for each target region. Default: %default')
	group2.add_option('--index-table', dest='index_table', default='/solexa/solexa_data/HPCGG/references/SureSelectBarcodes.txt', help='PCR barcode lookup table. Two columns: index number and sequence. Default: %default')
	group2.add_option('--dbsnp-ref', dest='refDbsnp_rod', default='/solexa/solexa_data/HPCGG/references/dbsnp_130_b37.rod', help='dbSNP reference file in ROD format. Default: %default')
	parser.add_option_group(group2)
	
	group3 = OptionGroup(parser, 'Skip functions')
	group3.add_option('--skip-lsf-header', dest='do_lsf_header', default=True, action='store_false', help='skip addition of bsub header to LSF file.')
	group3.add_option('--skip-bwa-alignment', dest='do_bwa_alignment', default=True, action='store_false', help='skip BWA alignment.')
	group3.add_option('--skip-gatk-recal', dest='do_gatk_recal', default=True, action='store_false', help='skip GATK bam recalibration and cleaning.')
	group3.add_option('--skip-picard-metrics', dest='do_picard_metrics', default=True, action='store_false', help='skip generation of Picard metrics.')
	group3.add_option('--skip-gatk-coverage', dest='do_gatk_coverage', default=True, action='store_false', help='skip GATK generating coverage metrics.')
	group3.add_option('--skip-gatk-calls', dest='do_gatk_calls', default=True, action='store_false', help='skip GATK calling of indels and sequence variants.')
	group3.add_option('--skip-lsf-submission', dest='do_lsf_submission', default=True, action='store_false', help='skip submission of lsf file to cluster.')
	parser.add_option_group(group3)
	
	(options, args) = parser.parse_args()
	
	return options, args

###########
#Functions#
###########
def splitFastqByBarcode():
	print 'splitFastqByBarcode'
	return file_prefixes

def write_lsf_header(output_subdirectory, prefix, threads):
	timestamp = time.ctime()
	bsub_err = os.path.join(output_subdirectory,prefix+'.bsub.err')
	bsub_out = os.path.join(output_subdirectory,prefix+'.bsub.out')
	s = ['#!/bin/bash\n',]
	s.append(' '.join(['#LSF submission file generated on', timestamp, 'by', sys.argv[0], '\n']))
	s.append(' '.join(['#BSUB','-J '+prefix,'-o '+bsub_out, '-e '+bsub_err, '-n 1', '-x', '-q 8core\n']) 
	return s

def bwa_alignment(fastq_file, lsf_file, out_dir, prefix, bwa, picard, refGenome_fasta, threads):
	lsf_file.write('#bwa_alignment: Perform BWA alignment, convert to sam and then bam format. Use Picard to mark duplicate reads and index.\n')
	prefix = os.path.join(out_dir,prefix)      #add output directory to prefix string
	#Files generated by this module, in order of creation
	sai_file =           prefix+'.sai'
	sam_file =           prefix+'.sam'
	clipped_sam_file =   prefix+'.clipped.sam'
	bam_file =           prefix+'.bam'
	sorted_bam_file =    prefix+'.sorted.bam'
	markdupes_bam_file = prefix+'.markdupes.bam'
	dupemetrics_file =   prefix+'.duplicateMetrics'
	bai_file =           prefix+'.bai'

	#Perform alignment and convert to bam format
	s = [" ".join([bwa, 'aln', '-t '+str(threads), refGenome_fasta, fastq_file, '>', sai_file, '\n']),]
	s.append( " ".join([bwa, 'samse', refGenome_fasta, sai_file, fastq_file, '>', sam_file, '\n'])
	s.append(" ".join([picard+'CleanSam.jar', 'INPUT='+sam_file, 'OUTPUT='+clipped_sam_file, 'VALIDATION_STRINGENCY=SILENT\n']))
	s.append(" ".join([picard+'SamFormatConverter.jar', 'INPUT='+clipped_sam_file, 'OUTPUT='+bam_file, 'VALIDATION_STRINGENCY=SILENT\n']))
	
	#Sort the bam file & mark duplicates
	s.append(" ".join([picard+'SortSam.jar', 'INPUT='+bam_file, 'OUTPUT='+sorted_bam_file, 'SORT_ORDER=coordinate VALIDATION_STRINGENCY=SILENT\n']))
	s.append(" ".join([picard+'MarkDuplicates.jar', 'INPUT='+sorted_bam_file, 'OUTPUT='+markdupes_bam_file, 'METRICS_FILE='+dupemetrics_file, 'VALIDATION_STRINGENCY=SILENT\n']))
	
	#Move .markdupes.bam to be the primary bam file and generate index.
	s.append(" ".join(['mv -f', prefix+'.markdupes.bam', bam_file, '\n']))
	s.append(.join([picard+'BuildBamIndex.jar', 'INPUT='+bam_file, 'OUTPUT='+bai_file, 'VALIDATION_STRINGENCY=SILENT\n']))

	#Remove intermediate .sorted.bam, sam, and sai files.
	s.append(.join(['rm -f', sai_file, sam_file, clipped_sam_file, sorted_bam_file, '\n']))

	s.append('\n')
	return s,bam_file

def gatk_recal_and_clean(bam_file, lsf_file, gatk, refGenome_fasta, refDbsnp_rod, RscriptPath):
	lsf_file.write('#gatk_recal_and_clean part 1: Generate covariates and use to recalibrate bam qualities.\n')
	output_dir = os.path.dirname(bam_file)
	prefix = os.path.splitext(os.path.basename(fastq_file))[0]
	
	recal_bam_file = os.path.join(output_dir,prefix+'.recal.bam')
	recal_bai_file = os.path.join(output_dir,prefix+'.recal.bai')
	realn_bam_file = os.path.join(output_dir,prefix+'.realn.bam')
	clean_bam_file = os.path.join(output_dir,prefix+'.cleaned.bam')
	clean_bai_file = os.path.join(output_dir,prefix+'.cleaned.bai')
	intervals_file = os.path.join(output_dir,prefix+'.realigned.intervals')
	
	prerecal_dir =  os.path.join(output_dir,'recal','pre')
	postrecal_dir = os.path.join(output_dir,'recal','post')
	covariatesPrerecal_file =  os.path.join(prerecal_dir, prefix+'.covariates.csv')
	covariatesPostrecal_file = os.path.join(postrecal_dir, prefix+'.covariates.csv')
	s = ['mkdir -p '+prerecal_dir,]
	s.append('mkdir -p '+postrecal_dir)

	#Recalibrate qualities (http://www.broadinstitute.org/gsa/wiki/index.php/Base_quality_score_recalibration)
	#1) Generate covariates pre-recalibration
	s.append(" ".join([gatk, '-T CountCovariates', '--input_file '+bam_file, '-recalFile '+covariatesPrerecal_file, '--reference_sequence '+refGenome_fasta, '--DBSNP '+refDbsnp_rod, '--default_platform illumina --validation_strictness SILENT -cov ReadGroupCovariate -cov QualityScoreCovariate -cov CycleCovariate -cov DinucCovariate'])
	#2) Recalibrate Scores & recreate index
	s.append(" ".join([gatk, '-T TableRecalibration', '--input_file '+bam_file, '-recalFile '+covariatesPrerecal_file, '--reference_sequence '+refGenome_fasta, '-outputBam '+recal_bam_file, '--default_platform illumina'])
	s.append(" ".join([picard+'BuildBamIndex.jar', 'INPUT='+recal_bam_file, 'OUTPUT='+recal_bai_file, 'VALIDATION_STRINGENCY=SILENT'])
	#3) Generate covariates post-recalibration
	s.append(" ".join([gatk, '-T CountCovariates', '--input_file '+recal_bam_file, '-recalFile '+covariatesPostrecal_file, '--reference_sequence '+refGenome_fasta, '--DBSNP '+refDbsnp_rod, '--default_platform illumina --validation_strictness SILENT -cov ReadGroupCovariate -cov QualityScoreCovariate -cov CycleCovariate -cov DinucCovariate'])
	#4) Analyze Covariates before and after recalibration
	analyzeCovariates = os.path.dirname(gatk)+'/AnalyzeCovariates.jar'
	resourcesDir = os.path.dirname(gatk).split()[-1]+'/resources/'
	s.append(" ".join([analyzeCovariates, '-recalFile '+covariatesPrerecal_file, '-outputDir '+os.path.dirname(covariatesPrerecal_file), '-Rscript '+RscriptPath, '-resources '+resourcesDir, '-ignoreQ 5'])
	s.append(" ".join([analyzeCovariates, '-recalFile '+covariatesPostrecal_file, '-outputDir '+os.path.dirname(covariatesPostrecal_file), '-Rscript '+RscriptPath, '-resources '+resourcesDir, '-ignoreQ 5'])
	#Clean bam file (local realignment around indels)
	s.append('#gatk_recal_and_clean part 2: Perform local re-alignments around likely indels.')
	#1)Find intervals to be Realigned
	s.append(" ".join([gatk, '-T RealignerTargetCreator', '--input_file '+recal_bam_file, '--reference_sequence '+refGenome_fasta, '--out '+intervals_file])
	#2)Perform Realignment on regions
	s.append(" ".join([gatk, '-T IndelRealigner', '--input_file '+recal_bam_file, '--reference_sequence '+refGenome_fasta, '--targetIntervals '+intervals_file, '--output '+realn_bam_file])
	#3)Fix mate pair information, also sorts bam by coordinates for subsequent indexing
	s.append(" ".join([picard+'FixMateInformation.jar', 'INPUT='+realn_bam_file, 'OUTPUT='+clean_bam_file, 'SORT_ORDER=coordinate VALIDATION_STRINGENCY=SILENT'])
	#4) Build Index for cleaned BAM file
	s.append(" ".join([picard+'BuildBamIndex.jar', 'INPUT='+clean_bam_file, 'OUTPUT='+clean_bai_file, 'VALIDATION_STRINGENCY=SILENT'])

	#Remove realn and recal files as cleaned bam incorporates recalibrated qualities and realignments
	s.append(" ".join(['rm -f', recal_bam_file, recal_bai_file, realn_bam_file])

	return s,clean_bam_file

def picard_metrics(bam_file, lsf_file, picard, bait_intervals, target_intervals, refGenome_fasta):
	lsf_file.write('#picard_metrics: Assess QC metrics using Picard tools.\n')
	prefix=os.path.splitext(os.path.basename(bam_file))[0]
	picard_outdir = os.path.join(os.path.dirname(bam_file),'picard')
	picard_out = os.path.join(picard_outdir,prefix+'.')
	s = ['mkdir -p '+picard_outdir,]

	#Each line corresponds to a specific Picard tool
	s.append(" ".join([picard+'BamIndexStats.jar INPUT='+bam_file,'> '+picard_out+'BamIndexStats.txt', 'VALIDATION_STRINGENCY=SILENT'])
	s.append(" ".join([picard+'CalculateHsMetrics.jar INPUT='+bam_file, 'OUTPUT='+picard_out+'CalculateHsMetrics.txt', 'BAIT_INTERVALS='+bait_intervals, 'TARGET_INTERVALS='+target_intervals, 'VALIDATION_STRINGENCY=SILENT'])
	s.append(" ".join([picard+'CollectAlignmentSummaryMetrics.jar INPUT='+bam_file, 'OUTPUT='+picard_out+'CollectAlignmentSummaryMetrics.txt', 'REFERENCE_SEQUENCE='+refGenome_fasta, 'VALIDATION_STRINGENCY=SILENT']))
	s.append(" ".join([picard+'CollectGcBiasMetrics.jar INPUT='+bam_file, 'OUTPUT='+picard_out+'CollectGcBiasMetrics.txt', 'REFERENCE_SEQUENCE='+refGenome_fasta, 'SUMMARY_OUTPUT='+picard_out+'CollectGcBiasMetricsSummary.txt', 'CHART_OUTPUT='+picard_out+'CollectGcBiasMetrics.pdf', 'VALIDATION_STRINGENCY=SILENT']))
	s.append(" ".join([picard+'MeanQualityByCycle.jar INPUT='+bam_file, 'OUTPUT='+picard_out+'MeanQualityByCycle.txt', 'CHART_OUTPUT='+picard_out+'MeanQualityByCycle.pdf','VALIDATION_STRINGENCY=SILENT']))
	s.append(" ".join([picard+'QualityScoreDistribution.jar INPUT='+bam_file, 'OUTPUT='+picard_out+'QualityScoreDistribution.txt', 'CHART_OUTPUT='+picard_out+'QualityScoreDistribution.pdf','VALIDATION_STRINGENCY=SILENT']))
	#lsf_file.write(" ".join([picard+'CollectInsertSizeMetrics.jar INPUT='+bam_file, 'OUTPUT='+picard_out+'CollectInsertSizeMetrics.txt', 'HISTOGRAM_FILE='+picard_out+'CollectInsertSizeMetrics.pdf','VALIDATION_STRINGENCY=SILENT\n']))
	#lsf_file.write(" ".join([picard+'EstimateLibraryComplexity.jar INPUT='+bam_file, 'OUTPUT='+picard_out+'EstimateLibraryComplexity.txt','VALIDATION_STRINGENCY=SILENT\n']))

	return s

def gatk_coverage_metrics(bam_file, lsf_file, bait_intervals, target_intervals, refGenome_fasta):
	lsf_file.write('#gatk_coverage_metrics: Calculate coverage metrics for target regions\n')
	prefix=os.path.splitext(os.path.basename(bam_file))[0]
	cov_outdir = os.path.join(os.path.dirname(bam_file), 'cov')
	bait_cov_file = os.path.join(cov_outdir,prefix+'.bait.cov')
	target_cov_file = os.path.join(cov_outdir,prefix+'.target.cov')
	lsf_file.write('mkdir -p '+cov_outdir+'\n')

	#Bait coverage summary
	s = [" ".join([gatk, '-T DepthOfCoverage', '--input_file '+bam_file, '--out '+bait_cov_file, '--reference_sequence '+refGenome_fasta, '--intervals '+bait_intervals, '--outputFormat rtable\n']),]
	# Target coverage summary
	s.append('\n')
	s.append(" ".join([gatk, '-T DepthOfCoverage', '--input_file '+bam_file, '--out '+target_cov_file, '--reference_sequence '+refGenome_fasta, '--intervals '+target_intervals, '--outputFormat rtable\n'])
	return s

def gatk_call_variants_indels(bam_file, lsf_file, target_intervals, refGenome_fasta, refDbsnp_rod):
	s = ['#gatk_call_variants_indels: Call SNPs and indels.',]
	prefix = str(os.path.splitext(bam_file)[0])
	indel_bed_file = prefix+'.indels.bed'
	indel_full_file = prefix+'.indels'
	snp_file = prefix+'.snps.vcf'
	allbases_file = prefix+'.allbases.vcf'

	#Call indels
	s.append(" ".join([gatk, '-T IndelGenotyperV2', '--input_file '+bam_file, '--outputFile '+indel_bed_file, '--out '+indel_full_file, '--reference_sequence '+refGenome_fasta, '--intervals '+target_intervals, '--verbose --minFraction 0.1\n'])
	#Call sequence variants only at sites of variation
	s.append(" ".join([gatk, '-T UnifiedGenotyper', '--input_file '+bam_file, '--variants_out '+snp_file, '--reference_sequence '+refGenome_fasta, '--intervals '+target_intervals, '--DBSNP '+refDbsnp_rod, '--platform solexa -mmq 10 -mbq 10 -mm40 3 -stand_call_conf 30 -stand_emit_conf 30 -A DepthOfCoverage -A AlleleBalance -A SpanningDeletions\n'])
	#Call genotypes for all bases in ROI
	s.append(" ".join([gatk, '-T UnifiedGenotyper', '--input_file '+bam_file, '--variants_out '+allbases_file, '--reference_sequence '+refGenome_fasta, '--intervals '+target_intervals, '--DBSNP '+refDbsnp_rod, '--platform solexa -mmq 10 -mbq 10 -mm40 3 -stand_call_conf 30 -stand_emit_conf 30 -A DepthOfCoverage -A AlleleBalance -A SpanningDeletions --output_all_callable_bases \n'])
	#Filter sequence variants
	#java -jar GenomeAnalysisTK.jar -T VariantFiltration -R resources/Homo_sapiens_assembly18.fasta -o snps.filtered.vcf -B variant,VCF,snps.raw.vcf -B mask,Bed,indels.mask.bed --maskName InDel --clusterWindowSize 10 --filterExpression "QUAL < 30.0 || AB > 0.75 && DP > 40 || QD < 5.0 || HRun > 5 || SB > -0.10" --filterName "StandardFilters" --filterExpression "MQ0 >= 4 && ((MQ0 / (1.0 * DP)) > 0.1)" --filterName "HARD_TO_VALIDATE"
	#Filter indels (from http://www.broadinstitute.org/gsa/wiki/index.php/Whole_exome)
	#perl/filterSingleSampleCalls.pl --calls detailed.output.bed --max_cons_av_mm 3.0 --max_cons_nqs_av_mm 0.5 --mode ANNOTATE > indels.filtered.bed
	return s

##############
#Main program#
##############

#Collect and parse command line arguments
options, args = parse_options()
try:
	original_fastq_file = args[0]
	output_directory = args[1]
except IndexError:
	print 'Fastq filename or output directory not provided. Use option -h for help.'
	sys.exit()
	
bwa = options.bwaPath
java = options.javaPath+' -Xmx4g -Djava.io.tmpdir=/tmp'
picard = java+' -jar '+options.picardPath+'/'
gatk = java+' -jar '+options.gatkPath+' --logging_level INFO'

#If indexes provided, divide reads into separate fastq files for each barcode, otherwise use original fastq as-is.
if options.indexes != None:
	fastq_files = splitFastqByBarcode(options.original_fastq_file, index)
else:
	fastq_files = [original_fastq_file]

#Write & submit LSF file for each fastq listed in fastq_names
for fastq_file in fastq_files:
	prefix=os.path.splitext(os.path.basename(fastq_file))[0]  #output files have same name as fastq but different extension
	output_subdirectory = os.path.join(output_directory, prefix)       #output files will be in output_directory/fastq_name/

	#Make output directory but fail if --overwrite not provided (prevents accidental clobbering of output files)
	if not os.path.exists(output_subdirectory):
		os.makedirs(output_subdirectory)
	elif options.overwrite == False:
		print 'Output directory already exists: '+output_subdirectory
		print 'Use --overwrite to replace this directory and its contents.'
		sys.exit(1)

	#Run modules
	lsf_filename = os.path.join(output_subdirectory,prefix+'.lsf')
	lsf_file = open(lsf_filename,'w')
	runCmds = []
	if(options.do_lsf_header):
         runCmds = write_lsf_header(output_subdirectory, prefix, options.threads)
	if(options.do_bwa_alignment):  
        s,bam_file = bwa_alignment(fastq_file, lsf_file, output_subdirectory, prefix, bwa, picard, options.refGenome_fasta, options.threads)
        if s: 
            runCmds += s
	else:
        bam_file = os.path.join(output_subdirectory,prefix)+'.bam'
	if(options.do_gatk_recal):     
        s,clean_bam_file = gatk_recal_and_clean(bam_file, lsf_file, gatk, options.refGenome_fasta, options.refDbsnp_rod, options.RscriptPath)
        if s:
            runCmds += s
	else:
        clean_bam_file = os.path.join(output_subdirectory,prefix)+'.cleaned.bam'
	if(options.do_picard_metrics): 
        runCmds += picard_metrics(clean_bam_file, lsf_file, picard, options.bait_intervals, options.target_intervals, options.refGenome_fasta)
	if(options.do_gatk_coverage):  
        runCmds += gatk_coverage_metrics(clean_bam_file, lsf_file, options.bait_intervals, options.target_intervals, options.refGenome_fasta)
	if(options.do_gatk_calls):
        runCmds += gatk_call_variants_indels(clean_bam_file, lsf_file, options.target_intervals, options.refGenome_fasta, options.refDbsnp_rod)

	lsf_file.write('\n'.join(runCmds))
    lsf_file.write('\n')
	
	#Submit LSF file to cluster
	if(options.do_lsf_submission): os.system('%s < %s' % (submitCmd,submitCmd_filename)

sys.exit(0)