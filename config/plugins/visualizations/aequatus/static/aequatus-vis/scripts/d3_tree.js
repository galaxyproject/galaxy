/**
 * Created with IntelliJ IDEA.
 * User: thankia
 * Date: 30/07/2014
 * Time: 13:16
 * To change this template use File | Settings | File Templates.
 */


/**
 * Setup D3 to draw tree
 * @param json_tree gene tree in JSON format
 * @param div HTML div reference to draw tree
 * @param event event to be initialise for onclick on gene
 */

var ranked = false;
var last = 0;
var nodes;
var root;
var cluster;
var svg;
var i = 0,
    duration = 750;
var diagonal = d3.svg.line().interpolate('step-before')
    .x(function (d) {
        return d.x;
    })
    .y(function (d) {
        return d.y;
    });
var count = 0;
var gene_width, margin, width, height;



var maxHeight = 1000;
var event;

function drawTree(json_tree, div, event) {
    this.event = event;
    gene_width = jQuery("body").width() * 0.8
    margin = {top: 0, right: 0, bottom: 0, left: 0},
    width = jQuery("body").width() * 0.2,
    height = 800 - margin.top - margin.bottom;

    cluster = d3.layout.cluster()
        .size([height, width - 160]);


    svg = d3.select(div).append("svg")
        .attr("width", width + margin.right + margin.left)
        .attr("height", height + margin.top + margin.bottom)
        .style("overflow", "visible")
        .style("left", "100px")
        .style("position", "relative")
        .append("g")
        .attr("transform", "translate(" + margin.left + "," + margin.top + ")");


    var genome_list_all = []


    for (var key in syntenic_data.member) {
        genome_list_all.push(syntenic_data.member[key].species)
    }
    var genome_list = [];
    jQuery.each(genome_list_all, function (i, el) {
        if (jQuery.inArray(el, genome_list) === -1) genome_list.push(el);
    });

    d3.select(filter_div).selectAll("input")
        .data(genome_list)
        .enter()
        .append('label')
        .attr("class", "filter")
        .style("font-size", "12px")
        .style("text-align", "left")
        .style("display", "table-row")
        .attr('for', function (d, i) {
            return 'checkbox' + d;
        })
        .text(function (d) {
            return d;
        })
        .append("input")
        .attr("checked", true)
        .attr("type", "checkbox")
        .attr("id", function (d, i) {
            return 'checkbox' + d;
        })
        .on("click", function (d) {
            filtercheck(d)
            update(root, member_id);
        });

    jQuery(slider_filter_div).html("<table width=90%>" +
        "<tr>" +
        "<td><b><center>Filter Tree by distance</center></b></td>" +
        "</tr>" +
        "<tr>" +
        "<td><div id='slider_div'></div>" +
        "<td><input type='number' min='0' id='slider_percentage' style='border: 1px solid lightgray; font-weight: bold; margin-left: 10px; padding: 2px; width: 50px;'>" +
        "</tr>" +
        "</table>")

    jQuery("#slider_div").slider({
        value: 3,
        min: 1,
        max: 10,
        step: 1,
        stop: function (event, ui) {
            if (ui.value < last) filterRank(ui.value)//$("#amount").val("this is increasing");
            if (ui.value > last) filterRankUP(ui.value)//$("#amount").val("this is decreasing");
            last = ui.value;
            jQuery("#slider_percentage").val(ui.value);
        }
    });

    last = jQuery("#slider_div").slider("value")

    jQuery("#slider_div").slider().bind({
        stop: function (event, ui) {
            var value = jQuery("#slider_div").slider("value")
            if (value < last) filterRank(value)//$("#amount").val("this is increasing");
            if (value > last) filterRankUP(value)//$("#amount").val("this is decreasing");
            last = value;
            jQuery("#slider_percentage").val(value);
        }
    })

    jQuery("#slider_percentage").val(jQuery("#slider_div").slider("value"));

    jQuery("#slider_percentage").on("change", function () {
        var val = jQuery("#slider_percentage").val()
        if (val < last) filterRank(val)//$("#amount").val("this is increasing");
        if (val > last) filterRankUP(val)//$("#amount").val("this is decreasing");
        last = val;

        jQuery("#slider_div").slider({
            value: val
        })
    })

    d3.json(json_tree, function () {

        root = json_tree;

        root.x0 = height / 2;
        root.y0 = 0;
        root.children.forEach(function (d) {
            recursiveChildren(d)
        });
        nodes = cluster.nodes(root);
        rank();


    });

    d3.select(self.frameElement).style("height", "800px");


    function recursiveChildren(d) {
        if (d.children && d.children.size() == 1) {
            var new_children = pack(d)
            d.children = new_children.child;
            d.close = true
            d.type = new_children.type;
        }
        if (d.children) {
            d.children.forEach(function (e) {
                recursiveChildren(e)
            })
        }
    }

}

