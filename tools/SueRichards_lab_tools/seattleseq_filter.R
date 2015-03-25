#   Filter data received from University of Washington's Annotation programs

#   Things to grab in the Galaxy UI:
#   - ethnicity:  place this in a variable named "ethnicity"
#   - are we performing carrier screening?  Relates to heterozygosity vs. homozygosity
#   - filter cutoff percentage:  save in "filter.cutoff.percent"
#
#   In the original Excel work process, "discarded" records (e.g. those that did not
#       meet the filter criteria) were kept within the Excel workbook.  This formed
#       documentation / provenance for the workflow.  Keeping in the spirit of this
#       we retain and save indices of records that this script removes from the "final" dataset
#      
options(java.parameters="-Xmx4g"); 
#   Setup for execution
#   Load libaries we need
library(stringr, quietly=TRUE);
#   library(xlsx) was causing problems with Galaxy, as it output a message when loading, even when
#       quietly=TRUE was set in the call to library();  We tried outputting to /dev/null, using
#       suppressWarnings(), etc., but the technique below is the only one that worked.
suppressPackageStartupMessages(library(xlsx, quietly=TRUE));

#####################################################################################
#    Variables and configuration here
#####################################################################################
run.script <- TRUE;
#####################################################################################
#   If you want to debug/test this script as a stand-alone for additional features,
#   enable the debug and testing to TRUE, and provide a path for debug.file
debug <- FALSE;
# debug.file <- "<path_for_debug_file";
testing <- FALSE;
#####################################################################################

#   We do some type conversions that are correct, but that raise warnings
#       TODO:  find a more elegant way to address warnings
options(warn=-1);
#   TODO:  the number of HGMD publication references can vary.  We assume here that there is a maximum
#       of ten total references (columns 37 through 46, inclusive).  Potentially there are more, so 
#       we should ideally detect at runtime the largest number of references, and proceed accordingly
max.columns <- 46; #    Maximum number of columns expected in the SeattleSeq output

#   Some values in the ESPEurAlleleCounts field contain a double-asterisk (**) appended to the value
#       This indicates that the value in the ESPEurMinorPercent value is inverted.  For example if the
#       value in ESPEurAlleleCounts is:
#
#               T=6953/A=1555**
#   
#       and the value in ESPEurMinorPercent is 82, then we need to convert the 82 to 18.  
#   TODO:  handle different cases based on ethnicity
convert.inverted.ESP.values <- function(input.data, ethnicity) {
    variants.to.invert <- which(str_detect(input.data$ESPEurAlleleCounts, "\\*\\*"));
    values.to.invert <- input.data[variants.to.invert,]$ESPEurMinorPercent;
    values.to.invert <- 100 - values.to.invert;
    values.to.invert <- input.data[variants.to.invert,]$ESPEurMinorPercent <- values.to.invert;
    return(input.data);
}   #   convert.inverted.ESP.values()
#
#
##   Output filtering results
add.rejection.justification <- function(input.data)   {
    #   Rejection case 1
    variants <- which(input.data$reject.code == 1);
    if(length(variants) > 0)
        input.data[variants,]$reject.message <- paste("Frequencies not adequate:  1000Genomes value: ", input.data[variants,]$X1000GenomesEur., ", ESP value: ", input.data[variants,]$ESPEurMinorPercent, sep="");
    variants <- which(input.data$reject.code == 2);
    if(length(variants) > 0)
        input.data[variants,]$reject.message <- paste("1000 Genomes and ESP frequencies OK, but functionGVS not adequate.  FunctionGVS value: ", input.data[variants,]$functionGVS, sep="");
    variants <- which(input.data$reject.code == 3);
    if(length(variants) > 0)
        input.data[variants,]$reject.message <- paste("1000 Genomes, ESP frequencies, and functionGVS OK, but no citations for ClinVar or HGMD");
    
    return(input.data);
    
}   #   add.rejection.justification()


