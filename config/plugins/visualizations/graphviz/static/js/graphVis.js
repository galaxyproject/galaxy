 var showNodeLabel;
 var showEdgeLabel;
 var showOut;
 var showIn;
 var demoNodes = [];
 var demoEdges = [];
 var shape;
 var allcy;
 var cy;



 $(function() { // on dom ready


 	$("body").css("overflow-x", "hidden"); //// remove horizontal scrollbar


 }); // END on dom ready

// shape of the graph
 $("select option:selected").each(function() {
 	shape = $(this).val();

 });
 
 ///////// create graph
 function createGraph(data) {

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
 			'width': 4,
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
 	allcy.load(data);

// if graph contains more than 50 nodes load only root nodes 
 	if (allcy.nodes().length > 50 && allcy.nodes().roots().length != 0 ) {
			
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
 	cy.boxSelectionEnabled(true);


 	checkBoxes();


 } // END create graph	


 //// parse function for matrix data
 function parseAndCreate(demoNodes, demoEdges) {
 	var data = {
 		nodes: demoNodes,
 		edges: demoEdges
 	};
 	createGraph(data);
 }


 ///// parsing function for json: for link/egde and "" issues
 function parseJson(dataToParse) {

 	if (dataToParse.links == null) {

 		var links = dataToParse.edges;
 	} else {
 		var links = dataToParse.links;
 		dataToParse.edges = links;

 	}

 	var nodes = dataToParse.nodes;

 	for (var i = 0; i < nodes.length; i++) {

 		dataToParse.nodes[i].data = nodes[i];
 		dataToParse.nodes[i].data.id = '"' + nodes[i].id + '"';
 	}


 	for (var i = 0; i < links.length; i++) {

 		dataToParse.edges[i].data = links[i];
 		dataToParse.edges[i].data.source = '"' + links[i].source + '"';
 		dataToParse.edges[i].data.target = '"' + links[i].target + '"';
 	}

 	createGraph(dataToParse);
 }