/**
 * selects tree nodes for species
 * @param de species name
 */
function filtercheck(de) {
    var selected = de;
    var display = jQuery("#checkbox" + de).is(":checked")

    root.children.forEach(function (d, i) {
        recursiveChildren(d)

    });

    function recursiveChildren(d) {
        if (!d.children || d._children) {
            if (d.sequence && d.id.accession && display == false) {
                if (d.sequence.id[0].accession == protein_member_id) {
                } else {
                    if (d._children) {
                        var children = d._children.size()
                        while (children--) {
                        }
                    }

                    if (syntenic_data.member[d.id.accession] && selected == syntenic_data.member[d.id.accession].species) {
                        if (display == true) {


                        } else {
                            if (d.close && d.close == true) {

                            } else {
                                if (!d.parent._children) {
                                    d.parent._children = [];
                                }

                                if (d.parent.children.size() > 1) {
                                    d.parent._children.push(d)
                                    d.parent.children.splice(d.parent.children.indexOf(d), 1)
                                    // update(d, member_id);

                                } else {
                                    var cont = true;
                                    var child = d.parent
                                    while (cont) {
                                        if (!child._children) {
                                            child._children = [];
                                        }
                                        child._children.push(child.children[0])

                                        child.children.splice(0, 1)
                                        if (child.parent.children.size() > 1) {
                                            cont = false;
                                        }

                                        child = child.parent;

                                    }
                                }
                            }
                        }
                    }
                }
            }
            else {

                if (d._children && d._children.size() > 0) {
                    var newObject = d;//jQuery.extend(true, {}, d);

                    var cont = true;
                    if (d.sequence) {
                    }
                    while (cont) {
                        if (d._children && d._children.size() > 0) {
                            var children = d._children.size()
                            while (children--) {
                                if (!d.children) {
                                    d.children = []
                                }
                                if (d._children[children].sequence && d._children[children].id.accession == member_id && selected == syntenic_data.member[syntenic_data.ref].species) {
                                    d.children.push(d._children[children])
                                    d._children.splice(children, 1)
                                    cont = false;
                                    // update(newObject, member_id);
                                } else if (d._children[children].sequence && d._children[children].id.accession && selected == syntenic_data.member[d._children[children].id.accession].species) {
                                    d.children.push(d._children[children])
                                    d._children.splice(children, 1)
                                    cont = false;
                                    // update(d, member_id);
                                } else if (d._children[children]._children && d._children[children]._children.size() > 0) {
                                    d = d._children[children]
                                } else {
                                    cont = false;
                                }
                            }
                        }
                    }
                }
            }
        }
        if (d.children) {
            d.children.forEach(function (e) {
                recursiveChildren(e)
            })
        }
    }
}


function filterRank(rank) {
    svg.selectAll(".node")
        .filter(function (d) {
            if (d.rank && d.rank > rank) {
                var newObject = d;
                newObject.children.forEach(function (e) {
                    if (e.rank && e.rank <= rank) {

                    } else if (e.rank && e.rank > rank) {
                        recursiveCheck(e)
                    } else {
                        closeNode(d, e)
                    }
                })
            }


            function recursiveCheck(node) {
                node.children.forEach(function (e) {
                    if (e.rank && e.rank <= rank) {
                    } else if (e.rank && e.rank > rank) {
                        recursiveCheck(e)
                    } else {
                        closeNode(node, e)
                    }
                })
            }

            function closeNode(node, childNode) {
                var temp_children = childNode
                if (temp_children) {
                    if (!node._children)
                        node._children = []
                    node._children.push(temp_children)
                    var i = node.children.indexOf(childNode);
                    node.children.splice(i, 1)
                    update(node, member_id);
                }
            }
        });
}

function filterRankUP(rank) {
    svg.selectAll(".node")
        .filter(function (d) {
            if (d.rank && d.rank <= rank) {
                var newObject = d;
                if (newObject._children && newObject._children.size() > 0) {
                    newObject._children.forEach(function (e, i) {
                        if (e.rank && e.rank <= rank) {
                        } else if (e.rank && e.rank <= rank) {
                            recusrsiveCheckOpen(e)
                        } else {
                            openNode(d, e)
                        }
                    })
                }
            }

            function recusrsiveCheckOpen(node) {
                node.children.forEach(function (e) {
                    if (e.rank && e.rank <= rank) {
                    } else if (e.rank && e.rank <= rank) {
                        recusrsiveCheckOpen(e)
                    } else {
                        openNode(node, e)
                    }
                })
            }


            function openNode(node, childNode) {
                var temp_children = childNode
                if (temp_children) {
                    if (!node.children)
                        node.children = []

                    node.children.push(temp_children)
                    var i = node._children.indexOf(childNode);
                    node._children.splice(i, 1)
                    update(node, member_id);
                }
            }
        });

}