##   Lookup table associating ethnicities to columns in the input data
#ethnicity <- c("Caucasian",
#               "African",
#               "Asian");
#
#ethnicity.thousand.column.name <- c("X1000GenomesEur.",
#                           "X1000GenomesAfr.",
#                           "X1000GenomesAsn.");
#
##   TODO:  is there supposed to be a value for "ESPAsnMinorPercent"?
##       We added one as a workaround, to make the data frame work.
#ethnicity.ESP.column.name <- c("ESPEurMinorPercent",
#                                 "ESPAfrMinorPercent",
#                                 "ESPAsnMinorPercent");
#
#ethnicity.lookup.table <- data.frame(ethnicity, 
#                                     ethnicity.thousand.column.name,
#                                     ethnicity.ESP.column.name,
#                                     stringsAsFactors=FALSE);
#

#   We expect the input data file has these column names, in this order
#   TODO:  I believe we expect variation in at least some of these columns, across files
#       Need to find a good way to check, without literal matches on column names
expected.col.names <- c("chrom",
                                 "position",
                                 "type",
                                 "refBase",
                                 "altBase",
                                 "filterFlagGATK",
                                 "QUAL",
                                 "PG0001599.BLDGType",
                                 "PG0001599.BLDDepth",
                                 "PG0001599.BLDQual",
                                 "geneList",
                                 "rsID",
                                 "createBuild",
                                 "functionGVS",
                                 "aminoAcids",
                                 "proteinPosition",
                                 "cDNAPosition",
                                 "genomeHGVS",
                                 "granthamScore",
                                 "scorePhastCons",
                                 "consScoreGERP",
                                 "scoreCADD",
                                 "polyPhen",
                                 "SIFT",
                                 "ESPEurAlleleCounts",
                                 "ESPEurMinorPercent",
                                 "ESPAfrAlleleCounts",
                                 "ESPAfrMinorPercent",
                                 "X1000GenomesEur.",
                                 "X1000GenomesAfr.",
                                 "X1000GenomesAsn.",
                                 "local507",
                                 "clinicalAssn",
                                 "OMIM",
                                 "clinVar",
                                 "phenotypeHGMD",
                                 "referenceHGMD", # Column 37
                                 "X.",  #   R assigns these as header names.  TODO:  rename them, e.g. "referenceHGMD 1" 
                                 "X..1",
                                 "X..2",
                                 "X..3",
                                 "X..4",
                                 "X..5",
                                 "X..6",
                                 "X..7",
                                 "X..8");



#ethnicity.filter.minor.column <- ethnicity.lookup.table[ethnicity.lookup.table$ethnicity 
#                                                        == input.ethnicity]$ethnicity.minor.column.name;


#######################################################################################
#   FOR DEBUGGING ONLY - TODO:  wire this up to Galaxy
#   Assume that the Subject is European, since the example file we're using to build
#       this script assumes European
input.ethnicity <- "Caucasian";
filter.cutoff.percent <- 5;
truncate.table.id <- FALSE;
if(truncate.table.id)
    cat("Note that truncate.table.id is set to TRUE\n\n");
#######################################################################################



#####################################################################################
#   Read in the data from the Excel file, and place it in a data structure suitable
#       for processing by R
#####################################################################################
#   TODO:  Figure out how Galaxy's going to interact with R
#   Using XLConnect we can easily grab the worksheet we need, e.g.:
#
#       wb <- loadWorkbook("<PATH/TO/WORKBOOK.xlsx>");
#       raw.data <- readTable(wb, sheet="<SHEET_NAME>");
#
#   XLConnect provides some functions for extracting the sheet name, etc.  
import.csv <- function(path.to.csv) {
    if(truncate.table.id){
        raw.data <- read.csv(file=path.to.csv, 
                         header=TRUE, 
                         stringsAsFactors=FALSE);
        #   Remove Table ID column
        raw.data[,1] <- NULL;
        #   Remove Keep column
        raw.data[,1] <- NULL;
        #   Save then delete Reject Code column
        reject.code.expected <- raw.data[,1];
        raw.data[,1] <- NULL;
    } else	{
#    	path.to.input.file <- commandArgs(trailingOnly=TRUE)[1];
        raw.data <- read.csv(file=path.to.csv,                  
                         header=TRUE, 
                         stringsAsFactors=FALSE);
#        #   Remove Table ID column
#         raw.data[,1] <- NULL;
#         #   Remove Keep column
#         raw.data[,1] <- NULL;
#         #   Save then delete Reject Code column
#         reject.code.expected <- raw.data[,1];
#         raw.data[,1] <- NULL;                    
    }   #   end else
    cat("Path to input file: ", path.to.csv, "\n");
    return(raw.data);
}  #   import.csv()


