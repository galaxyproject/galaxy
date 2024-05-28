<%!
import collections
import json
import sys
from numpy import inf

from galaxy.exceptions import RequestParameterInvalidException

MAX_SIZE = 100000  # 100 KB
%>

<%
def to_counter(state, ordering):
    """Transforms given state to Counter using given ordering."""
    state = eval(state)
    if state[0] == inf:
        return inf
    return +collections.Counter({ordering[i]: state[i] for i in range(len(ordering))})


def node_to_string(node):
    """Creates string representation of Counter of agents."""
    if node == inf:
        return "inf"
    return "<br>".join([str(int(v)) + " " + str(k) for k, v in node.items()])


def side_to_string(side):
    """Another string representation of Counter, this time used as side in reaction."""
    if side == inf:
        return "inf"
    return " + ".join([str(int(v)) + " " + str(k) for k, v in side.items()])


def create_sides(lhs, rhs):
    """From given substrates and products counters creates their mutual differences."""
    if lhs == inf:
        return inf, inf
    if rhs == inf:
        return collections.Counter(), inf
    left = lhs - rhs
    right = rhs - lhs
    return left, right


def write_node(ID, label, node_class):
    """Creates string representation of a node."""
    if label == "inf":
        node_class = "hell"
    return "\t\t{{id: {0}, label: '{0}', class: '{2}', shape: 'ellipse', title: '{0}', text: '{1}'}},\n".format(
        ID, label, node_class)


def write_reaction(edge_id, left_index, right_index, substrates, products, rate, label):
    """Creates string representation of a reaction."""
    rate = " @ " + str(rate) if rate else ""
    label = label + " ~ " if label else ""
    return "\t\t{{id: {}, from: {}, to: {}, arrows: 'to', text: '{}{} => {}{}'}},\n".format(
        edge_id, left_index, right_index, label, side_to_string(substrates), side_to_string(products), rate)


def load_data():
    output = {"nodes": "", "border_nodes": "", "edges": "", "edges": "", "self_loops": ""}

    lines = []
    size = 0

    for line in hda.datatype.dataprovider(hda, 'line', strip_lines=True, strip_newlines=True):
        size += len(line)
        if size > MAX_SIZE:
            raise RequestParameterInvalidException("Dataset too large to render, dataset must be less than 100 KB in size.")
        lines.append(line)
    data = json.loads("".join(lines))

    ordering = data['ordering']
    nodes = {int(key): to_counter(data['nodes'][key], ordering) for key in data['nodes'].keys()}

    border_nodes = set()
    edges = []
    self_loops = []

    for edge_id, edge in enumerate(data['edges'], 1):
        substrates, products = create_sides(nodes[edge['s']], nodes[edge['t']])
        if edge['s'] == edge['t']:
            self_loops.append((edge_id, edge['s'], edge['t'], substrates,
                               products, edge.get('p', None), edge.get('label', None)))
        edges.append((edge_id, edge['s'], edge['t'], substrates, products,
                      edge.get('p', None), edge.get('label', None)))
        if products == inf and substrates != inf:
            border_nodes.add(edge['s'])

    border_nodes_write = []
    for id, state in nodes.items():
        if id in border_nodes:
            node_class = "border"
            border_nodes_write.append((id, node_to_string(state), node_class))
        else:
            node_class = "default"
        output["nodes"] += write_node(id, node_to_string(state), node_class)

    for node in border_nodes_write:
        output["border_nodes"] += write_node(*node)

    for edge in edges:
        output["edges"] += write_reaction(*edge)

    for edge in self_loops:
        output["self_loops"] += write_reaction(*edge)

    iterations = (len(nodes)//100+1) * 100

    output["iterations"] = iterations
    output["step"] = iterations//100
    output["fromNode"] = str(int(data['initial']))
    return output


root = h.url_for("/static/")
app_root = root + "plugins/visualizations/ts_visjs/static/"
output = load_data()
%>

## ----------------------------------------------------------------------------

<!DOCTYPE HTML>
<html>
<head>
    <title>TS network visualisation</title>

    ${h.javascript_link(app_root + "dist/vis.min.js")}
    ${h.stylesheet_link(app_root + "dist/vis.min.css")}
    ${h.stylesheet_link(app_root + "style.css")}

</head>
<body>
    <div id="mynetwork"></div>

    <aside>
        <table>
          <tbody>
            <tr>
              <td>
                <img src="${app_root + 'icons/border.png'}" alt="border states" style="display: block; width: 60px;">
              </td>
            </tr>
            <tr class="switch_button">
              <td class="switch_td">
                <label class="switch">
                  <input type="checkbox" name="check" id='border_nodes'>
                  <span class="slider round"></span>
                </label>
              </td>
            </tr>
            <tr>
              <td>
                <img src="${app_root + 'icons/loop.png'}" alt="self-loop" style="display: block; width: 60px;">
              </td>
            </tr>
            <tr class="switch_button">
              <td class="switch_td">
                <label class="switch">
                  <input type="checkbox" name="check" id="loop_edges" checked>
                  <span class="slider round"></span>
                </label>
              </td>
            </tr>
            <tr>
              <td>
                <img src="${app_root + 'icons/fire.png'}" alt="hell state" style="display: block; width: 60px;">
              </td>
            </tr>
            <tr>
              <td class="switch_td">
                <label class="switch">
                  <input type="checkbox" name="check" id="hell_node" checked>
                  <span class="slider round"></span>
                </label>
              </td>
            </tr>
          </tbody>
        </table>
    </aside>

    <div id="rectangle"style="width:94%;border:1px solid #000;"> </div>

    <div id="loadingBar">
        <div class="outerBorder">
            <div id="text">0%</div>
            <div id="border">
                <div id="bar"></div>
            </div>
        </div>
    </div>

    <script type="text/javascript">
        var nodes = new vis.DataSet([ ${output["nodes"]} ]);
        var border_nodes = [ ${output["border_nodes"]} ];
        var edges = new vis.DataSet([ ${output["edges"]} ]);
        var self_loops = [ ${output["self_loops"]} ];
        var fromNode = ${output["fromNode"]};

        var def_iterations = ${output["iterations"]};
        var def_updateInterval = ${output["step"]};
    </script>

    ${h.javascript_link(app_root + "script.js")}

</body>
</html>
