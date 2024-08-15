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
            iterations: def_iterations,
            updateInterval: def_updateInterval
        },
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

var container = document.getElementById('mynetwork');

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

window.onresize = function() {
    var network = new vis.Network(container, data, options);

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

    network.once("stabilizationIterationsDone", function() {
        document.getElementById('text').innerHTML = '100%';
        document.getElementById('bar').style.width = '496px';
        document.getElementById('loadingBar').style.opacity = 0;
        setTimeout(function () {document.getElementById('loadingBar').style.display = 'none';}, 0);
    });

    network.on("doubleClick", function (params) {
        params.event = "[original event]";
        network.focus(params.nodes);
    });

    network.on("stabilizationProgress", function(params) {
        var iterations = def_iterations;
        var updateInterval = def_updateInterval;
        var width = 5*(params.iterations/updateInterval);
        var widthFactor = params.iterations/iterations;

        document.getElementById('bar').style.width = width + 'px';
        document.getElementById('text').innerHTML = Math.round(widthFactor*100) + '%';
    });
};