##########################################################################################################
#   Perform some error-checking
#   TODO:  Add some additional checks
##########################################################################################################
#   Remove empty columns.  DUring .csv imports from Excel R often adds additional 
#       blank columns.  We expect no more than 37 columns containing information, so we truncate
#       the data.frame at 37 columns.
error.check.data <- function(raw.data) {    

    raw.data <- raw.data[,1:max.columns];
    
    #   Validate file structure by checking that the imported column names match what
    #       we expect.  If there is a difference, alert the user
    #       TODO: wire this error-checking step up to Galaxy correctly; Galaxy must have some kind of mechanism to handle
    #           errors and/or alert the user
    #   We use a loop to process most of the columns, but treat columns 8-10 (inclusive) separately,
    #       since they vary from Excel file to Excel file
    #   TODO:  remove the dependence on column order
    #   TODO:  remove the dependence on columns.  Traditionally the columns included in the input file have varied from
    #       sample to sample.  While we should seek to look down required columns in a consistent format, we want the
    #       system to be robust enough to accept some amount of variation in columns
    raw.data.col.names <- colnames(raw.data);
    special.columns <- 8:10;
    col.name.error <- FALSE;
    problem.columns <- integer();
    for(i in 1:max.columns)  {
        if(i %in% special.columns)
            next;
        if(raw.data.col.names[i] != expected.col.names[i])  {
            col.name.error <- TRUE;
            problem.columns <- c(problem.columns, i);
        }
    }
    if(!str_detect(raw.data.col.names[8], "Type"))   {
        col.name.error <- TRUE;
        problem.columns <- c(problem.columns, 8);
    }
    if(!str_detect(raw.data.col.names[9], "Depth"))  {
        col.name.error <- TRUE;
        problem.columns <- c(problem.columns, 9);
    }
    if(!str_detect(raw.data.col.names[10], "Qual"))  {
        col.name.error <- TRUE;
        problem.columns <- c(problem.columns, 10);
    }
    #   TODO:  Alert Galaxy / the user if there is a mismatch
    if(col.name.error)
        stop("Error detected in loaded data; check formatting, schema, etc.");
    return(raw.data);
}  #   error.check.data()

##########################################################################################################
#   Pre-process the data  
#   TODO:  wire this up to ethnicity.  We currently assume that the sample is from a European origin,
#       since such samples account for nearly all samples presently processed by the lab
##########################################################################################################
pre.process.data <- function(raw.data)  {

    #   Convert columns appropriately
    #   As-is, the read.xlsx2() function returns a data frame for our dataset, which creates problems
    #       downstream with the filtering logic.  Though we could choose to specify colClasses for the
    #       read.xlsx2() function, we instead simply perform explicit type conversion here.  
    #   Note that some of the variables (e.g. position) have multiple conversions.  This is required
    #       to perform the conversion correctly
    raw.data$chrom <- as.character(raw.data$chrom);   #   column #1
    raw.data$position <- as.integer(as.character(raw.data$position));
    raw.data$type <- as.character(raw.data$type);
    raw.data$refBase <- as.character(raw.data$refBase);
    raw.data$altBase <- as.character(raw.data$altBase);
    raw.data$filterFlagGATK <- as.character(raw.data$filterFlagGATK);
    raw.data$QUAL <- as.numeric(raw.data$QUAL);
    raw.data[,8] <- as.character(raw.data[,8]);   #   GType
    raw.data[,9] <- as.character(raw.data[,9]);   #   BLDDepth
    raw.data[,10] <- as.integer(raw.data[,10]);   #   Qual
    raw.data$functionGVS <- as.character(raw.data$functionGVS);
    raw.data$ESPEurAlleleCounts <- as.character(raw.data$ESPEurAlleleCounts);
    raw.data$ESPEurMinorPercent <- as.numeric(as.character(raw.data$ESPEurMinorPercent));
    raw.data$X1000GenomesEur. <- as.character(raw.data$X1000GenomesEur.);
    raw.data$clinVar <- as.character(raw.data$clinVar);
    raw.data$phenotypeHGMD <- as.character(raw.data$phenotypeHGMD);
    
    #   TODO:  Rename the column names for X. through X..8.  These are the possibly empty columns that we read in, 
    #       case that there are additional HGMD references in them.  Since the headers in the Excel input file
    #       are blank when we call read.xlsx2(), R gives them the names X., X..1, X..2, etc.  These ideally
    #       should be renamed something like "referenceHGMD 1", referenceHGMD 2", etc.
    #   TODO:  make these hyperlinks (as they are in the initial spreadsheet generated by SeattleSeq)

    #   Add additional columns to the data frame, for our internal use.  These fields will annotate the variant
    #       with our justification for rejecting it
    raw.data$reject.code <- 0;
    raw.data$reject.message <- "";
    #   See function header for explanation
    raw.data <- convert.inverted.ESP.values(raw.data, input.ethnicity);
    return(raw.data);
}  #   pre.process.data()

