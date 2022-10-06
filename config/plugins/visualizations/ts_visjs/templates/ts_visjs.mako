<%!
import collections
import json
import sys
from numpy import inf
%>

<%
def to_counter(state, ordering):
    """
    Transforms given state to Counter using given ordering

    :param state: str representation of state
    :param ordering: enumeration of agents
    :return: Counter representing the state
    """
    state = eval(state)
    if state[0] == inf:
        return inf
    return +collections.Counter({ordering[i]: state[i] for i in range(len(ordering))})


def node_to_string(node):
    """
    Creates string representation of Counter of agents.

    :param node: given Counter of agents.
    :return: string representation of Counter
    """
    if node == inf:
        return "inf"
    return "<br>".join([str(int(v)) + " " + str(k) for k, v in node.items()])


def side_to_string(side):
    """
    Another string representation of Counter, this time used as side in reaction
    :param side: given Counter
    :return: string representation of Counter
    """
    if side == inf:
        return "inf"
    return " + ".join([str(int(v)) + " " + str(k) for k, v in side.items()])


def create_sides(lhs, rhs):
    """
    From given substrates and products counters creates their mutual differences

    :param lhs: dict of substrates
    :param rhs: dict of products
    :return: two counters representing differences
    """
    if lhs == inf:
        return inf, inf
    if rhs == inf:
        return collections.Counter(), inf
    left = lhs - rhs
    right = rhs - lhs
    return left, right


def write_node(ID, label, node_class):
    """
    Creates string representation of a node

    :param ID: ID of given node
    :param label: enumeration of agents
    :return: string representation
    """
    if label == "inf":
        node_class = "hell"
    return "\t\t{{id: {0}, label: '{0}', class: '{2}', shape: 'ellipse', title: '{0}', text: '{1}'}},\n".format(
        ID, label, node_class)


def write_reaction(edge_id, left_index, right_index, substrates, products, rate, label):
    """
    Creates string representation of a reaction

    :param edge_id: ID of given reaction
    :param left_index: ID of FROM node
    :param right_index: ID of TO node
    :param substrates: enumeration of substrates
    :param products: enumeration of products
    :param rate: rate of the reaction (if any)
    :param label: used rule label
    :return: string representation
    """
    rate = " @ " + str(rate) if rate else ""
    label = label + " ~ " if label else ""
    return "\t\t{{id: {}, from: {}, to: {}, arrows: 'to', text: '{}{} => {}{}'}},\n".format(
        edge_id, left_index, right_index, label, side_to_string(substrates), side_to_string(products), rate)


