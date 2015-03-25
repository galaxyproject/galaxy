#   Filter data received from University of Washington's Annotation programs
  
#####################################################################################
#    Variables and configuration
#####################################################################################
options(java.parameters="-Xmx4g"); 
#   Load libaries we need
library(stringr, quietly=TRUE);
#   library(xlsx) was causing problems with Galaxy, as it output a message when loading, even when
#       quietly=TRUE was set in the call to library();  We tried outputting to /dev/null, using
#       suppressWarnings(), etc., but the technique below is the only one that worked.
suppressPackageStartupMessages(library(xlsx, quietly=TRUE));
run.script <- TRUE; #   default is TRUE
#   If you wish to debug this script, e.g. in a standalone Galaxy instance, or on your
#       own development machine, set "debug" to true and set a path to which write debug
#       information.
#   For example:
#
#                   debug <- TRUE;
#                   debug.file <- "/path/to/debug/file.txt";
#
debug <- FALSE; #   default is FALSE
debug.file <- "";
testing <- FALSE;   #   default is FALSE
options(warn=-1);
max.columns <- 46; #    Maximum number of columns expected in the SeattleSeq output
input.ethnicity <- "Caucasian";
filter.cutoff.percent <- 5; #   default percentage; actual percentage is captured below

#   We expect the input data file has these column names, in this order
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
                                 "X.",  #   R assigns "X." as generic header names.  Additional HGMD references (if any) stored in this column
                                 "X..1",    #   Additional HGMD references (if any) stored in this column
                                 "X..2",    #   Additional HGMD references (if any) stored in this column
                                 "X..3",    #   Additional HGMD references (if any) stored in this column
                                 "X..4",    #   Additional HGMD references (if any) stored in this column
                                 "X..5",    #   Additional HGMD references (if any) stored in this column
                                 "X..6",    #   Additional HGMD references (if any) stored in this column
                                 "X..7",    #   Additional HGMD references (if any) stored in this column
                                 "X..8");   #   Additional HGMD references (if any) stored in this column

#####################################################################################
#    Support functions
#####################################################################################
#   Some values in the ESPEurAlleleCounts field contain a double-asterisk (**) appended to the value
#       This indicates that the value in the ESPEurMinorPercent value is inverted.  For example if the
#       value in ESPEurAlleleCounts is:
#
#               T=6953/A=1555**
#   
#       and the value in ESPEurMinorPercent is 82, then we need to convert the 82 to 18.  
convert.inverted.ESP.values <- function(input.data, ethnicity) {
    variants.to.invert <- which(str_detect(input.data$ESPEurAlleleCounts, "\\*\\*"));
    values.to.invert <- input.data[variants.to.invert,]$ESPEurMinorPercent;
    values.to.invert <- 100 - values.to.invert;
    values.to.invert <- input.data[variants.to.invert,]$ESPEurMinorPercent <- values.to.invert;
    return(input.data);
}   #   convert.inverted.ESP.values()

#   Format filtering results; this function adds a meaningful rejection message to each
#       rejected variant.  It supplements the "reject.code" also assigned to each variant
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

#   This is used for debugging purposes only; it compares actual results to expected results
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


#####################################################################################
#    Primary functions
#####################################################################################

##########################################################################################################
#   Perform some error-checking
##########################################################################################################
error.check.data <- function(raw.data) {    

    raw.data <- raw.data[,1:max.columns];
    
    #   Validate file structure by checking that the imported column names match what
    #       we expect.  If there is a difference, alert the user
    #   We use a loop to process most of the columns, but treat columns 8-10 (inclusive) separately,
    #       since they vary from Excel file to Excel file
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
    if(col.name.error)
        stop("Error detected in loaded data; check formatting, schema, etc.");
    return(raw.data);
}  #   error.check.data()

##########################################################################################################
#   Pre-process the data  
##########################################################################################################
pre.process.data <- function(raw.data)  {

    #   Convert columns appropriately
    #   As-is, the read.xlsx2() function returns a data frame where all columns are factors.
    #       This would make the filtering difficult.  
    #   Though we could choose to specify colClasses for the read.xlsx2() function, we instead simply 
    #       perform explicit type conversion here.  
    #   Note that some of the variables (e.g. position) have multiple conversions.  This is required
    #       to perform the conversion correctly
    raw.data$chrom <- as.character(raw.data$chrom);   #   column #1
    raw.data$position <- as.integer(as.character(raw.data$position));
    raw.data$type <- as.character(raw.data$type);
    raw.data$refBase <- as.character(raw.data$refBase);
    raw.data$altBase <- as.character(raw.data$altBase);
    raw.data$filterFlagGATK <- as.character(raw.data$filterFlagGATK);
    raw.data$QUAL <- as.numeric(as.character(raw.data$QUAL));
    raw.data[,8] <- as.character(raw.data[,8]);   #   Type
    raw.data[,9] <- as.character(raw.data[,9]);   #   Depth
    raw.data[,10] <- as.integer(as.character(raw.data[,10]));   #   Qual
    raw.data$functionGVS <- as.character(raw.data$functionGVS);
    raw.data$ESPEurAlleleCounts <- as.character(raw.data$ESPEurAlleleCounts);
    raw.data$ESPEurMinorPercent <- as.numeric(as.character(raw.data$ESPEurMinorPercent));
    raw.data$X1000GenomesEur. <- as.character(raw.data$X1000GenomesEur.);
    raw.data$clinVar <- as.character(raw.data$clinVar);
    raw.data$phenotypeHGMD <- as.character(raw.data$phenotypeHGMD);
    
    #   Add additional columns to the data frame, for our internal use.  These fields will annotate the variant
    #       with our justification for rejecting it
    #   A reject code of "0" means the variant is a keeper, so we err on the conservative side, assuming
    #       that all variants are keepers (unless proven otherwise)
    raw.data$reject.code <- 0;
    raw.data$reject.message <- "";
    #   See function header for explanation
    raw.data <- convert.inverted.ESP.values(raw.data, input.ethnicity);
    return(raw.data);
}  #   pre.process.data()


