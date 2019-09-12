var $ = jQuery = require("jquery");
var cytoscape = require("cytoscape");

var Style = module.exports = function(theme){
    this.theme = theme;
}

Style.prototype.getColor = function(element){
    //Get color for a certain nucleotide as specified by the color
	//picker in the options column of the page.
	var col = "black";
	if($("#acolor").length > 0){
		if (element === "A"){
			col = $("#acolor").spectrum('get').toHexString();
		}
		else if (element === "C"){
			col = $("#ccolor").spectrum('get').toHexString();
		}
		else if (element === "U"){
			col = $("#ucolor").spectrum('get').toHexString();
		}
		else if (element === "G"){
			col = $("#gcolor").spectrum('get').toHexString();
		}
		else if (element === "hbond"){
			col = "#3A9AD9";
		}
		else if(element === "violation") {
			col = "red";
		}
	} else {
		if (element === "A"){
			col = "#64F73F";
		}
		else if (element === "C"){
			col = "#FFB340";
		}
		else if (element === "U"){
			col = "#3C88EE";
		}
		else if (element === "G"){
			col = "#EB413C";
		}
		else if (element === "hbond"){
			col = "#3A9AD9";
		}
		else if(element === "violation") {
			col = "red";
		}
	}
	return col;
}

Style.prototype.getWeight = function(type){
    //Get weight for a certain bond type
    var weight;
    if(type=== "hbond" || type === "violation"){
        weight = 4;
    } else {
        weight = 5;
    }
    return weight;
}

Style.prototype.getCytoscapeStyle = function(){
    var css = cytoscape.stylesheet()
            .selector("node")
            .css({
                "content": "data(label)",
                "text-valign": "center",
                "color": "white",
                "text-outline-width": 2,
                "text-outline-color": "#778899"
            })
            .selector("edge")
            .css({
                "background-color": "white"
            })
            .selector(".chosen")
            .css({
                "background-color": "black",
                "opacity": 0.6
            })
            .selector(".edgehandles-hover")
            .css({
                "background-color": "red"
            })
            .selector(".edgehandles-source")
            .css({
                "border-width": 2,
                "border-color": "red"
            })
            .selector(".edgehandles-target")
            .css({
                "border-width": 2,
                "border-color": "red"
            })
            .selector(".edgehandles-preview, .edgehandles-ghost-edge")
            .css({
                "line-color": "red",
                "target-arrow-color": "red",
                "target-arrow-color": "red"
            })
            .selector(".wcwccis")
            .css({
                "mid-target-arrow-shape": "circle",
                "mid-target-arrow-color": "red"
            })
            .selector(".wcsgcis")
            .css({
                "source-arrow-shape": "circle",
                "source-arrow-color": "red",
                "target-arrow-shape": "triangle",
                "target-arrow-color": "red"
            })
            .selector(".sgwccis")
            .css({
                "target-arrow-shape": "circle",
                "target-arrow-color": "red",
                "source-arrow-shape": "triangle",
                "source-arrow-color": "red"
            })
            .selector(".hgsgcis")
            .css({
                "source-arrow-shape": "square",
                "source-arrow-color": "red",
                "target-arrow-shape": "triangle",
                "target-arrow-color": "red"
            })
            .selector(".sghgcis")
            .css({
                "target-arrow-shape": "square",
                "target-arrow-color": "red",
                "source-arrow-shape": "triangle",
                "source-arrow-color": "red"
            })
            .selector(".wchgcis")
            .css({
                "source-arrow-shape": "circle",
                "source-arrow-color": "red",
                "target-arrow-shape": "square",
                "target-arrow-color": "red"
            })
            .selector(".hgwccis")
            .css({
                "target-arrow-shape": "circle",
                "target-arrow-color": "red",
                "source-arrow-shape": "square",
                "source-arrow-color": "red"
            })
            .selector(".sgsgcis")
            .css({
                "mid-target-arrow-shape": "triangle",
                "mid-target-arrow-color": "red"
            })
            .selector(".wcwctrans")
            .css({
                "mid=target-arrow-shape": "circle",
                "mid-target-arrow-color": "red",
                "mid-target-arrow-fill": "hollow"
            })
            .selector(".wcsgtrans")
            .css({
                "source-arrow-shape": "circle",
                "source-arrow-color": "red",
                "target-arrow-shape": "triangle",
                "target-arrow-color": "red",
                "target-arrow-fill": "hollow",
                "source-arrow-fill": "hollow"
            })
            .selector(".sgwctrans")
            .css({
                "target-arrow-shape": "circle",
                "target-arrow-color": "red",
                "source-arrow-shape": "triangle",
                "source-arrow-color": "red",
                "source-arrow-fill": "hollow",
                "target-arrow-fill": "hollow"
            })
            .selector(".hgsgtrans")
            .css({
                "source-arrow-shape": "square",
                "source-arrow-color": "red",
                "target-arrow-shape": "triangle",
                "target-arrow-color": "red",
                "target-arrow-fill": "hollow",
                "source-arrow-fill": "hollow"
            })
            .selector(".sghgtrans")
            .css({
                "target-arrow-shape": "square",
                "target-arrow-color": "red",
                "source-arrow-shape": "triangle",
                "source-arrow-color": "red",
                "source-arrow-fill": "hollow",
                "target-arrow-fill": "hollow"
            })
            .selector(".wchgtrans")
            .css({
                "source-arrow-shape": "circle",
                "source-arrow-color": "red",
                "target-arrow-shape": "square",
                "target-arrow-color": "red",
                "target-arrow-fill": "hollow",
                "source-arrow-fill": "hollow"
            })
            .selector(".hgwctrans")
            .css({
                "target-arrow-shape": "circle",
                "target-arrow-color": "red",
                "source-arrow-shape": "square",
                "source-arrow-color": "red",
                "source-arrow-fill": "hollow",
                "target-arrow-fill": "hollow"
            })
            .selector(".sgsgtrans")
            .css({
                "mid-target-arrow-shape": "triangle",
                "mid-target-arrow-color": "red",
                "mid-target-arrow-fill": "hollow"
            })
            .selector(".hghgcis")
            .css({
                "mid-target-arrow-shape": "square",
                "mid-target-arrow-color": "red",
            })
            .selector(".hghgtrans")
            .css({
                "mid-target-arrow-shape": "square",
                "mid-target-arrow-color": "red",
                "mid-target-arrow-fill": "hollow"
            });

    return css;
}