def create_HTML_graph(): #data):
    output_file = firstpart

    data = ''.join(list(hda.datatype.dataprovider(hda, 'line', strip_lines=True, strip_newlines=True)))
    data = json.loads(data)

    # data = json.load(data)

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
        output_file += write_node(id, node_to_string(state), node_class)

    output_file += mid_1

    for node in border_nodes_write:
        output_file += write_node(*node)

    output_file += mid_2

    for edge in edges:
        output_file += write_reaction(*edge)

    output_file += mid_3

    for edge in self_loops:
        output_file += write_reaction(*edge)

    initial = data['initial']

    iterations = (len(nodes)//100+1) * 100
    step = iterations//100

    output_file += secondpart_1_1
    output_file += stabil_physics.format(iterations, step)
    output_file += secondpart_1_2

    output_file += "\tvar fromNode = " + str(int(initial)) + ";\n"

    output_file += secondpart_2_1
    output_file += stabil_bar.format(iterations, step)
    output_file += secondpart_2_2
    return output_file


firstpart = \
'''<!doctype html>
<html>
<head>
    <title>TS network visualisation</title>

    ${h.javascript_link(app_root + "dist/vis.min.js")}
    # da sa to?
    ${h.stylesheet_link(app_root + "dist/vis.min.css")}
    ${h.stylesheet_link(app_root + "style.css")}

   <script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/vis/4.21.0/vis.min.js"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/vis/4.21.0/vis.min.css" rel="stylesheet" type="text/css"/>
        
    </style>
</head>
<body>

<div id="mynetwork"></div>

<aside>
    <table>
      <tbody>
        <tr>
          <td>
            <img src="static/icons/border.png" alt="border states" style="display: block; width: 60px;">
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
            <img src="static/icons/loop.png" alt="self-loop" style="display: block; width: 60px;">
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
            <img src="static/icons/fire.png" alt="hell state" style="display: block; width: 60px;">
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
setTimeout(function () {
    // create an array with nodes
    var nodes = new vis.DataSet([
'''


mid_1 = '''
    ]);
    var border_nodes = [

'''

mid_2 = '''
    ];

    var edges = new vis.DataSet([

'''

mid_3 = '''
    ]);

    var self_loops = [
'''

secondpart_1_1 = '''
    ];

    // create a network
    var container = document.getElementById('mynetwork');

    var options = {
        layout: {improvedLayout: true},
        physics: {
            enabled: true,
            barnesHut: {
                gravitationalConstant: -25000,
                centralGravity: 0.5,
                springConstant: 0.5,
                springLength: 200,
                damping: 0.15
            },
            maxVelocity: 50,
            minVelocity: 7.5,
            solver: 'barnesHut',
            timestep: 0.5,
            stabilization: {
                        enabled: true,
'''

secondpart_1_2 = '''                    },
        },
        nodes: {
            size: 15,
            font: {
                size: 20
            },
            borderWidth: 2,
            borderWidthSelected: 4,
            color:{highlight:{border: '#B20F0F', background: 'red'}}
        },
        edges: {
            width: 4,
            selectionWidth: function (width) {return width*2.5;},
            color:{color:'#2B7CE9', hover:'#2B7CE9', highlight: 'red'}
        },
        interaction: {
        navigationButtons: true,
        keyboard: true,
        hover: true,
        tooltipDelay: 500,
        multiselect: true
        }
    };

    // data filters
    hell_filter = document.getElementById('hell_node')
    loops_filter = document.getElementById('loop_edges')
    border_filter = document.getElementById('border_nodes')

    let noHell = false
    const nodesFilter = (node) => {
        if (noHell) {
            return (node.class != 'hell')
        } else {
            return true
        }
    }

    var nodesView = new vis.DataView(nodes, { filter: nodesFilter })

    // remove hell
    hell_filter.addEventListener('change', (e) => {
        if (hell_filter.checked){
            noHell = false
        } else {
            noHell = true
        }
        nodesView.refresh()
    });

    data = {
            nodes: nodesView,
            edges: edges
        };

    var network = new vis.Network(container, data, options);

    loops_filter.addEventListener('change', (e) => {
        if (loops_filter.checked){
            for (index = 0; index < self_loops.length; index++) {
                edges.add(self_loops[index]);
            }
        } else {
            for (index = 0; index < self_loops.length; index++) {
                edges.remove({id: self_loops[index].id});
            }
        }
    });

    border_filter.addEventListener('change', (e) => {
        if (border_filter.checked){
            for (index = 0; index < border_nodes.length; index++) {
                nodes.update({id: border_nodes[index].id, shape: "box"});
            }
        } else {
            for (index = 0; index < border_nodes.length; index++) {
                nodes.update({id: border_nodes[index].id, shape: "ellipse"});
            }
        }
    });

    var stabil = true;
'''

secondpart_2_1 = '''
    network.on("click", function (params) {
        params.event = "[original event]";
        var tmp = " ";


        for (var i = 1; i <= nodes.length; i++) {
            if (nodes.get(i).id == params.nodes) {
                tmp = nodes.get(i).text;
            };
        };

        if(params.nodes.length === 0 && params.edges.length > 0) {
            for (var i = 1; i <= edges.length; i++) {
                if (edges.get(i).id == params.edges) {
                    tmp = edges.get(i).text;
                };
            };
        };

        document.getElementById('rectangle').innerHTML = '<div style="width:100%;height:100%;text-align:center;border:0px solid #000;">' + tmp + '</div>';
    });

    network.on("stabilized", function (params) {
    if(stabil) {
        network.fit();
        stabil = false;
    };
    });

    network.on("stabilizationProgress", function(params) {
'''

secondpart_2_2 = '''
                var width = 5*(params.iterations/updateInterval);
                var widthFactor = params.iterations/iterations;

                document.getElementById('bar').style.width = width + 'px';
                document.getElementById('text').innerHTML = Math.round(widthFactor*100) + '%';
            });

    network.once("stabilizationIterationsDone", function() {
                document.getElementById('text').innerHTML = '100%';
                document.getElementById('bar').style.width = '496px';
                document.getElementById('loadingBar').style.opacity = 0;
                // really clean the dom element
                setTimeout(function () {document.getElementById('loadingBar').style.display = 'none';}, 0);
    });

    clickedNode = nodes.get(fromNode);
    clickedNode.color = {
            border: 'orange',
            background: 'orange',
            highlight: {
                border: 'orange',
                background: 'orange'
            }
        }
        nodes.update(clickedNode);

    network.on("doubleClick", function (params) {
        params.event = "[original event]";
        network.focus(params.nodes);
    });
}, 5);
</script>

</body>
</html>
'''

stabil_physics = \
'''                        iterations: {},
                        updateInterval: {}
'''

stabil_bar = \
'''                var iterations = {};
                var updateInterval = {};
'''

# for testing
# filename = open('bigger_pMC.json', "r")
# graph = create_HTML_graph(filename)

graph = create_HTML_graph()
%>

${graph}