/**
 * changes genes view to normal view with full length introns
 */
function changeToNormal() {
    jQuery(".style1").show()
    jQuery(".style2").hide()

}

/**
 * changes genes view to exon focused view with fixed length introns
 */
function changeToExon() {
    jQuery(".style2").show()
    jQuery(".style1").hide()
}

/**
 * changes genes label to stable ids
 */
function changeToStable() {
    jQuery(".genelabel").hide();
    jQuery(".protein_id").hide();
    jQuery(".stable").show();
}

/**
 * changes genes label to gene names
 */
function changeToGeneInfo() {
    jQuery(".genelabel").hide();
    jQuery(".protein_id").hide();
    jQuery(".geneinfo").show();
}

/**
 * changes genes label to protein ids
 */
function changeToProteinId() {
    jQuery(".genelabel").hide();
    jQuery(".geneinfo").hide();
    jQuery(".protein_id").show();
}

/**
 * Toggle children on click.
 * @param d clicked node
 */
function click(d) {

    if (d.rank) {
        var curr_rank = jQuery("#slider_percentage").val()

        if (curr_rank > d.rank) {
            jQuery("#slider_div").slider({
                value: d.rank
            })
            jQuery("#slider_percentage").val(d.rank)
            filterRank(d.rank)
        } else if (curr_rank < d.rank) {
            jQuery("#slider_div").slider({
                value: d.rank
            })
            jQuery("#slider_percentage").val(d.rank)
            filterRankUP(d.rank)
        } else {
        }
    } else if (d.children && d.children != null) {
        if (d.children.size() == 1) {
            d._children = d.children;
            var new_children = pack(d)
            d.children = new_children.child;
            d.close = true
            d.type = new_children.type;
        } else {
            d._children = d.children;
            d.children = null;
        }
    } else {
        d.children = d._children;
        d._children = null;
    }

    update(d, member_id);

}

function updateWindow(count) {
    var y = count * 40;

    svg.attr("height", y);
    cluster = d3.layout.cluster()
        .size([y, width - 160]);
}

