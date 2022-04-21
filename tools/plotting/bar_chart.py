#!/usr/bin/env python
"""
histogram_gnuplot.py <datafile> <xtic column> <column_list> <title> <ylabel> <yrange_min> <yrange_max> <grath_file>
a generic histogram builder based on gnuplot backend

   data_file    - tab delimited file with data
   xtic_column  - column containing labels for x ticks [integer, 0 means no ticks]
   column_list  - comma separated list of columns to plot
   title        - title for the entire histrogram
   ylabel       - y axis label
   yrange_max   - minimal value at the y axis (integer)
   yrange_max   - maximal value at the y_axis (integer)
                  to set yrange to autoscaling assign 0 to yrange_min and yrange_max
   graph_file   - file to write histogram image to
   img_size     - as X,Y pair in pixels (e.g., 800,600 or 600,800 etc.)


   This tool required gnuplot and gnuplot.py

anton nekrutenko | anton@bx.psu.edu
"""

import sys
import tempfile

import Gnuplot
import Gnuplot.funcutils

assert sys.version_info[:2] >= (2, 4)


def stop_err(msg):
    sys.stderr.write(msg)
    sys.exit()


def main(tmpFileName):
    skipped_lines_count = 0
    skipped_lines_index = []
    gf = open(tmpFileName, "w")

    try:
        in_file = open(sys.argv[1])
        xtic = int(sys.argv[2])
        col_list = sys.argv[3].split(",")
        title = 'set title "' + sys.argv[4] + '"'
        ylabel = 'set ylabel "' + sys.argv[5] + '"'
        ymin = sys.argv[6]
        ymax = sys.argv[7]
        img_file = sys.argv[8]
        img_size = sys.argv[9]
    except Exception:
        stop_err("Check arguments\n")

    try:
        int(col_list[0])
    except Exception:
        stop_err("You forgot to set columns for plotting\n")

    for i, line in enumerate(in_file):
        valid = True
        line = line.rstrip("\r\n")
        if line and not line.startswith("#"):
            row = []
            try:
                fields = line.split("\t")
                for col in col_list:
                    row.append(str(float(fields[int(col) - 1])))
            except Exception:
                valid = False
                skipped_lines_count += 1
                skipped_lines_index.append(i)
        else:
            valid = False
            skipped_lines_count += 1
            skipped_lines_index.append(i)

        if valid and xtic > 0:
            row.append(fields[xtic - 1])
        elif valid and xtic == 0:
            row.append(str(i))

        if valid:
            gf.write("\t".join(row))
            gf.write("\n")

    if skipped_lines_count < i:
        # Prepare 'using' clause of plot statement
        g_plot_command = " "

        # Set the first column
        if xtic > 0:
            g_plot_command = "'%s' using 1:xticlabels(%s) ti 'Column %s', " % (tmpFileName, str(len(row)), col_list[0])
        else:
            g_plot_command = "'%s' using 1 ti 'Column %s', " % (tmpFileName, col_list[0])

        # Set subsequent columns
        for i in range(1, len(col_list)):
            g_plot_command += "'%s' using %s t 'Column %s', " % (tmpFileName, str(i + 1), col_list[i])

        g_plot_command = g_plot_command.rstrip(", ")

        yrange = "set yrange [" + ymin + ":" + ymax + "]"

        try:
            g = Gnuplot.Gnuplot()
            g("reset")
            g("set boxwidth 0.9 absolute")
            g("set style fill  solid 1.00 border -1")
            g("set style histogram clustered gap 5 title  offset character 0, 0, 0")
            g("set xtics border in scale 1,0.5 nomirror rotate by 90 offset character 0, 0, 0")
            g("set key invert reverse Left outside")
            if xtic == 0:
                g("unset xtics")
            g(title)
            g(ylabel)
            g_term = "set terminal png tiny size " + img_size
            g(g_term)
            g_out = 'set output "' + img_file + '"'
            if ymin != ymax:
                g(yrange)
            g(g_out)
            g("set style data histograms")
            g.plot(g_plot_command)
        except Exception:
            stop_err("Gnuplot error: Data cannot be plotted")
    else:
        sys.stderr.write("Column(s) %s of your dataset do not contain valid numeric data" % sys.argv[3])

    if skipped_lines_count > 0:
        sys.stdout.write(
            "\nWARNING. You dataset contain(s) %d invalid lines starting with line #%d.  These lines were skipped while building the graph.\n"
            % (skipped_lines_count, skipped_lines_index[0] + 1)
        )


if __name__ == "__main__":
    # The tempfile initialization is here because while inside the main() it seems to create a condition
    # when the file is removed before gnuplot has a chance of accessing it
    gp_data_file = tempfile.NamedTemporaryFile("w")
    Gnuplot.gp.GnuplotOpts.default_term = "png"
    main(gp_data_file.name)
