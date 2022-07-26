<%!
import sys
from io import StringIO
import csv
%>

<%
def create_option(option, value, selected):
    return '\t\t<option value="{0}"{1}>{2}</option>\n'.format(value, " selected" if selected else "", option)

def create_options(header):
    default_colour = 2
    default_data_start = 5
    colour_options = ""
    for i in range(default_data_start):
        selected = False
        if i == default_colour:
             selected = True
        colour_options += create_option(header[i], i, selected)

    start_options = ""

    for i in range(len(header) - 2):
        selected = False
        if i == default_data_start:
            selected = True
        start_options += create_option(i, i, selected)

    return colour_options, start_options

def load_data():
    input = "\n".join(list(hda.datatype.dataprovider(hda, 'line', comment_char=none, provide_blank=True, strip_lines=False, strip_newlines=True)))
    tabular_file = StringIO(input)
    dialect = csv.Sniffer().sniff(tabular_file.read(1024), delimiters=";,\t")
    tabular_file.seek(0)
    table = csv.reader(tabular_file, dialect)
    data = "["
    for i, row in enumerate(table):
        if i == 0:
            header = row
        data += "\t" + str(row) + ",\n"
    data += "];\n"
    return data, header


root = h.url_for("/static/")
app_root = root + "plugins/visualizations/PCA_3Dplot/static/"
data, header = load_data()
colour_options, start_options = create_options(header)
%>

## ----------------------------------------------------------------------------

<!DOCTYPE HTML>
<html>
<head>

${h.javascript_link(app_root + "dist/d3.min.js")}
${h.javascript_link(app_root + "dist/plotly.min.js")}
${h.javascript_link(app_root + "dist/pca.min.js")}
${h.javascript_link(app_root + "script.js")}
${h.stylesheet_link(app_root + "style.css")}

<script type="text/javascript">
var data = ${data}
var header = ${header}
</script>
</head>

<body>
    <div id="wrapper">
        <div id="combos">
            <label for="colour_column">Colour column name</label>
            <select class="minimal" id="colour_column" onchange="colour_changed();">
                ${colour_options}
            </select>
            <label for="data_start">Data start column ID</label>
            <select class="minimal" id="data_start" onchange="data_start_changed();">
                ${start_options}
            </select>
        </div>
        <div id="visualisation"><!-- Plotly chart will be drawn inside this DIV --></div>
    </div>
</body>
</html>