filter.data <- function(raw.data)   {
    ##########################################################################################################
    #   Filter the data based on various criteria related to:
    #       - Frequencies
    #       - Gene function
    #       - Presence of ClinVar or HGMD references
    #   For additional details on the filtering process, consult the appropriate documentation
    ##########################################################################################################
    ##########################################################################################################
    #   Filter records based on 1000 Genomes and ESP frequencies
    ##########################################################################################################
    #   Capture records on Row 1 of filtering table
    frequency.variants.to.flag <- which((as.integer(raw.data$X1000GenomesEur.) > filter.cutoff.percent) & (raw.data$ESPEurMinorPercent > filter.cutoff.percent));
    #   Capture records on Row 3 of filtering table    
    frequency.variants.to.flag <- c(frequency.variants.to.flag,
                                        which((as.integer(raw.data$X1000GenomesEur.) > filter.cutoff.percent) & (raw.data$ESPEurMinorPercent == "-100")));
    #   Capture records on Row 7 of filtering table    
    frequency.variants.to.flag <- c(frequency.variants.to.flag,
                                        which((raw.data$X1000GenomesEur. == "unknown") & (raw.data$ESPEurMinorPercent > filter.cutoff.percent)));
    #   Make variants unique
    frequency.variants.to.flag <- unique(frequency.variants.to.flag);

    #   Flag variants that are rejected due for frequency reasons
    if(length(frequency.variants.to.flag) > 0)  {
        raw.data[frequency.variants.to.flag,]$reject.code <- 1;
        raw.data <- add.rejection.justification(raw.data);
    }   #   fi
    
    #   Create aggregate variables for use in later filtering steps
    rejected.variants <- frequency.variants.to.flag;
    contender.variants <- setdiff(1:length(raw.data[,1]), rejected.variants);
    
    cat("Completed filtering on frequencies. ", length(frequency.variants.to.flag), "variants rejected\n");
    ########################################################################################################
    #   Filter based on gene function
    ########################################################################################################
    #   Identify the variants that contain functionGVS values of interest
    #       These variants occur on the major columns A and B
    frameshift.variants <- which((str_detect(raw.data$functionGVS, "frameshift")));
    acceptor.variants <- which((str_detect(raw.data$functionGVS, "acceptor")));
    donor.variants <- which((str_detect(raw.data$functionGVS, "donor")));
    stop.variants <- which((str_detect(raw.data$functionGVS, "stop")));
    missense.variants <- which((str_detect(raw.data$functionGVS, "missense")));
    synonymous.variants <- which((str_detect(raw.data$functionGVS, "synonymous")));
    intron.variants <- which((str_detect(raw.data$functionGVS, "intron")));
    
    #   Aggregate the functionGVS rows
    OK.functionGVS.variants <- unique(c(frameshift.variants, 
                                 acceptor.variants, 
                                 donor.variants, 
                                 stop.variants,
                                 missense.variants,
                                 synonymous.variants,
                                 intron.variants));
    
    #   Identify and flag variants that are rejected because of the wrong gene function
    functionGVS.variants.to.flag <- setdiff(contender.variants, OK.functionGVS.variants);
    if(length(functionGVS.variants.to.flag) > 0)    {
        raw.data[functionGVS.variants.to.flag,]$reject.code <- 2;
        raw.data <- add.rejection.justification(raw.data);
    }   #   fi
    
    #   Update aggregate variables
    rejected.variants <- which(raw.data$reject.code != 0);
    contender.variants <- which(raw.data$reject.code == 0);
    
    cat("Completed filtering on gene function. ", length(functionGVS.variants.to.flag), "variants rejected\n");
    # ########################################################################################################
    # #   Filter missenses, introns, and synonymous genes based on ClinVar and HGMD references
    # ########################################################################################################
    # #   Identify the variants that contain either ClinVar or HGMD entries
    clinVar.variants <- which(!raw.data$clinVar == "none");
    HGMD.variants <- which(!raw.data$phenotypeHGMD == "none");
    
    #   Aggregate the clinVar and HGMD rows
    reference.variants <- unique(c(clinVar.variants, HGMD.variants));
    
    function.variants <- unique(c(missense.variants, synonymous.variants, intron.variants));
    
    #   Identify and flag missense variants that are rejected because of they lack annotation
    reference.variants.to.flag <- setdiff(function.variants, reference.variants);
    reference.variants.to.flag <- setdiff(reference.variants.to.flag, rejected.variants);
    if(length(reference.variants.to.flag) > 0)  {
        raw.data[reference.variants.to.flag,]$reject.code <- 3;
        raw.data <- add.rejection.justification(raw.data);
    }   #   fi
    
    #   Update aggregate variables
    rejected.variants <- which(raw.data$reject.code != 0);    
    contender.variants <- which(raw.data$reject.code == 0);    

    cat("Completed filtering on references. ", length(reference.variants.to.flag), "variants rejected\n");
    # ########################################################################################################
    # #   Filter based on zygosity (2.7)
    # ########################################################################################################    
    #   Identify column in raw.data that contains the relevant scores
    #   TODO:  fix header values - has varied between BLDDepth and CHR21Depth
    BLDDepth.col <- which(str_detect(colnames(raw.data), "Depth"));
    read.depth <- raw.data[,BLDDepth.col] 
    #   Break up the relevant column into separate columns
    #   Find parentheses locations

    open.paren.locations <- str_locate(read.depth, "\\(")[,1];
    closed.paren.locations <- str_locate(read.depth, "\\)")[,1];
    
    #   Extract only the parenthesized values
    read.depth.extract <- str_sub(read.depth, (open.paren.locations + 1), (closed.paren.locations - 1));
    
    #   Break the comma-separated values into two columns.  The stringr function we use is a bit 'unusual', 
    #       returning a list, so we use a loop to get what we want
    read.depth.extract <- str_split(read.depth.extract, ",");
    first.value <- integer();
    second.value <- integer();
    #   TODO:  vectorize this, it takes ~15 seconds on my laptop
    for(i in 1:length(read.depth.extract))  {
        first.value <- c(first.value, read.depth.extract[[i]][1]);
        second.value <- c(second.value, read.depth.extract[[i]][2]);
    }   #   for i
    
    #   Identify which of the records are homozygous by looking for values of the two variables
    #       first.value and second.value that are zero
    first.value.rows <- which(first.value == 0);
    second.value.rows <- which(second.value == 0);
    homozygous.variants.to.flag <- unique(c(first.value.rows, second.value.rows));
    homozygous.variants.to.flag <- setdiff(homozygous.variants.to.flag, rejected.variants);
    if(length(homozygous.variants.to.flag) > 0) {
        raw.data[homozygous.variants.to.flag,]$reject.code <- 4;
        raw.data <- add.rejection.justification(raw.data);
    }   #   fi

    #   Update aggregate variables
    rejected.variants <- which(raw.data$reject.code != 0);    
    contender.variants <- which(raw.data$reject.code == 0);    

    cat("Completed filtering on gene zygosity. ", length(homozygous.variants.to.flag), "variants rejected\n");
    # ########################################################################################################
    # #   Filter based on GATK score
    # ########################################################################################################        
    filterFlagGATK.variants.to.flag <- which(raw.data$filterFlagGATK != "PASS");
    filterFlagGATK.variants.to.flag <- setdiff(filterFlagGATK.variants.to.flag, rejected.variants);
    if(length(filterFlagGATK.variants.to.flag) > 0) {
        raw.data[filterFlagGATK.variants.to.flag,]$reject.code <- 5;
        raw.data <- add.rejection.justification(raw.data);    
    }   #   fi

    #   Update aggregate variables
    rejected.variants <- which(raw.data$reject.code != 0);    
    contender.variants <- which(raw.data$reject.code == 0);    

    cat("Completed filtering on filterFlagGATK score. ", length(filterFlagGATK.variants.to.flag), "variants rejected\n");
    return(raw.data);
}   #   filter.data()

