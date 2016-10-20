var Backbone = require("backbone");
var $ = jQuery = require("jquery");
var spectrum = require("../utils/spectrum");
var lassotool = require("../utils/lasso");
var _ = require("underscore");
var tooltip = require("tooltip");

var Optspanel = Backbone.View.extend({
    events: {
        "click #export": "exportAsPNG",
        "click #center": "center",
        "click #lasso": "activateLasso",
        "click #discovery": "activateDiscovery",
        "click #newbond": "activateBondDrawing"
    },
    initialize: function(opts){
        this.el = opts.el;
        this.el.className += "container-fluid";
        this.el.id = "opts";
        this.struct = opts.struct;
        this.vis = opts.vis;

        this.listenTo(this.vis, "rendered", this.checkMode)
    },
    render: function(){
        tooltip({
            showDelay: 100,
            offset: {
                x: -85,
                y: 0
            },
            style: {
                "border-radius": "5px"
            }
        });
        this.el.innerHTML += '<div class="cntrl"><button class="icon" id="discovery" data-tooltip="Exploration mode" value="Discovery mode" readonly="readonly"><img class="mode" src="http://www.cipherpoint.com/wp-content/uploads/2014/07/search.png"></button>'
                        + '<button class="icon" id="lasso" value="Lasso mode"  data-tooltip="Selection mode" readonly="readonly"><img class="mode" src="https://d30y9cdsu7xlg0.cloudfront.net/png/21906-200.png"></button>'
                        + '<button class="icon" id="newbond" value="Bond drawing mode" data-tooltip="Editing mode" readonly="readonly"><img class="mode" src="http://vseo.vn/dao-tao-seo/uploads/tin-tuc/anchor-link.png"></button></div>';
  		this.el.innerHTML += '<div class="col-md-3"><p class="res">A</p></div>';
  		this.el.innerHTML += '<div class="col-md-3"><p class="res">C</p></div>';
  		this.el.innerHTML += '<div class="col-md-3"><p class="res">G</p></div>';
  		this.el.innerHTML += '<div class="col-md-3"><p class="res">U</p></div>';
        this.el.innerHTML += '<div class="col-md-3"><input type="text" id="acolor"></div>';
  		this.el.innerHTML += '<div class="col-md-3"><input type="text" id="ccolor"></div>';
  		this.el.innerHTML += '<div class="col-md-3"><input type="text" id="gcolor"></div>';
  		this.el.innerHTML += '<div class="col-md-3"><input type="text" id="ucolor"></div>';
        this.el.innerHTML += '<div class="col-md-9 colsel"><p>Color of selected nucleic acids</p></div>';
        this.el.innerHTML += '<div class="col-md-3 colsel"><input type="text" id="selcolor"></div>';
    	this.el.innerHTML += '<div class="cntrl"><input class="button" id="center" value="Reset viewport" readonly="readonly">'
    	               + '<input class="button" id="export" value="Export as PNG" readonly="readonly"></div>';

        //init colors
        this.initColors(this);
    },
    initColors: function(self){
        var res = self.struct.get("residues");
        var cy = self;
        $("#acolor").spectrum({
            color: "#64F73F",
            change: function(color){
                res.setResidueColor("A", color.toHexString());
                cy.vis.cy.nodes("[label='A']").css("background-color", color.toHexString());
            }
        });
        $("#ccolor").spectrum({
            color: "#FFB340",
            change: function(color){
                res.setResidueColor("C", color.toHexString());
                cy.vis.cy.nodes("[label='C']").css("background-color", color.toHexString());
            }
        });
        $("#gcolor").spectrum({
            color: "#EB413C",
            change: function(color){
                res.setResidueColor("G", color.toHexString());
                cy.vis.cy.nodes("[label='G']").css("background-color", color.toHexString());
            }
        });
        $("#ucolor").spectrum({
            color: "#3C88EE",
            change: function(color){
                res.setResidueColor("U", color.toHexString());
                cy.vis.cy.nodes("[label='U']").css("background-color", color.toHexString());
            }
        });
        $("#selcolor").spectrum({
            color: "#F6F6F6",
            change: function(color){
                var sel = cy.vis.cy.$(".chosen");
                res.setSelectionColor(sel, color.toHexString());
                sel.css("background-color", color.toHexString());
            }
        });
    },
    exportAsPNG: function(){
        var cy = this.vis.cy;
        var png64 = cy.png({scale: 5});
        var newTab = window.open();
        newTab.document.write("<img src=" + png64 + " />");
        newTab.focus();
    },
    center: function(){
        var cy = this.vis.cy;
        cy.center();
        cy.fit();
    },
    activateLasso: function(){
        var polygon = [];
        var cy = this.vis.cy;
        var self = this;
        //turn off panning and zoom
        cy.userPanningEnabled(false);
        cy.userZoomingEnabled(false);
        cy.nodes().lock();
        //disable edge drawing
        cy.edgehandles("disable");
        this.bondDrawing = false;
        //add lasso
        $(".cy")
        .lasso()
        .on("lassoBegin", function(e, lassoPoints) {
            polygon = [];
            canvas = self.vis.el.childNodes[1];
            c2 = canvas.getContext('2d');
            c2.fillStyle = "rgba(100, 100, 100, 0.02)";
            c2.beginPath();

            c2.moveTo(e.pageX, e.pageY);
        })
        .bind("lassoPoint", function(e, lassoPoint) {
            c2.lineTo(lassoPoint[0], lassoPoint[1] );
            c2.fill();
            polygon.push({x: lassoPoint[0], y: lassoPoint[1]});
        })
        .on("lassoDone", function(e, lassoPoints) {
            // do something with lassoPoints
            c2.closePath();
            c2.clearRect(0,0,canvas.width,canvas.height);
            var graphNodes = cy.nodes("[type!='index']");
            var nd = null;
            for(var i=0; i<graphNodes.length; i++){
                if(self.isPointInPoly(polygon, cy.$("#" + graphNodes[i].id()).renderedPosition())){
                    cy.$("#" + graphNodes[i].id()).addClass("chosen");
                }
            }
        });
    },
    isPointInPoly: function(poly, pt){
        var i, j, c = false;
        for (i = 0, j = poly.length-1; i < poly.length; j = i++) {
          if ( ((poly[i].y>pt.y) != (poly[j].y>pt.y)) &&
            (pt.x < (poly[j].x-poly[i].x) * (pt.y-poly[i].y) / (poly[j].y-poly[i].y) + poly[i].x) )
            c = !c;
        }
        return c;
    },
    activateDiscovery: function(){
        var cy = this.vis.cy;
        //remove lasso
        this.removeLasso();
        //disable edge drawing
        cy.edgehandles("disable");
        //turn zooming and panning back on
        cy.userPanningEnabled(true);
        cy.userZoomingEnabled(true);
        cy.nodes().unlock();
        this.bondDrawing = false;
    },
    activateBondDrawing: function(){
        var cy = this.vis.cy;
        //remove lasso
        this.removeLasso();
        cy.edgehandles("enable");
        this.bondDrawing = true;
    },
    removeLasso: function(){
        //remove lasso
        $(".cy").lasso().off("lassoBegin");
        $(".cy").lasso().off("lassoDone");
        $(".cy").lasso().unbind("lassoPoint");
    },
    checkMode: function(){
        if(this.bondDrawing){
            this.vis.cy.edgehandles("enable");
        }
    }
});

module.exports = Optspanel;
