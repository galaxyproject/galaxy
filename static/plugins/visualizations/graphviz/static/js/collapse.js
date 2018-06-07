var collapseOrder = 0;   // the order of collapsed nodes
var collapseNodeCount = 0;  // the number of collapsed nodes 
var num = 0;

function colNode() { 	//// collapse node


	var selectedNode = cy.nodes(':selected');
	var connectedEdges = selectedNode.connectedEdges(function() {
		return !this.target().anySame(selectedNode);
	});
	var connectedNodes = connectedEdges.targets();

	collapseNodeCount = connectedNodes.length;
	num = selectedNode.data('colNum', collapseNodeCount);
	connectedNodes.addClass('collapsedNode' + collapseOrder);
	connectedEdges.addClass('collapsedNode' + collapseOrder);
	selectedNode.addClass('superNode');

	addCollapsedEdges(selectedNode, collapseOrder);    

// hide collapsed nodes
	cy.style()
		.selector('.collapsedNode' + collapseOrder)
		.css({
		'visibility': 'hidden'
	})
		.update();
// change the size of superNode
	cy.style()
		.selector('.superNode')
		.css({
		'opacity': 0.8,
		'width': 50,
		'height': 50
	})
		.update();

	cy.fit();


	collapseOrder = collapseOrder + 1;

	//}
	$('.btn.colNode').prop('disabled', true);
	console.log("shape = " + shape);

}

/// uncollapse(expand) superNode

function unColNode() { 

	var selectedNode = cy.nodes(':selected');
	var connectedEdges = selectedNode.connectedEdges(function() {
		return !this.target().anySame(selectedNode);
	});
	var connectedNodes = connectedEdges.targets();
	cy.style()
		.selector('.superNode')
		.update();

	selectedNode.removeClass('superNode');

	for (var i = collapseOrder; i >= 0; i--) {

		if (connectedNodes.hasClass('collapsedNode' + i) || connectedEdges.hasClass('collapsedNode' + i)) {

			connectedNodes.removeClass('collapsedNode' + i);
			connectedEdges.removeClass('collapsedNode' + i);
			removeCollapsedEdges(selectedNode, i);

			cy.style()
				.update(); // remove invisibility
			cy.fit();
		}

	}

	collapseOrder--;
	
	$('.btn.colNode').prop('disabled', true);  // disable collapse button

}

/// creating edges from superNode to childNodes of the collapsed Nodes
function addCollapsedEdges(selectedNode, collapseOrder) {

	var connectedEdges = selectedNode.connectedEdges(function() {
		return !this.target().anySame(selectedNode);
	});

	var connectedNodes = connectedEdges.targets();
	var newTargetEdges = connectedNodes.connectedEdges(function() {
		return !this.target().anySame(connectedNodes);
	});
	var newSourceEdges = connectedNodes.connectedEdges(function() {
		return !this.source().anySame(connectedNodes);
	});

	var newTargetNodes = newTargetEdges.targets();
	var newSourceNodes = newSourceEdges.sources();


	newTargetNodes.each(function(i, ele) {

		if (ele.edgesTo(selectedNode).sources().data('id') == selectedNode.data('id') || ele.data('id') == selectedNode.data('id')) { // preventing duplicate edges 

			ele = ele + 1;
		} else {


			cy.add({
				group: "edges",
				data: {
					source: selectedNode.data('id'),
					target: ele.data('id')
				}
			})
				.addClass('virtualEdges' + collapseOrder)
		}
	});




	newSourceNodes.each(function(i, ele) {

		if (ele.edgesTo(selectedNode).targets().data('id') == selectedNode.data('id') || ele.data('id') == selectedNode.data('id')) {

			ele = ele + 1;
		} else {

			cy.add({
				group: "edges",
				data: {
					source: ele.data('id'),
					target: selectedNode.data('id')
				}
			})
				.addClass('virtualEdges' + collapseOrder)
		}
	});



}

// removes the edges created by addCollapsedEdges
function removeCollapsedEdges(selectedNode, collapseOrder) {

	selectedNode.connectedEdges().each(function(i, ele) {

		if (ele.hasClass('virtualEdges' + collapseOrder)) {

			cy.remove(ele);
		}
	});

}

//reseting all superNodes
function resetCollapse() {

	for (var i = collapseOrder; i >= 0; i--) {

		cy.style()
			.selector('.collapsedNode' + i)
			.css({
			'opacity': 0.8,
			'background-color': '#888888',
			'line-color': '#ddd',
			'target-arrow-color': '#ddd'
		})
			.update();

		cy.style()
			.selector('.superNode')
			.css({
			'opacity': 0.8,
			'background-color': '#888888', //
			'border-width': 0
		})
			.update();

		cy.remove('.virtualEdges' + i);

		cy.nodes().removeClass('superNode');
		cy.nodes().removeClass('collapsedNode' + i);
		cy.edges().removeClass('collapsedNode' + i);
		cy.edges().removeClass('virtualEdges' + i);

	}
}



// counts the number of collapsed nodes for the given superNode
function countCollapse(nd) {

	if (nd.hasClass('superNode')) {
		Tip('contains ' + nd.data().colNum + ' node(s)', PADDING, 10);
	} else if (nd.hasClass('toBeExpaned')) {

		var eles = allcy.nodes();
		var selectedNodeId = nd.id();
		selectedNodeId = selectedNodeId.replace(/[^0-9\.]+/g, "");

		var nodeCount = eles[selectedNodeId].outdegree();
		Tip('contains ' + nodeCount + ' node(s)', PADDING, 10);

	} else {
		Tip('contains 0 node(s)', PADDING, 10);
	}
}