function pack(d) {
    var cont = true;
    var child = d;
    var new_children = {}
    new_children.type = []
    var children = null;

    while (cont) {
        if (child.children && child.children.size() == 1 && !child.children[0].sequence) {
            child = (child.children[0])
            if (child.type) {
                new_children.type = new_children.type.concat(child.type)
            } else {
                new_children.type.push(child.node_type)
            }
        } else {
            if (child.children) {
                children = child.children
            }
            else {
                children = child.parent.children
            }
            cont = false;
            break;
        }
    }

    new_children.child = children;
    return new_children;
}
function update(source, ref_member) {
    // Compute the new tree layout.
    // Normalize for fixed-depth.
    nodes = cluster.nodes(root)
    count = 0

    cluster.nodes(root).forEach(function (d) {
        if (d.children == null)
            count++;
    });

    updateWindow(count)


    nodes = cluster.nodes(root)

    var links = cluster.links(nodes);

    var node = svg.selectAll("g.node")
        .data(nodes, function (d) {
            return d.ID || (d.ID = ++i);
        });

    // Enter any new nodes at the parent's previous position.
    var nodeEnter = node.enter().append("g")
        .attr("id", function (d, i) {

            return "node" + d.node_id;
        })
        .attr("class", "node")
        .attr("transform", function (d) {
            if (source.x0 > maxHeight) {
                maxHeight = source.x0
            }
            return "translate(" + d.y + "," + d.x + ")";
        })
        .attr("species", function (d) {
            if (d.sequence) {
                if (d.sequence.id[0].accession == protein_member_id) {
                    return syntenic_data.member[syntenic_data.ref].species;
                } else {
                    return syntenic_data.member[d.id.accession].species;
                }
            }
            else {
                return "";
            }
        })
        .attr("rank", function (d) {
            if (d.rank) {
                return d.rank;
            }

        })
        .on("click", function (d) {
            if (d.sequence) {
                event(d.id.accession, d.sequence.id[0].accession)
            } else {
                if (d.children && d.children != null) {
                    if (d.children.size() > 0) {
                        click(d)
                    }
                } else {
                    if (d._children.size() > 0) {
                        click(d)
                    }
                }
            }
        })

    nodeEnter.append("circle")
        .attr("id", function (d, i) {
            if (d.sequence)// && d.children != null) {
            {
                return "circle" + d.sequence.id[0].accession;
            } else {
                return "circle" + d.node_id;

            }
        })
        .attr("r", function (d) {
            if (d.sequence && d.sequence.id[0].accession == protein_member_id)// && d.children != null) {
            {
                return 6;
            }
            else {
                return 4;
            }
        })
        .style("fill", function (d) {
            if (d.sequence) {
                return "white";
            }
            else if (d.close && d.close == true) {
                return "white";
            } else if (d.events) {
                if (d.events.type == "duplication") {
                    return 'red';
                } else if (d.events.type == "dubious") {
                    return "cyan";
                } else if (d.events.type == "speciation") {
                    return 'blue';
                } else if (d.events.type == "gene_split") {
                    return 'pink';
                } else {
                    return "white";
                }
            }
        })
        .style("stroke-width", function (d) {
            if ((d.sequence && d.sequence.id[0].accession == protein_member_id) || (d.close && d.close == true)) {
                return "2px";
            } else {
                return "1px";
            }
        })
        .style("stroke", function (d) {
            if ((d.sequence && d.id.accession == protein_member_id)) {
                return "black";
            }
        });

    // Transition nodes to their new position.
    var nodeUpdate = node.transition()
        .attr("id", function (d, i) {

            return "node" + d.node_id;
        })
        .duration(duration)
        .attr("transform", function (d) {
            if (d.x > maxHeight) {
                maxHeight = d.x
            }
            return "translate(" + d.y + "," + d.x + ")";
        });

    nodeUpdate.select("circle")
        .attr("id", function (d, i) {
            if (d.sequence)// && d.children != null) {
            {
                return "circle" + d.sequence.id[0].accession;
            } else {
                return "circle" + d.node_id;

            }
        })
        .attr("r", function (d) {
            if (d.sequence && d.sequence.id[0].accession == protein_member_id)// && d.children != null) {
            {
                return 6;
            }
            else {
                return 4;
            }
        })
        .style("fill", function (d) {
            if (d.sequence) {
                return "white";
            }
            else if (d.close && d.close == true) {
                return "white";
            } else if (d.events) {
                if (d.events.type == "duplication") {
                    return 'red';
                } else if (d.events.type == "dubious") {
                    return "cyan";
                } else if (d.events.type == "speciation") {
                    return 'blue';
                } else if (d.events.type == "gene_split") {
                    return 'pink';
                } else {
                    return "white";
                }
            }
        })
        .style("stroke-width", function (d) {
            if ((d.sequence && d.sequence.id[0].accession == protein_member_id) || (d.close && d.close == true)) {
                return "2px";
            } else {
                return "1px";
            }
        })
        .style("stroke", function (d) {
            if ((d.sequence && d.sequence.id[0].accession == protein_member_id)) {
                return "black";
            }
        });

    // Transition exiting nodes to the parent's new position.
    var nodeExit = node.exit().transition()
        .duration(duration)
        .attr("transform", function (d) {
            return "translate(" + source.y + "," + source.x + ")";
        })
        .remove();

    nodeExit.select("circle")
        .attr("r", 1e-6);

    nodeExit.select("text")
        .style("fill-opacity", 1e-6);


    nodeEnter.filter(function (d) {
        if (d.sequence) {
            return true;
        } else {
            return false;
        }
    }).append("foreignObject")
        .attr("class", "node_gene_holder")
        .attr('width', width)
        .attr('height', '40px')
        .attr('x', 20)
        .attr('y', -5)
        .style("fill", "red")

        .append('xhtml:div')
        .style("width", gene_width)
        .style("height", "0px")
        .style("z-index", "999")
        .style("position", "fixed")
        .style("left", "10px")
        .style("top", "0px")
        .html(function (d) {
            if (d.sequence) {
                return "<div id = 'id" + d.sequence.id[0].accession + "' style='position:relative;  cursor:pointer; height: 14px;  LEFT: 0px; width :" + gene_width + "px;'></div>";//jQuery("#gene_widget #id" + d.seq_member_id).html();
            }
        });

    nodeEnter.filter(function (d) {
        if (d.sequence && d.sequence.id[0].accession == protein_member_id) {
            jQuery("#id" + d.sequence.id[0].accession).svg()
            dispGenesForMember_id("#id" + d.sequence.id[0].accession, syntenic_data.cigar[d.sequence.id[0].accession], d.id.accession, d.sequence.id[0].accession)
            dispGenesExonForMember_id("#id" + d.sequence.id[0].accession, syntenic_data.cigar[d.sequence.id[0].accession], d.id.accession, d.sequence.id[0].accession)
        } else if (d.sequence && syntenic_data.member[d.id.accession]) {
            jQuery("#id" + d.sequence.id[0].accession).svg()

            var ref_gicar = syntenic_data.cigar[protein_member_id]
            dispGenesForMember_id("#id" + d.sequence.id[0].accession, syntenic_data.cigar[d.sequence.id[0].accession], d.id.accession, d.sequence.id[0].accession, ref_gicar)
            dispGenesExonForMember_id("#id" + d.sequence.id[0].accession, syntenic_data.cigar[d.sequence.id[0].accession], d.id.accession, d.sequence.id[0].accession, ref_gicar)
        }


        checkVisuals();
    });

    nodeUpdate.select("foreignObject")
        .attr('width', function (d) {
            return jQuery("body").width() * 0.8;
        })
        .attr("rank", function (d) {
            if (d.rank) {
                return d.rank;
            } else {
                return null;
            }

        })
        .attr('height', '40px')
        .attr('x', 10)
        .attr('y', -5);
    var width = 1;
    var max_width = jQuery('#slider_div').slider("option", "max");

    // Update the links…
    var link = svg.selectAll("path.link")
        .data(links, function (d, i) {
            return d.target.ID;
        });

    // Enter any new links at the parent's previous position.
    link.enter().insert("path", "g")
        .attr("class", "link")
        .attr('id', function (d) {
            return "link" + d.target.node_id
        })
        .attr("d", function (d) {
            return diagonal([{
                y: d.source.x,
                x: d.source.y
            }, {
                y: d.target.x,
                x: d.target.y
            }]);
        })
        .attr('stroke-width', function (d) {
            if (d.source.rank) {
                width = (max_width - d.source.rank) + 1
            }
            else {
                width = jQuery("#link" + d.source.node_id).attr('stroke-width')
            }
            return width
        });
    // Transition links to their new position.
    link.transition()
        .duration(duration)
        .attr('id', function (d) {
            return "link" + d.target.node_id
        })
        .attr("d", function (d) {
            return diagonal([{
                y: d.source.x,
                x: d.source.y
            }, {
                y: d.target.x,
                x: d.target.y
            }]);
        })
        .attr('stroke-width', function (d) {
            if (d.source.rank) {
                width = (max_width - d.source.rank) + 1
            }
            else {
                width = jQuery("#link" + d.source.node_id).attr('stroke-width')
            }
            return width
        });

    // Transition exiting nodes to the parent's new position.
    link.exit().transition()
        .duration(duration)
        .attr("d", function (d) {
            return diagonal([{
                y: d.source.x,
                x: d.source.y
            }, {
                y: d.target.x,
                x: d.target.y
            }]);
        })
        .remove();

    // Stash the old positions for transition.
    nodes.forEach(function (d, i) {
        d.x0 = d.x;
        d.y0 = d.y;
    });

    if (maxHeight > height) {
        var body = d3.select("body");
        var temp_svg = body.select("svg")
        temp_svg.attr("height", parseInt(maxHeight) + 100 + "px")

    }
}
function rank() {
    var rank = 1;
    nodes.reverse()
    if (ranked == false) {
        nodes.forEach(function (d, i) {
            if (d.rank) {
                delete d.rank;
            }
        })
        nodes.forEach(function (d, i) {
            if (d.sequence && d.sequence.id[0].accession == protein_member_id) {
                d.parent['rank'] = rank;
            }
            if (d.parent && d.rank > 0) {
                rank++;
                d.parent['rank'] = rank;
            }


            if (d.rank > jQuery("#slider_percentage").val()) {
                if (!d._children)
                    d._children = []

                d.children.forEach(function (e, i) {

                    if (!e.rank) {
                        d._children.push(e)
                        d.children.splice(i, 1)
                    }
                })
            }
            if (d.rank <= jQuery("#slider_percentage").val() && d._children) {
                d._children.forEach(function (e, i) {
                    d.children.push(e)
                    d._children.splice(i, 1)
                })
            }
        });

        jQuery('#slider_div').slider("option", "max", rank);
        ranked = true;
    }
    else {
        nodes.forEach(function (d, i) {
            if (d.rank >= rank) {
                rank = d.rank;
            }
        })
        jQuery('#slider_div').slider("option", "max", rank);
    }
    jQuery(filter_div).children("label").each(function () {
        filtercheck(jQuery(this).text())
    })

    update(root, member_id);
}

