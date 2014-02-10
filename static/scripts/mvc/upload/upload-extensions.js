// dependencies
define([], function() {

var dictionary = {

    auto : {
        text: 'The system will attempt to detect Axt, Fasta, Fastqsolexa, Gff, Gff3, Html, Lav, Maf, Tabular, Wiggle, Bed and Interval (Bed with headers) formats. If your file is not detected properly as one of the known formats, it most likely means that it has some format problems (e.g., different number of columns on different rows). You can still coerce the system to set your data to the format you think it should be.  You can also upload compressed files, which will automatically be decompressed'
    },

    ab1 : {
        url : 'https://wiki.galaxyproject.org/Learn/Datatypes#Ab1',
        text: 'A binary sequence file in \'ab1\' format with a \'.ab1\' file extension.  You must manually select this \'File Format\' when uploading the file.'
    },

    axt : {
        url : 'https://wiki.galaxyproject.org/Learn/Datatypes#Axt',
        text: 'blastz pairwise alignment format.  Each alignment block in an axt file contains three lines: a summary line and 2 sequence lines.  Blocks are separated from one another by blank lines.  The summary line contains chromosomal position and size information about the alignment. It consists of 9 required fields.'
    },

    bam : {
        url : 'https://wiki.galaxyproject.org/Learn/Datatypes#BAM',
        text: 'A binary file compressed in the BGZF format with a \'.bam\' file extension.'
    },

    bed : {
        url : 'https://wiki.galaxyproject.org/Learn/Datatypes#Bed',
        text: 'BED format provides a flexible way to define the data lines that are displayed in an annotation track. BED lines have three required columns and nine additional optional columns. The three required columns are chrom, chromStart and chromEnd.'
    },

    fasta : {
        url : 'https://wiki.galaxyproject.org/Learn/Datatypes#Fasta',
        text: 'A sequence in FASTA format consists of a single-line description, followed by lines of sequence data. The first character of the description line is a greater-than (">") symbol in the first column. All lines should be shorter than 80 characters.'
    },
    
    fastq : {
        url : 'https://wiki.galaxyproject.org/Learn/Datatypes#Fastq',
        text: 'FASTQ format is a text-based format for storing both a biological sequence (usually nucleotide sequence) and its corresponding quality scores. '
    },

    fastqsolexa : {
        url : 'https://wiki.galaxyproject.org/Learn/Datatypes#FastqSolexa',
        text: 'FastqSolexa is the Illumina (Solexa) variant of the Fastq format, which stores sequences and quality scores in a single file.'
    },

    gff : {
        url : 'https://wiki.galaxyproject.org/Learn/Datatypes#GFF',
        text: 'GFF lines have nine required fields that must be tab-separated.'
    },
       
    gff3 : {
        url : 'https://wiki.galaxyproject.org/Learn/Datatypes#GFF3',
        text: 'The GFF3 format addresses the most common extensions to GFF, while preserving backward compatibility with previous formats.'
    },
    
    interval : {
        url : 'https://wiki.galaxyproject.org/Learn/Datatypes#GFF3',
        text: 'File must start with definition line in the following format (columns may be in any order).'
    },
    
    lav : {
        url : 'https://wiki.galaxyproject.org/Learn/Datatypes#GFF3',
        text: 'Lav is the primary output format for BLASTZ.  The first line of a .lav file begins with #:lav..'
    },

    maf : {
        url : 'https://wiki.galaxyproject.org/Learn/Datatypes#MAF',
        text: 'TBA and multiz multiple alignment format.  The first line of a .maf file begins with ##maf. This word is followed by white-space-separated "variable=value" pairs. There should be no white space surrounding the "=".'
    },
    
    scf : {
        url : 'https://wiki.galaxyproject.org/Learn/Datatypes#Scf',
        text: 'A binary sequence file in \'scf\' format with a \'.scf\' file extension.  You must manually select this \'File Format\' when uploading the file.'
    },
    
    sff : {
        url : 'https://wiki.galaxyproject.org/Learn/Datatypes#Sff',
        text: 'A binary file in \'Standard Flowgram Format\' with a \'.sff\' file extension.'
    },
    
    tabular : {
        url : 'https://wiki.galaxyproject.org/Learn/Datatypes#Tabular_.28tab_delimited.29',
        text: 'Any data in tab delimited format (tabular).'
    },
    
    wig : {
        url : 'https://wiki.galaxyproject.org/Learn/Datatypes#Wig',
        text: 'The wiggle format is line-oriented.  Wiggle data is preceded by a track definition line, which adds a number of options for controlling the default display of this track.'
    },
    
    txt : {
        url : 'https://wiki.galaxyproject.org/Learn/Datatypes#Plain_text',
        text: 'Any text file.'
    },

};

// create description content
return function(key) {
    var description = dictionary[key];
    if (description) {
        var tmpl = description.text;
        if (description.url) {
            tmpl += '&nbsp;(<a href="' + description.url + '" target="_blank">read more</a>)';
        }
        return tmpl;
    } else {
        return 'There is no description available for this file extension.';
    }
}
});