process.results <- function(raw.data, path.and.filename)    {

    #   write out all variants
    output.file <- paste(path.and.filename, "_all.csv", sep="");   
#    if(!testing) {
#        write.csv(raw.data, file=output.file, sep=",");
        write.csv(raw.data, file="/home/leyshockp/galaxy/filtering/debug.csv", sep=",");
#    }   #`fi
    #   write out only "keeper" variants
    output.file <- paste(path.and.filename, "_actual.csv", sep="");
    final.index <- which(raw.data$reject.code == 0);
    final.result <- raw.data[final.index,];
    if(testing) {
        write.csv(final.result, file=output.file, sep=",");
    }  #    fi 
    cat("Results written to: ", output.file, "\n");
    return(final.result);
}   #   process.results()


check.for.errors <- function(actual.results, path.to.expected.results)  {

    cat("Path to expected results file: ", path.to.expected.results, "\n");
    #   read in expected results
    expected.variants <- scan(file=path.to.expected.results, what=character(), quiet=TRUE);

    #   Prepare the actual results for comparison to the expected results.
    #       We assume that the chromosome and position, when concatenated, form a unique ID for the variant.
    actual.variants <- paste(actual.results$chrom, ".", actual.results$position, sep="");

        #   Formatting
    cat("\nRESULTS ****************\n");
    #   Compare lengths
    cat(length(actual.variants), " actual variants found, ", length(expected.variants), " variants expected\n", sep="");
    
    #   Compare contents of actual vs. expected results
    #       The expected result should be a subset (proper or not) of the actual result.
    #       If it is not, our filtering logic incorrectly removed a variant
    missed.variants <- setdiff(expected.variants, actual.variants);
    if(length(missed.variants) > 0) {
        cat("At least one expected variant was not identified by the filtering logic.\n");
        cat("The unidentified variant(s) are:\n");
        print(missed.variants);
    }   else {
        cat("All expected variants found in actual variants\n");   
    }
    #   Formatting
    cat("************************\n\n");
}   #   check.for.errors()


