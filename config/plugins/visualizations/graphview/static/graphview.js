function get_firstChild(n) {
	y=n.firstChild;
	while (y && y.nodeType!=1) {
		y=y.nextSibling;
 	}
	return y;
}

function get_nextSibling(n) {
	y=n.nextSibling;
	while (y) {
		if (y.nodeType==1) {
			return y;
		}
		y=y.nextSibling;
	}
	return y;
}

function parse_xgmml_attr(elm) {
	out = {};
	var c = get_firstChild(elm);
	while (c) {
		if (c.nodeName == "att") {
			if (c.attributes['type'].value == "string") {
				out[c.attributes['name'].value] = c.attributes['value'].value;
			}
		}
		c = get_nextSibling(c);
	}
	return out
}

function parse_xgmml(root, add_node, add_edge) {
	graph=root.getElementsByTagName("graph")[0];
	elm = get_firstChild(graph);
	while (elm) {
		if (elm.nodeName == "node") {
			var attr = parse_xgmml_attr(elm);
			add_node( elm.attributes['id'].value, elm.attributes['label'].value, attr );
		}
		if (elm.nodeName == "edge") {
			var attr = parse_xgmml_attr(elm);
			add_edge( elm.attributes['source'].value, elm.attributes['target'].value, attr );
		}
		
		elm = get_nextSibling(elm);
	}
}

function parse_sif(data, add_node, add_edge) {
	var lines = data.split("\n")
	for (var i in lines) {
		var tmp = lines[i].split("\t");
		if (tmp.length == 3) {
			add_edge(tmp[0], tmp[2], {type:tmp[1]});
		}
	}

}

jQuery.fn.graphViewer = function(config) {

	var svg, colors;
	var nodes = [],
	  	links = [];

	var height = config.height;
	var width = config.width;


	colors = d3.scale.category10();

	this.each(function() {
		svg = d3.select(this)
			.append('svg')
			.attr('width', width)
			.attr('height', height);
		}
	);

	var tooltip_div = d3.select("#tooltip").attr("class", "tooltip").style("opacity", 0);;

	this.add_node = function(node_id, node_label, attr) {	
		nodes.push( {id: node_id, label:node_label, attr:attr} );
	}

	this.add_edge = function(src_id, dst_id, attr) {
		var src, target;
		for (var i in nodes) {
			if (nodes[i].id == src_id) {
				src = nodes[i];
			}
			if (nodes[i].id == dst_id) {
				target = nodes[i];
			}
		}
		if (typeof src==="undefined") {
			i = nodes.length
			nodes.push( {id:src_id, label:src_id, attr:{}} )
			src = nodes[i]
		}
		if (typeof target==="undefined") {
			i = nodes.length
			nodes.push( {id:dst_id, label:dst_id, attr:{}} )
			target = nodes[i]
		}
		if (src && target) {
			links.push( {source: src, target: target, left: false, right: true } );
		}
	}

	this.render = function() {
		var path = svg.append('svg:g').selectAll('path'),
	    circle = svg.append('svg:g').selectAll('g');


		circle = circle.data(nodes, function(d) { return d.id; });
		var g = circle.enter().append('svg:g');

		circle.on('mouseover', function(d) {
			tooltip_div.transition()        
            .duration(200)      
            .style("opacity", .9);
			tooltip_div.html( "<div>" + d.label + "</div><div>" + d.attr.type + "</div>" ).style("left", (d3.event.pageX + 40) + "px")
            .style("top", (d3.event.pageY - 35) + "px");   
		})
		.on("mouseout", function(d) {       
        	tooltip_div.transition()        
            .duration(500)      
            .style("opacity", 0);
        });

		path = path.data(links);


		function tick() {
			path.attr('d', function(d) {
    			return 'M' +  d.source.x + ',' +  d.source.y + 'L' + d.target.x + ',' + d.target.y;
    		});
			circle.attr('transform', function(d) {
				return 'translate(' + d.x + ',' + d.y + ')';
			});
		}


		g.append('svg:circle')
			.attr('class', 'node')
			.attr('r', 8)
			.style('stroke', 'black')
			.attr('fill', function(d) { 
				return colors(d['attr']['type']) 
			});

		path.enter().append('svg:path')
			.attr('class', 'link')


	  	// init D3 force layout
		var force = d3.layout.force()
		    .nodes(nodes)
		    .links(links)
		    .size([width, height])
		    .linkDistance(25)
		    .charge(-50)
		    .on('tick', tick)
		circle.call(force.drag)
		force.start()

	}

	return this

}

