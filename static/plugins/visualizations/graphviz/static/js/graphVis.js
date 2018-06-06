var showNodeLabel;
var showEdgeLabel;
var showOut;
var showIn;
var demoNodes = [];
var demoEdges = [];
var shape;
var allcy;
var cy;
// The key to hold down when brush/box selecting: 16 === shift
var BRUSH_KEY = 16;

$(function() {
    // remove horizontal scrollbar
    $("body").css("overflow-x", "hidden");

    // set up a key that, when held down, allows box selection and turns panning off
    $( document )
        .on( 'keydown', function( ev ){
            if( cy && ev.keyCode === BRUSH_KEY ){
                cy.panningEnabled( false );
                cy.boxSelectionEnabled( true );
            }
        })
        .on( 'keyup', function( ev ){
            if( cy && ev.keyCode === BRUSH_KEY ){
                cy.panningEnabled( true );
                cy.boxSelectionEnabled( false );
            }
        });
});

// shape of the graph
$("select option:selected").each(function() {
    shape = $(this).val();
});

///////// create graph
function createGraph(data) {
    window.graphData = data;

 	allcy = cytoscape({
 		headless: true,
 	});

 	cy = cytoscape({
 		container: document.getElementById('cy'),

 		layout: {
 			name: shape
 			//avoidOverlap: true,
 			//padding: 10
 		},
 		hideEdgesOnViewport: true,
 		hideLabelsOnViewport: true,
 		motionBlur: true,
 		textureOnViewport: true,

        // initially have click and drag pan the viewport
        panningEnabled: true,
        boxSelectionEnabled: false,

 		ready: function() {

 			window.cy = this;
 			cy.nodes().on("click", function(e) {
 				showNodeInfo(e.cyTarget);
 			});
 		},

 		style: cytoscape.stylesheet()
 			.selector('node')
 			.css({
     			'content': showNodeLabel,
     			'text-valign': 'center',
     			'background-color': '#888888',
     			'opacity': 0.8
            })

 			.selector('edge')
 			.css({
     			'curve-style': 'unbundled-bezier',
     			'target-arrow-shape': 'triangle',
     			'width': 2,
     			'line-color': '#ddd',
     			'target-arrow-color': '#ddd',
     			'content': showEdgeLabel
            })

 			.selector(':selected')
 			.css({
     			'background-color': '#FE2E64',
     			'line-color': '#FE2E64',
     			'target-arrow-color': '#FE2E64',
     			'source-arrow-color': '#FE2E64',
     			'opacity': 1
     		})

            .selector('core')
            .css({
                'outside-texture-bg-color': 'white'
     		})
 	});
    window.cy = cy;
 	allcy.load(data);

    // if graph contains more than 50 nodes load only root nodes
 	if (allcy.nodes().length > 50 && allcy.nodes().roots().length !== 0 ) {
		var toAdd = allcy.nodes().roots().closedNeighborhood();
		allcy.nodes().roots().addClass("roots");

		showNodesToExpand(toAdd);
 		cy.add(toAdd);
		cy.load(cy.elements('*').jsons());

 		cy.style()
 			.selector('.toBeExpaned')
 			.css({
     			'width': 50,
     			'height': 50
     		})
 			.update();

 	} else {
        cy.add(data);
        cy.load(cy.elements('*').jsons());
 	}
 	checkBoxes();

} // END create graph


//// parse function for matrix data
function parseTextMatrix(data) {
    var nodes = [],
        edges = [];

    data.split( '\n' ).forEach( function( line ){
        var columns = line.split( /,?\s+/ ),
            sourceId = columns[0]; // split by comma or space

        nodes.push({
            data: { id: sourceId }
        });

        for( var i = 1; i < columns.length; i++ ){
            edges.push({
                data: {
                    source  : sourceId,
                    target  : columns[i]
                }
            });
        }
    });

	createGraph({
        nodes: nodes,
        edges: edges
    });
}

///// parsing function for json: for link/egde and "" issues
function parseJson( data ) {

    if( data.hasOwnProperty( 'links' ) ){
        data.edges = data.links;
        delete data.links;
    }
	data.nodes = data.nodes.map( function _processNode( node ){
        return {
            data : $.extend( {}, node.data, {
                id : node.id + ''
            })
        };
    });
    data.edges = data.edges.map( function _processEdge( edge ){
        return {
            data : $.extend( {}, edge.data, {
                id      : edge.id || undefined,
                source  : data.nodes[ edge.source ].data.id,
                target  : data.nodes[ edge.target ].data.id
            })
        };
    });
	createGraph( data );
}