#   The schema of the input files should match those described in supplemental documentation
#   The expected result files should consist of a text file, where each item is 'chrom.position',
#       one entry per line.   For example:
#
#                       1.234151
#                       1.899931
#                       3.9918935
#
input.files.with.paths <- c(#"./test_data/inputs/basic_test_suite.csv");    
#                            "./test_data/inputs/sample_3_test.csv",    #   not enough detail to generate a good "expected" file
#                             "./test_data/inputs/sample_5_test.csv",   #   not enough detail to generate a good "expected" file
                            "./test_data/inputs/sample_6_test.csv");
#                           "./test_data/inputs/sample_9_test.csv");#,
#                             "./test_data/inputs/sample_10_test.csv",
#                             "./test_data/inputs/sample_11_test.csv");    
#                            "./test_data/inputs/sample_12_test.csv",
#                              "./test_data/inputs/sample_13_test.csv",
#                              "./test_data/inputs/sample_14_test.csv");    
#                            "./test_data/inputs/sample_15_test.csv",   #   mixed-ethnicity, so holding off for now
#                            "./test_data/inputs/sample_16_test.csv",
#                              "./test_data/inputs/sample_17_test.csv",
#                              "./test_data/inputs/sample_18_test.csv");        
                                
expected.results.with.paths <- c(#"./test_data/expected/basic_test_suite_expected.txt");
#                            "./test_data/expected/sample_3_expected.txt",      #   not enough detail to generate a good "expected" file
#                             "./test_data/expected/sample_5_expected.txt",     #   not enough detail to generate a good "expected" file
                            "./test_data/expected/sample_6_expected.txt");
