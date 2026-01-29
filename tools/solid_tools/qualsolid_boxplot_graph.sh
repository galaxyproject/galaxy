#!/bin/sh

#    Modified fastq_quality_boxplot_graph.sh from FASTX-toolkit - FASTA/FASTQ preprocessing tools.
#    Copyright (C) 2009  A. Gordon (gordon@cshl.edu)
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as
#   published by the Free Software Foundation, either version 3 of the
#   License, or (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

function usage()
{
	echo "SOLiD-Quality BoxPlot plotter"
	echo "Generates a SOLiD quality score box-plot graph "
	echo
	echo "Usage: $0 [-i INPUT.TXT] [-t TITLE] [-p] [-o OUTPUT]"
	echo
	echo "  [-p]           - Generate PostScript (.PS) file. Default is PNG image."
	echo "  [-i INPUT.TXT] - Input file. Should be the output of \"solid_qual_stats\" program."
	echo "  [-o OUTPUT]    - Output file name. default is STDOUT."
	echo "  [-t TITLE]     - Title (usually the solid file name) - will be plotted on the graph."
	echo
	exit 
}

#
# Input Data columns: #pos	cnt	min	max	sum       	mean	Q1	med	Q3	IQR	lW	rW
#  As produced by "solid_qual_stats" program

TITLE=""					# default title is empty
FILENAME=""
OUTPUTTERM="set term png size 800,600"
OUTPUTFILE="/dev/stdout"   			# Default output file is simply "stdout"
while getopts ":t:i:o:ph" Option
	do
	case $Option in
		# w ) CMD=$OPTARG; FILENAME="PIMSLogList.txt"; TARGET="logfiles"; ;;
		t ) TITLE="for $OPTARG" ;;
		i ) FILENAME=$OPTARG ;;
		o ) OUTPUTFILE="$OPTARG" ;;
		p ) OUTPUTTERM="set term postscript enhanced color \"Helvetica\" 4" ;;
		h ) usage ;;
		* ) echo "unrecognized argument. use '-h' for usage information."; exit -1 ;;
	esac
done
shift $(($OPTIND - 1)) 


if [ "$FILENAME" == "" ]; then
	usage
fi

if [ ! -r "$FILENAME" ]; then
	echo "Error: can't open input file ($1)." >&2
	exit 1
fi

#Read number of cycles from the stats file (each line is a cycle, minus the header line)
#But for the graph, I want xrange to reach (num_cycles+1), so I don't subtract 1 now.
NUM_CYCLES=$(cat "$FILENAME" | wc -l) 

GNUPLOTCMD="
$OUTPUTTERM
set boxwidth 0.8 
set size 1,1
set key Left inside
set xlabel \"read position\"
set ylabel \"Quality Score \"
set title  \"Quality Scores $TITLE\"
#set auto x
set bars 4.0
set xrange [ 0: $NUM_CYCLES ]
set yrange [-2:45]
set y2range [-2:45]
set xtics 1 
set x2tics 1
set ytics 2
set y2tics 2
set tics out
set grid ytics
set style fill empty
plot '$FILENAME' using 1:7:11:12:9 with candlesticks lt 1  lw 1 title 'Quartiles' whiskerbars, \
      ''         using 1:8:8:8:8 with candlesticks lt -1 lw 2 title 'Medians'
"

echo "$GNUPLOTCMD" | gnuplot > "$OUTPUTFILE"