#########################################################################################################
#   Filter the data based on various criteria related to:
#       - Frequencies
#       - Gene function
#       - Presence of ClinVar or HGMD references
#   For additional details on the filtering process, consult the appropriate documentation
##########################################################################################################
filter.data <- function(raw.data)   {

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
    #       These variants occur on the major columns A and B, in the filtering logic table
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
    
    ########################################################################################################
    #   Filter missenses, introns, and synonymous genes based on ClinVar and HGMD references
    ########################################################################################################
    #   Identify the variants that contain either ClinVar or HGMD entries
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
    
    ########################################################################################################
    #   Filter based on zygosity (2.7)
    ########################################################################################################    
    #   Identify column in raw.data that contains the relevant scores
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
    #   This could be vectorized, if performance becomes a problem (not expected, but possible)
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
    
    ########################################################################################################
    #   Filter based on GATK score
    ########################################################################################################        
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


create.hyperlinked.workbook <- function(input.data.frame, output.file) {

    #   Define hyperlink base
    pubmed.base <- "http://www.ncbi.nlm.nih.gov/pubmed?term=";
    
    #   create new workbook with a worksheet
    wb <- createWorkbook(type="xls");
    createSheet(wb, sheetName="filtered_variants");
    sheet <- getSheets(wb);
    sheet <- sheet[[1]];    #   There is only one sheet in the workbook to get

    
    #   add the existing filtered data.frame to the worksheet
    addDataFrame(input.data.frame, sheet, row.names=FALSE);
    #   identify the cells that need hyperlinked, and hyperlink them
    for(i in 37:max.columns)    {
        #   identify the rows for that column that need hyperlinked
        rows.to.hyperlink <- which(input.data.frame[,i] != "");
        if(length(rows.to.hyperlink) == 0)
            next;

        #   hyperlink them
        for(j in 1:length(rows.to.hyperlink))   {
            #   grab the text string that's part of the hyperlink
            pubmed.id <- as.character(input.data.frame[rows.to.hyperlink[j],i]);
            #   grab the appropriate cell
            rows <- getRows(sheet, (rows.to.hyperlink[j] + 1));    #   we add one to skip the header line
            cell <- getCells(rows, colIndex=i);
            #   add the hyperlink
            addHyperlink(cell[[1]], paste(pubmed.base, pubmed.id, sep="")); #   there is only one cell, since we're loop processing
        }   #   for j
    }   #   for i
    #   save changes to the workbook
    saveWorkbook(wb, file=output.file);

}   #   create.hyperlinked.workbook()



###################################################################################################
#   "main" program below
###################################################################################################
if(run.script)  {
    cat("Running filtering script\n");
    cat("Capturing parameter values and input and output file paths from Galaxy");

    input.files.with.paths <- commandArgs(trailingOnly=TRUE)[1];
    output.files.with.paths <- commandArgs(trailingOnly=TRUE)[2];
    filter.cutoff.percent <- as.numeric(commandArgs(trailingOnly=TRUE)[3]);
    
    if(debug)   {
        cat("Input path: ", input.files.with.paths, "\n", file=debug.file);
        cat("Output path: ", output.files.with.paths, "\n", file=debug.file, append=TRUE);
        cat("Filter cutoff percent (default is 5.0): ", filter.cutoff.percent, "\n", file=debug.file, append=TRUE);
    }
	#	read in data for processing
    tryCatch({
        cat("Loading input data\n");
        #   sheetIndices begin at 1.  At present the second worksheet output by the SeattleSeq annotation program
        #       is the worksheet that we filter on
        raw.data <- read.xlsx2(input.files.with.paths, sheetIndex=2, colIndex=1:max.columns);
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
            create.hyperlinked.workbook(filtered.data, temp.file);
#            write.xlsx2(filtered.data, 
#                       file=temp.file,
#                       sheetName="filtered_variants",
#                       row.names=FALSE);
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






