#                           "./test_data/expected/sample_9_expected.txt",
#                             "./test_data/expected/sample_10_expected.txt",
#                             "./test_data/expected/sample_11_expected.txt");
#                               "./test_data/expected/sample_12_expected.txt",
#                             "./test_data/expected/sample_13_expected.txt",
#                             "./test_data/expected/sample_14_expected.txt");
#                               "./test_data/expected/sample_15_expected.txt",  #   mixed-ethnicity, so holding off for now    
#                               "./test_data/expected/sample_16_expected.txt",
#                             "./test_data/expected/sample_17_expected.txt",
#                             "./test_data/expected/sample_18_expected.txt");
    
###################################################################################################
#   "main" program below
###################################################################################################

if(!testing)    {
    input.files.with.paths <- commandArgs(trailingOnly=TRUE)[1];
    if(debug)
        cat("Input path: ", input.files.with.paths, "\n", file=debug.file);
    output.files.with.paths <- commandArgs(trailingOnly=TRUE)[2];
    if(debug)
        cat("Output path: ", output.files.with.paths, "\n", file=debug.file, append=TRUE);
}   #   fi

if(run.script)  {
    cat("Running filtering script\n");
	#	read in data for processing
    tryCatch({
        cat("Loading input data\n");
        if(testing) {
            raw.data <- import.csv(input.files.with.paths[i]);
        } else {
            #   TODO:  removed dependence on sheetIndex = 2
            #   sheetIndices begin at 1.  At present the second worksheet output by the SeattleSeq annotation program
            #       is the "worksheet of interest"
            raw.data <- read.xlsx2(input.files.with.paths, sheetIndex=2, colIndex=1:max.columns);
        }   #   else
        if(debug)
            cat("Data imported\n", file=debug.file, append=TRUE);
    }, error = function(e)  {
        stop("Problem loading data: ", e, "\n");
    })  #   tryCatch, loading data
        
	#	check for errors
    tryCatch({
        cat("Checking data for errors\n");
        raw.data <- error.check.data(raw.data);
        if(debug)
            cat("Data checked for errors\n", file=debug.file, append=TRUE);
    }, error = function(e)  {
        stop("Problem with loaded data; check formatting, schema, etc.: ", e, "\n");
    })  #   tryCatch, error-checking data

    #	pre-process the data
    tryCatch({
        cat("Pre-processing data\n");
        pre.processed.data <- pre.process.data(raw.data);
        if(debug)
            cat("Data pre-processed\n", file=debug.file, append=TRUE);
     }, error = function(e) {
         stop("Problem pre-processing data: ", e, "\n");
     }) #   tryCatch, pre-processing

    #	filter the data
    tryCatch({
        cat("Filtering data\n");
        filtered.data <- filter.data(pre.processed.data);
        if(debug)
            cat("Data filtered\n", file=debug.file, append=TRUE);
    }, error = function(e)  {
        stop("Problem filtering data: ", e, "\n");
    })

    #   format and write out results
    tryCatch({
        cat("Writing out results\n");
        if(testing) {
            final.data <- process.results(filtered.data, input.files.with.paths[1]);
        }   else    {

            cat("Number of final variants: ", length(filtered.data[,1]), "\n");
            #   This is a workaround for getting Galaxy to recognize the output
            temp.file <- paste(output.files.with.paths, ".xls", sep="");
            write.xlsx2(filtered.data, 
                       file=temp.file,
                       sheetName="filtered_variants",
                       row.names=FALSE);
            move.command <- paste("mv ", temp.file, " ", output.files.with.paths, sep="");
            system(move.command);
        }   #   else
    }, error = function(e)  {
        stop("Problem writing out data: ", e, "\n");
    })

    #   compare actual results vs. expected results
    if(testing)
        check.for.errors(final.data, expected.results.with.paths[i]);
}   #   fi

