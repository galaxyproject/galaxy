var Backbone = require("backbone");
var parseStruct = require("../utils/parsedbr");
var Layout = require("../layouts/layout.js");
var Style = require("../utils/style");
var Link = require("./link");
var LinkCol = require("./linkcol");
var Residue = require("./residue");
var ResidueCol = require("./residuecol");

var Structure = Backbone.Model.extend({
    initialize: function(seq, dotbr, layout){
        this.set("seq", seq);
        this.set("dotbr", dotbr);
        this.set("layout", layout);
        this.set("style", new Style("standard"));
        this.set("renderSwitch", true);
        this.defineStructure();
        //event listening
        this.on("change:renderSwitch", this.defineStructure);
    },
    reconstruct: function(){
        //This function is used to update String/Dot-Bracket Notation
    	//after a hbond was inserted
    	var seq = "";
    	var dotbr = [];
    	var partner;
        var res = this.get("residues");

    	for(var i=0; i<res.length; i++){
    		seq += res.at(i).get("name");
    		partner = this.getPartner(i.toString());
    		if(partner === -1){
    			dotbr[i] = ".";
    		}
    		else if(partner > i){
    			dotbr[i] = "(";
    			dotbr[partner] = ")";
    		}
    		else {
    			continue;
    		}
    	}
        this.set("seq", seq);
        this.set("dotbr", dotbr.join(""));
        this.set("renderSwitch", !this.get("renderSwitch"));
    },
    defineStructure: function(){
        var seq = this.get("seq"),
            dotbr = this.get("dotbr"),
            layout = this.get("layout"),
            style = this.get("style");

        //set residues
        var resCol = new ResidueCol();
        var graph = parseStruct.parseDbr(seq, dotbr);
        var coords = new Layout(layout, graph.nodes, graph.links).getCoords();
        for(var i=0; i<graph.nodes.length; i++){
            resCol.add(new Residue({
                name: graph.nodes[i].name,
                color: style.getColor(graph.nodes[i].name),
                x: coords[i].x,
                y: coords[i].y,
                id: i.toString()
            }));
        }
        this.set("residues", resCol);

        //set bonds
        var linkCol = new LinkCol(null, style, resCol);
        for(var i=0; i<graph.links.length; i++){
            linkCol.add(new Link({
                id: graph.links[i].source + "to" + graph.links[i].target,
                source: graph.links[i].source.toString(),
                target: graph.links[i].target.toString(),
                label: graph.links[i].type,
                weight: style.getWeight(graph.links[i].type),
                color: style.getColor(graph.links[i].type)
            }));
        }
        this.set("links", linkCol);
        this.listenTo(this.get("links"), "update", this.reconstruct);
    },
    toCytoscape: function(){
        //Create a JSON structure from a graph object built by the
    	//transformDotBracket function
    	//The JSON structure fits the requirements of CytoscapeJS
    	var elements = [];
    	var el;

    	var nodes = this.get("residues");
    	for(var i = 0; i < nodes.length; i++){
            el = nodes.at(i);
    		elements.push({
    			group: el.get("group"),
    			data: {
    				id: el.get("id"),
    				label: el.get("name"),
                    type: "residue"
    			},
    			position: {
    				x: el.get("x"),
    				y: el.get("y")
    			},
    			selected: el.get("selected"),
    			selectable: el.get("selectable"),
    			locked: el.get("locked"),
    			grabbable: el.get("grabbable"),
    			css: {
    				'background-color': el.get("color")
    			}
    		});
    	}
    	var links = this.get("links");
    	for(var i = 0; i < links.length; i++){
    		el = links.at(i);
            elements.push({
    			group: el.get("group"),
    			data: {
    				id: el.get("id"),
    				source: el.get("source"),
        			target: el.get("target"),
        			label: el.get("label"),
        			weight: el.get("weight")
    			},
    			css: {
    				'line-color': el.get("color"),
    				'width': el.get("weight")
    			}
    		});
    	}
    	return elements;
    },
    getPartner: function(srcIndex){
    	//Returns the partner of a nucleotide:
    	//-1 means there is no partner
        var links = this.get("links");
    	var partner = -1;

    	for(var i=0; i<links.length; i++){
    		if(links.at(i).get("label") !== "phosphodiester"){
    			if(links.at(i).get("source") === srcIndex){
    				partner = links.at(i).get("target");
    				break;
    			}
    			else if(links.at(i).get("target") === srcIndex){
    				partner = links.at(i).get("source");
    				break;
    			}
    			else {
    				continue;
    			}
    		}
    	}
    	return partner;
    }
});

module.exports = Structure;
