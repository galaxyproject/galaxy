var Backbone = require("backbone");
var cytoscape = require("cytoscape");
var $ = jQuery = require("jquery");
var Link = require("../models/link");
var AnnoView = require("./annoview");
var edgehandles = require("cytoscape-edgehandles")(cytoscape, $);
var Style = require("../utils/style");

var Vispanel = Backbone.View.extend({
    initialize: function(opts){
        this.el = opts.el;
        this.struct = opts.struct;
        this.resindex = opts.resindex;
        this.annotate = true;

        //events
        this.listenTo(this.struct, "change:renderSwitch", this.render);
    },
    render: function(){
        var self = this;
        var srcNode = null;
        var targetNode = null;
        self.innerHTML = "";

        this.cy = cytoscape({
      		container: self.el,
      		style: (new Style()).getCytoscapeStyle(),
      		elements: self.struct.toCytoscape(),
      		layout: {
      			//Use preset layout with precalculated
      			//nucleotide coordinates
        		name: 'preset',
      		},
          	ready: function(){
                this.edges("[label='violation']").each(function(index, ele){
                    if(Object.keys(ele._private.classes).length === 0){
                        ele.addClass("wcwccis");
                    }
                });
                //events
                this.on("tapstart", function(evt){
                    this.$(".chosen").removeClass("chosen");
                });
                this.on("tapdragover", "node", function(evt){
                    var seqbox = document.getElementById("seqbox");
                    if(seqbox && (this.id() < seqbox.value.length)){
                        seqbox.selectionStart = parseInt(this.id());
                        seqbox.selectionEnd = parseInt(this.id())+1;
                    }
                });
                this.on("tapdragout", "node", function(evt){
                    var seqbox = document.getElementById("seqbox");
                    if(seqbox && (this.id() < seqbox.value.length)){
                        seqbox.selectionEnd = -1;
                    }
                });
                this.on("tap", "edge", function(evt){
                    if(self.annotate && this.data("label") === "violation"){
                        var obj = this._private.classes;
                        for(var c in obj) break;
                        new AnnoView(c.substring(0, 2), c.substring(2, 4), c.substring(4, c.length+1), this, self.el);
                    }
                });

                //Residue Nodes
                if(self.resindex){
                    self.setResidueNodes(this);
                }
          	},
            userPanningEnabled: true,
            userZoomingEnabled: true
    	});

        this.cy.edgehandles({
            loopAllowed: function(node){
                // for the specified node, return whether edges from itself to itself are allowed
                return false;
            },
            complete: function(srcNode, targetNode, addedEntities){
                // fired when edgehandles is done and entities are added
                self.struct.get("links").newBond(srcNode[0].id(), targetNode[0].id());
            },
            enabled: false,
            preview: false
		});

        this.trigger("rendered");
    },
    setResidueNodes: function(cy){
        //index nodes
        for(var i=1; i<this.struct.get("seq").length/5; i++){
            var pos = this.getPos(this.struct, (i*5)-1);
            this.cy.add({
                group: "nodes",
                data: {
                    id: (this.struct.get("seq").length + i).toString(),
                    label: (i*5) + "",
                    type: "index"
                },
                position: {
                    x: pos[0],
                    y: pos[1]
                },
                selected: false,
                selectable: false,
                locked: false,
                grabbable: true,
                css: {
                    "background-color": "#fff"
                }
            });
            cy.add({
                group: "edges",
                data: {
                    id: "index" + i,
                    source: (i*5) - 1,
                    target: this.struct.get("seq").length + i,
                    label: i*5,
                    weight: 4
                },
                css: {
                    'line-color': "black",
                    'width': 4
                }
            });
        }
    },
    getPos: function(struct, target){
        var distance = 50;
        var found = false;
        var originX = struct.get("residues").at(target).get("x");
        var originY = struct.get("residues").at(target).get("y");
        var angleFactor = 0.0;
        var angle, x, y, tx, ty;
        while(!found && angleFactor<1){
            angle = angleFactor*Math.PI*2;
            x = Math.cos(angle)*distance + originX;
            y = Math.sin(angle)*distance + originY;
            for(var i=0; i<struct.get("seq").length+1; i++){
                if(i === struct.get("seq").length){
                    found = true;
                    break;
                }
                tx = struct.get("residues").at(i).get("x");
                ty = struct.get("residues").at(i).get("y");
                if(Math.pow((x - tx), 2) + Math.pow((y - ty), 2) < Math.pow(distance, 2)){
                    break;
                }
            }
            angleFactor += 0.05
        }
        return [x, y];
    },
    changeBondType: function(bondid, type){
        if(type === "canonical"){
            this.cy.$("#" + bondid)[0].style("line-color", "#3A9AD9")
            this.cy.$("#" + bondid)[0].style("width", 4);
            this.cy.$("#" + bondid)[0]._private.classes = {};
        }
        else if(type === "non-canonical"){
            this.cy.$("#" + bondid)[0].style("line-color", "red");
            this.cy.$("#" + bondid)[0].style("width", 4);
            this.cy.$("#" + bondid)[0].addClass("wcwccis");
        }
        else {
            throw new Error("Type must be 'canoncial' or 'non-canonical'");
        }
    },
    addNCBond: function(source, target){
        this.cy.add({
            group: "edges",
            data: {
                id: source + "to" + target,
                source: source.toString(),
                target: target.toString()
            },
            css: {
                "line-color": "red",
                "width": 4
            }
        });
        this.cy.$("#" + source + "to" + target)[0].addClass("wcwccis");
    },
    setLeontisWesthof: function(edge, lwclass){
        var validClasses = [
            "wcwccis",
            "wcwctrans",
            "sgsgcis",
            "sgsgtrans",
            "hghgcis",
            "hghgtrans",
            "wcsgcis",
            "wcsgtrans",
            "sgwccis",
            "sgwctrans",
            "wchgcis",
            "wchgtrans",
            "hgwccis",
            "hgwctrans",
            "hgsgcis",
            "hgsgtrans",
            "sghgcis",
            "sghgtrans"
        ];
        if(validClasses.indexOf(lwclass) === -1){
            throw new Error("LW-Class must be one of " + validClasses);
        }
        else {
            var classes = Object.keys(this.cy.$("#" + edge)[0]._private.classes);
            for(var i=0; i<classes.length; i++){
                this.cy.$("#" + edge)[0].removeClass(classes[i]);
            }
            this.cy.$("#" + edge)[0].addClass(lwclass);
        }
    }
});

module.exports = Vispanel;
