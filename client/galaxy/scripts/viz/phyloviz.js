import $ from "jquery";
import Backbone from "backbone";
import _l from "utils/localization";
import * as d3 from "libs/d3";
import visualization_mod from "viz/visualization";
import { Dataset } from "mvc/dataset/data";
import mod_icon_btn from "mvc/ui/icon-button";
import { show_message, hide_modal } from "layout/modal";

/**
 * Base class of any menus that takes in user interaction. Contains checking methods.
 */
var UserMenuBase = Backbone.View.extend({
    className: "UserMenuBase",

    /**
     * Check if an input value is a number and falls within max min.
     */
    isAcceptableValue: function($inputKey, min, max) {
        //TODO: use better feedback than alert
        var value = $inputKey.val();

        var fieldName = $inputKey.attr("displayLabel") || $inputKey.attr("id").replace("phyloViz", "");

        function isNumeric(n) {
            return !isNaN(parseFloat(n)) && isFinite(n);
        }

        if (!isNumeric(value)) {
            alert(`${fieldName} is not a number!`);
            return false;
        }

        if (value > max) {
            alert(`${fieldName} is too large.`);
            return false;
        } else if (value < min) {
            alert(`${fieldName} is too small.`);
            return false;
        }
        return true;
    },

    /**
     * Check if any user string inputs has illegal characters that json cannot accept
     */
    hasIllegalJsonCharacters: function($inputKey) {
        if ($inputKey.val().search(/"|'|\\/) !== -1) {
            alert(
                "Named fields cannot contain these illegal characters: " +
                    "double quote(\"), single guote('), or back slash(\\). "
            );
            return true;
        }
        return false;
    }
});

/**
 * -- Custom Layout call for phyloViz to suit the needs of a phylogenetic tree.
 * -- Specifically: 1) Nodes have a display display of (= evo dist X depth separation) from their parent
 *                  2) Nodes must appear in other after they have expand and contracted
 */
function PhyloTreeLayout() {
    var self = this; // maximum length of the text labels

    var hierarchy = d3.layout
        .hierarchy()
        .sort(null)
        .value(null);

    var // ! represents both the layout angle and the height of the layout, in px
        height = 360;

    var layoutMode = "Linear";

    var // height of each individual leaf node
        leafHeight = 18;

    var // separation between nodes of different depth, in px
        depthSeparation = 200;

    var // change to recurssive call
        leafIndex = 0;

    var // tree defaults to 0.5 dist if no dist is specified
        defaultDist = 0.5;

    var maxTextWidth = 50;

    self.leafHeight = inputLeafHeight => {
        if (typeof inputLeafHeight === "undefined") {
            return leafHeight;
        } else {
            leafHeight = inputLeafHeight;
            return self;
        }
    };

    self.layoutMode = mode => {
        if (typeof mode === "undefined") {
            return layoutMode;
        } else {
            layoutMode = mode;
            return self;
        }
    };

    // changes the layout angle of the display, which is really changing the height
    self.layoutAngle = angle => {
        if (typeof angle === "undefined") {
            return height;
        }
        // to use default if the user puts in strange values
        if (isNaN(angle) || angle < 0 || angle > 360) {
            return self;
        } else {
            height = angle;
            return self;
        }
    };

    self.separation = dist => {
        // changes the dist between the nodes of different depth
        if (typeof dist === "undefined") {
            return depthSeparation;
        } else {
            depthSeparation = dist;
            return self;
        }
    };

    self.links = (
        nodes // uses d3 native method to generate links. Done.
    ) => d3.layout.tree().links(nodes);

    // -- Custom method for laying out phylogeny tree in a linear fashion
    self.nodes = (d, i) => {
        //TODO: newick and phyloxml return arrays. where should this go (client (here, else), server)?
        if (toString.call(d) === "[object Array]") {
            // if d is an array, replate with the first object (newick, phyloxml)
            d = d[0];
        }

        // self is to find the depth of all the nodes, assumes root is passed in
        var _nodes = hierarchy.call(self, d, i);

        var nodes = [];
        var maxDepth = 0;
        var numLeaves = 0;
        //console.debug( JSON.stringify( _nodes, null, 2 ) )
        window._d = d;
        window._nodes = _nodes;

        //TODO: remove dbl-touch loop
        // changing from hierarchy's custom format for data to usable format
        _nodes.forEach(node => {
            maxDepth = node.depth > maxDepth ? node.depth : maxDepth; //finding max depth of tree
            nodes.push(node);
        });
        // counting the number of leaf nodes and assigning max depth
        //  to nodes that do not have children to flush all the leave nodes
        nodes.forEach(node => {
            if (!node.children) {
                //&& !node._children
                numLeaves += 1;
                node.depth = maxDepth; // if a leaf has no child it would be assigned max depth
            }
        });

        leafHeight = layoutMode === "Circular" ? height / numLeaves : leafHeight;
        leafIndex = 0;
        layout(nodes[0], maxDepth, leafHeight, null);

        return nodes;
    };

    /**
     * -- Function with side effect of adding x0, y0 to all child; take in the root as starting point
     *  assuming that the leave nodes would be sorted in presented order
     *          horizontal(y0) is calculated according to (= evo dist X depth separation) from their parent
     *          vertical (x0) - if leave node: find its order in all of the  leave node === node.id,
     *                              then multiply by verticalSeparation
     *                  - if parent node: is place in the mid point all of its children nodes
     * -- The layout will first calculate the y0 field going towards the leaves, and x0 when returning
     */
    function layout(node, maxDepth, vertSeparation, parent) {
        var children = node.children;
        var sumChildVertSeparation = 0;

        // calculation of node's dist from parents, going down.
        var dist = node.dist || defaultDist;
        dist = dist > 1 ? 1 : dist; // We constrain all dist to be less than one
        node.dist = dist;
        if (parent !== null) {
            node.y0 = parent.y0 + dist * depthSeparation;
        } else {
            //root node
            node.y0 = maxTextWidth;
        }

        // if a node have no children, we will treat it as a leaf and start laying it out first
        if (!children) {
            node.x0 = leafIndex * vertSeparation;
            leafIndex += 1;
        } else {
            // if it has children, we will visit all its children and calculate its position from its children
            children.forEach(child => {
                child.parent = node;
                sumChildVertSeparation += layout(child, maxDepth, vertSeparation, node);
            });
            node.x0 = sumChildVertSeparation / children.length;
        }

        // adding properties to the newly created node
        node.x = node.x0;
        node.y = node.y0;
        return node.x0;
    }
    return self;
}

/**
 * -- PhyloTree Model --
 */
var PhyloTree = visualization_mod.Visualization.extend({
    defaults: {
        layout: "Linear",
        separation: 250, // px dist between nodes of different depth to represent 1 evolutionary until
        leafHeight: 18,
        type: "phyloviz", // visualization type
        title: _l("Title"),
        scaleFactor: 1,
        translate: [0, 0],
        fontSize: 12, //fontSize of node label
        selectedNode: null,
        nodeAttrChangedTime: 0
    },

    initialize: function(options) {
        this.set(
            "dataset",
            new Dataset({
                id: options.dataset_id
            })
        );
    },

    root: {}, // Root has to be its own independent object because it is not part of the viz_config

    /**
     * Mechanism to expand or contract a single node. Expanded nodes have a children list, while for
     * contracted nodes the list is stored in _children. Nodes with their children data stored in _children will not
     * have their children rendered.
     */
    toggle: function(d) {
        if (typeof d === "undefined") {
            return;
        }
        if (d.children) {
            d._children = d.children;
            d.children = null;
        } else {
            d.children = d._children;
            d._children = null;
        }
    },

    /**
     *  Contracts the phylotree to a single node by repeatedly calling itself to place all the list
     *  of children under _children.
     */
    toggleAll: function(d) {
        if (d.children && d.children.length !== 0) {
            d.children.forEach(this.toggleAll);
            this.toggle(d);
        }
    },

    /**
     *  Return the data of the tree. Used for preserving state.
     */
    getData: function() {
        return this.root;
    },

    /**
     * Overriding the default save mechanism to do some clean of circular reference of the
     * phyloTree and to include phyloTree in the saved json
     */
    save: function() {
        var root = this.root;
        cleanTree(root);
        //this.set("root", root);

        function cleanTree(node) {
            // we need to remove parent to delete circular reference
            delete node.parent;

            // removing unnecessary attributes
            if (node._selected) {
                delete node._selected;
            }

            if (node.children) {
                node.children.forEach(cleanTree);
            }
            if (node._children) {
                node._children.forEach(cleanTree);
            }
        }

        var config = $.extend(true, {}, this.attributes);
        config.selectedNode = null;

        show_message("Saving to Galaxy", "progress");

        return $.ajax({
            url: this.url(),
            type: "POST",
            dataType: "json",
            data: {
                config: JSON.stringify(config),
                type: "phyloviz"
            },
            success: function(res) {
                hide_modal();
            }
        });
    }
});

// -- Views --
/**
 *  Stores the default variable for setting up the visualization
 */
var PhylovizLayoutBase = Backbone.View.extend({
    defaults: {
        nodeRadius: 4.5 // radius of each node in the diagram
    },

    /**
     *  Common initialization in layouts
     */
    stdInit: function(options) {
        var self = this;
        self.model.on(
            "change:separation change:leafHeight change:fontSize change:nodeAttrChangedTime",
            self.updateAndRender,
            self
        );

        self.vis = options.vis;
        self.i = 0;
        self.maxDepth = -1; // stores the max depth of the tree

        self.width = options.width;
        self.height = options.height;
    },

    /**
     *  Updates the visualization whenever there are changes in the expansion and contraction of nodes
     *  AND possibly when the tree is edited.
     */
    updateAndRender: function(source) {
        var self = this;
        source = source || self.model.root;

        self.renderNodes(source);
        self.renderLinks(source);
        self.addTooltips();
    },

    /**
     * Renders the links for the visualization.
     */
    renderLinks: function(source) {
        var self = this;
        var link = self.vis.selectAll("g.completeLink").data(self.tree.links(self.nodes), d => d.target.id);

        var calcalateLinePos = d => {
            // position of the source node <=> starting location of the line drawn
            d.pos0 = `${d.source.y0} ${d.source.x0}`;
            // position where the line makes a right angle bend
            d.pos1 = `${d.source.y0} ${d.target.x0}`;
            // point where the horizontal line becomes a dotted line
            d.pos2 = `${d.target.y0} ${d.target.x0}`;
        };

        var linkEnter = link
            .enter()
            .insert("svg:g", "g.node")
            .attr("class", "completeLink");

        linkEnter
            .append("svg:path")
            .attr("class", "link")
            .attr("d", d => {
                calcalateLinePos(d);
                return `M ${d.pos0} L ${d.pos1}`;
            });

        var linkUpdate = link.transition().duration(500);

        linkUpdate.select("path.link").attr("d", d => {
            calcalateLinePos(d);
            return `M ${d.pos0} L ${d.pos1} L ${d.pos2}`;
        });

        link.exit().remove();
    },

    // User Interaction methods below

    /**
     *  Displays the information for editing
     */
    selectNode: function(node) {
        var self = this;
        d3.selectAll("g.node").classed("selectedHighlight", d => {
            if (node.id === d.id) {
                if (node._selected) {
                    // for de=selecting node.
                    delete node._selected;
                    return false;
                } else {
                    node._selected = true;
                    return true;
                }
            }
            return false;
        });

        self.model.set("selectedNode", node);
        $("#phyloVizSelectedNodeName").val(node.name);
        $("#phyloVizSelectedNodeDist").val(node.dist);
        $("#phyloVizSelectedNodeAnnotation").val(node.annotation || "");
    },

    /**
     *  Creates bootstrap tooltip for the visualization. Has to be called repeatedly due to newly generated
     *  enterNodes
     */
    addTooltips: function() {
        $(".tooltip").remove(); //clean up tooltip, just in case its listeners are removed by d3
        $(".node")
            .attr("data-original-title", function() {
                var d = this.__data__;
                var annotation = d.annotation || "None";
                return d
                    ? `${d.name ? `${d.name}<br/>` : ""}Dist: ${d.dist} <br/>Annotation1: ${annotation}${
                          d.bootstrap ? `<br/>Confidence level: ${Math.round(100 * d.bootstrap)}` : ""
                      }`
                    : "";
            })
            .tooltip({ placement: "top", trigger: "hover" });
    }
});

/**
 * Linea layout class of Phyloviz, is responsible for rendering the nodes
 * calls PhyloTreeLayout to determine the positions of the nodes
 */
var PhylovizLinearView = PhylovizLayoutBase.extend({
    initialize: function(options) {
        // Default values of linear layout
        var self = this;
        self.margins = options.margins;
        self.layoutMode = "Linear";

        self.stdInit(options);

        self.layout();
        self.updateAndRender(self.model.root);
    },

    /**
     * Creates the basic layout of a linear tree by precalculating fixed values.
     * One of calculations are also made here
     */
    layout: function() {
        var self = this;
        self.tree = new PhyloTreeLayout().layoutMode("Linear");
        self.diagonal = d3.svg.diagonal().projection(d => [d.y, d.x]);
    },

    /**
     * Renders the nodes base on Linear layout.
     */
    renderNodes: function(source) {
        var self = this;
        var fontSize = `${self.model.get("fontSize")}px`;

        // assigning properties from models
        self.tree.separation(self.model.get("separation")).leafHeight(self.model.get("leafHeight"));

        var duration = 500;

        var nodes = self.tree.separation(self.model.get("separation")).nodes(self.model.root);

        var node = self.vis.selectAll("g.node").data(nodes, d => d.name + d.id || (d.id = ++self.i));

        // These variables has to be passed into update links which are in the base methods
        self.nodes = nodes;
        self.duration = duration;

        // ------- D3 ENTRY --------
        // Enter any new nodes at the parent's previous position.
        var nodeEnter = node
            .enter()
            .append("svg:g")
            .attr("class", "node")
            .on("dblclick", () => {
                d3.event.stopPropagation();
            })
            .on("click", d => {
                if (d3.event.altKey) {
                    self.selectNode(d); // display info if alt is pressed
                } else {
                    if (d.children && d.children.length === 0) {
                        return;
                    } // there is no need to toggle leaves
                    self.model.toggle(d); // contract/expand nodes at data level
                    self.updateAndRender(d); // re-render the tree
                }
            });
        //TODO: newick and phyloxml return arrays. where should this go (client (here, else), server)?
        if (toString.call(source) === "[object Array]") {
            // if d is an array, replate with the first object (newick, phyloxml)
            source = source[0];
        }
        nodeEnter.attr("transform", d => `translate(${source.y0},${source.x0})`);

        nodeEnter
            .append("svg:circle")
            .attr("r", 1e-6)
            .style("fill", d => (d._children ? "lightsteelblue" : "#fff"));

        nodeEnter
            .append("svg:text")
            .attr("class", "nodeLabel")
            .attr("x", d => (d.children || d._children ? -10 : 10))
            .attr("dy", ".35em")
            .attr("text-anchor", d => (d.children || d._children ? "end" : "start"))
            .style("fill-opacity", 1e-6);

        // ------- D3 TRANSITION --------
        // Transition nodes to their new position.
        var nodeUpdate = node.transition().duration(duration);

        nodeUpdate.attr("transform", d => `translate(${d.y},${d.x})`);

        nodeUpdate
            .select("circle")
            .attr("r", self.defaults.nodeRadius)
            .style("fill", d => (d._children ? "lightsteelblue" : "#fff"));

        nodeUpdate
            .select("text")
            .style("fill-opacity", 1)
            .style("font-size", fontSize)
            .text(d => (d.name && d.name !== "" ? d.name : d.bootstrap ? Math.round(100 * d.bootstrap) : ""));

        // ------- D3 EXIT --------
        // Transition exiting nodes to the parent's new position.
        var nodeExit = node
            .exit()
            .transition()
            .duration(duration)
            .remove();

        nodeExit.select("circle").attr("r", 1e-6);

        nodeExit.select("text").style("fill-opacity", 1e-6);

        // Stash the old positions for transition.
        nodes.forEach(d => {
            d.x0 = d.x; // we need the x0, y0 for parents with children
            d.y0 = d.y;
        });
    }
});

export var PhylovizView = Backbone.View.extend({
    className: "phyloviz",

    initialize: function(options) {
        var self = this;
        // -- Default values of the vis
        self.MIN_SCALE = 0.05; //for zooming
        self.MAX_SCALE = 5;
        self.MAX_DISPLACEMENT = 500;
        self.margins = [10, 60, 10, 80];

        self.width = $("#PhyloViz").width();
        self.height = $("#PhyloViz").height();
        self.radius = self.width;
        self.data = options.data;

        // -- Events Phyloviz view responses to
        $(window).resize(() => {
            self.width = $("#PhyloViz").width();
            self.height = $("#PhyloViz").height();
            self.render();
        });

        // -- Create phyloTree model
        self.phyloTree = new PhyloTree(options.config);
        self.phyloTree.root = self.data;

        // -- Set up UI functions of main view
        self.zoomFunc = d3.behavior.zoom().scaleExtent([self.MIN_SCALE, self.MAX_SCALE]);
        self.zoomFunc.translate(self.phyloTree.get("translate"));
        self.zoomFunc.scale(self.phyloTree.get("scaleFactor"));

        // -- set up header buttons, search and settings menu
        self.navMenu = new HeaderButtons(self);
        self.settingsMenu = new SettingsMenu({
            phyloTree: self.phyloTree
        });
        self.nodeSelectionView = new NodeSelectionView({
            phyloTree: self.phyloTree
        });
        self.search = new PhyloVizSearch();

        // using settimeout to call the zoomAndPan function according to the stored attributes in viz_config
        setTimeout(() => {
            self.zoomAndPan();
        }, 1000);
    },

    render: function() {
        // -- Creating helper function for vis. --
        var self = this;
        $("#PhyloViz").empty();

        // -- Layout viz. --
        self.mainSVG = d3
            .select("#PhyloViz")
            .append("svg:svg")
            .attr("width", self.width)
            .attr("height", self.height)
            .attr("pointer-events", "all")
            .call(
                self.zoomFunc.on("zoom", () => {
                    self.zoomAndPan();
                })
            );

        self.boundingRect = self.mainSVG
            .append("svg:rect")
            .attr("class", "boundingRect")
            .attr("width", self.width)
            .attr("height", self.height)
            .attr("stroke", "black")
            .attr("fill", "white");

        self.vis = self.mainSVG.append("svg:g").attr("class", "vis");

        self.layoutOptions = {
            model: self.phyloTree,
            width: self.width,
            height: self.height,
            vis: self.vis,
            margins: self.margins
        };

        // -- Creating Title
        $("#title").text(`Phylogenetic Tree from ${self.phyloTree.get("title")}:`);

        // -- Create Linear view instance --
        new PhylovizLinearView(self.layoutOptions);
    },

    /**
     * Function to zoom and pan the svg element which the entire tree is contained within
     * Uses d3.zoom events, and extend them to allow manual updates and keeping states in model
     */
    zoomAndPan: function(event) {
        var zoomParams;
        var translateParams;
        if (typeof event !== "undefined") {
            zoomParams = event.zoom;
            translateParams = event.translate;
        }

        var self = this;
        var scaleFactor = self.zoomFunc.scale();
        var translationCoor = self.zoomFunc.translate();
        var zoomStatement = "";
        var translateStatement = "";

        // Do manual scaling.
        switch (zoomParams) {
            case "reset":
                scaleFactor = 1.0;
                translationCoor = [0, 0];
                break;
            case "+":
                scaleFactor *= 1.1;
                break;
            case "-":
                scaleFactor *= 0.9;
                break;
            default:
                if (typeof zoomParams === "number") {
                    scaleFactor = zoomParams;
                } else if (d3.event !== null) {
                    scaleFactor = d3.event.scale;
                }
        }
        if (scaleFactor < self.MIN_SCALE || scaleFactor > self.MAX_SCALE) {
            return;
        }
        self.zoomFunc.scale(scaleFactor); //update scale Factor
        zoomStatement = `translate(${self.margins[3]},${self.margins[0]}) scale(${scaleFactor})`;

        // Do manual translation.
        if (d3.event !== null) {
            translateStatement = `translate(${d3.event.translate})`;
        } else {
            if (typeof translateParams !== "undefined") {
                var x = translateParams.split(",")[0];
                var y = translateParams.split(",")[1];
                if (!isNaN(x) && !isNaN(y)) {
                    translationCoor = [translationCoor[0] + parseFloat(x), translationCoor[1] + parseFloat(y)];
                }
            }
            self.zoomFunc.translate(translationCoor); // update zoomFunc
            translateStatement = `translate(${translationCoor})`;
        }

        self.phyloTree.set("scaleFactor", scaleFactor);
        self.phyloTree.set("translate", translationCoor);
        //refers to the view that we are actually zooming
        self.vis.attr("transform", translateStatement + zoomStatement);
    },

    /**
     * Primes the Ajax URL to load another Nexus tree
     */
    reloadViz: function() {
        var self = this;
        var treeIndex = $("#phylovizNexSelector :selected").val();
        $.getJSON(
            self.phyloTree.get("dataset").url(),
            {
                tree_index: treeIndex,
                data_type: "raw_data"
            },
            packedJson => {
                self.data = packedJson.data;
                self.config = packedJson;
                self.render();
            }
        );
    }
});

var HeaderButtons = Backbone.View.extend({
    initialize: function(phylovizView) {
        var self = this;
        self.phylovizView = phylovizView;

        // Clean up code - if the class initialized more than once
        $("#panelHeaderRightBtns").empty();
        $("#phyloVizNavBtns").empty();
        $("#phylovizNexSelector").off();

        self.initNavBtns();
        self.initRightHeaderBtns();

        // Initial a tree selector in the case of nexus
        $("#phylovizNexSelector")
            .off()
            .on("change", () => {
                self.phylovizView.reloadViz();
            });
    },

    initRightHeaderBtns: function() {
        var self = this;

        var rightMenu = mod_icon_btn.create_icon_buttons_menu(
            [
                {
                    icon_class: "gear",
                    title: _l("PhyloViz Settings"),
                    on_click: function() {
                        $("#SettingsMenu").show();
                        self.settingsMenu.updateUI();
                    }
                },
                {
                    icon_class: "disk",
                    title: _l("Save visualization"),
                    on_click: function() {
                        var nexSelected = $("#phylovizNexSelector option:selected").text();
                        if (nexSelected) {
                            self.phylovizView.phyloTree.set("title", nexSelected);
                        }
                        self.phylovizView.phyloTree.save();
                    }
                },
                {
                    icon_class: "chevron-expand",
                    title: "Search / Edit Nodes",
                    on_click: function() {
                        $("#nodeSelectionView").show();
                    }
                },
                {
                    icon_class: "information",
                    title: _l("Phyloviz Help"),
                    on_click: function() {
                        window.open("https://galaxyproject.org/learn/visualization/phylogenetic-tree/");
                        // https://docs.google.com/document/d/1AXFoJgEpxr21H3LICRs3EyMe1B1X_KFPouzIgrCz3zk/edit
                    }
                }
            ],
            {
                tooltip_config: { placement: "bottom" }
            }
        );
        $("#panelHeaderRightBtns").append(rightMenu.$el);
    },

    initNavBtns: function() {
        var self = this;

        var navMenu = mod_icon_btn.create_icon_buttons_menu(
            [
                {
                    icon_class: "zoom-in",
                    title: _l("Zoom in"),
                    on_click: function() {
                        self.phylovizView.zoomAndPan({ zoom: "+" });
                    }
                },
                {
                    icon_class: "zoom-out",
                    title: _l("Zoom out"),
                    on_click: function() {
                        self.phylovizView.zoomAndPan({ zoom: "-" });
                    }
                },
                {
                    icon_class: "arrow-circle",
                    title: "Reset Zoom/Pan",
                    on_click: function() {
                        self.phylovizView.zoomAndPan({
                            zoom: "reset"
                        });
                    }
                }
            ],
            {
                tooltip_config: { placement: "bottom" }
            }
        );

        $("#phyloVizNavBtns").append(navMenu.$el);
    }
});

var SettingsMenu = UserMenuBase.extend({
    className: "Settings",

    initialize: function(options) {
        // settings needs to directly interact with the phyloviz model so it will get access to it.
        var self = this;
        self.phyloTree = options.phyloTree;
        self.el = $("#SettingsMenu");
        self.inputs = {
            separation: $("#phyloVizTreeSeparation"),
            leafHeight: $("#phyloVizTreeLeafHeight"),
            fontSize: $("#phyloVizTreeFontSize")
        };

        //init all buttons of settings
        $("#settingsCloseBtn")
            .off()
            .on("click", () => {
                self.el.hide();
            });
        $("#phylovizResetSettingsBtn")
            .off()
            .on("click", () => {
                self.resetToDefaults();
            });
        $("#phylovizApplySettingsBtn")
            .off()
            .on("click", () => {
                self.apply();
            });
    },

    /**
     * Applying user values to phylotree model.
     */
    apply: function() {
        var self = this;
        if (
            !self.isAcceptableValue(self.inputs.separation, 50, 2500) ||
            !self.isAcceptableValue(self.inputs.leafHeight, 5, 30) ||
            !self.isAcceptableValue(self.inputs.fontSize, 5, 20)
        ) {
            return;
        }
        $.each(self.inputs, (key, $input) => {
            self.phyloTree.set(key, $input.val());
        });
    },
    /**
     * Called to update the values input to that stored in the model
     */
    updateUI: function() {
        var self = this;
        $.each(self.inputs, (key, $input) => {
            $input.val(self.phyloTree.get(key));
        });
    },
    /**
     * Resets the value of the phyloTree model to its default
     */
    resetToDefaults: function() {
        $(".tooltip").remove(); // just in case the tool tip was not removed
        var self = this;
        $.each(self.phyloTree.defaults, (key, value) => {
            self.phyloTree.set(key, value);
        });
        self.updateUI();
    },

    render: function() {}
});

/**
 * View for inspecting node properties and editing them
 */
var NodeSelectionView = UserMenuBase.extend({
    className: "Settings",

    initialize: function(options) {
        var self = this;
        self.el = $("#nodeSelectionView");
        self.phyloTree = options.phyloTree;

        self.UI = {
            enableEdit: $("#phylovizEditNodesCheck"),
            saveChanges: $("#phylovizNodeSaveChanges"),
            cancelChanges: $("#phylovizNodeCancelChanges"),
            name: $("#phyloVizSelectedNodeName"),
            dist: $("#phyloVizSelectedNodeDist"),
            annotation: $("#phyloVizSelectedNodeAnnotation")
        };

        // temporarily stores the values in case user change their mind
        self.valuesOfConcern = {
            name: null,
            dist: null,
            annotation: null
        };

        //init UI buttons
        $("#nodeSelCloseBtn")
            .off()
            .on("click", () => {
                self.el.hide();
            });
        self.UI.saveChanges.off().on("click", () => {
            self.updateNodes();
        });
        self.UI.cancelChanges.off().on("click", () => {
            self.cancelChanges();
        });

        ($ => {
            // extending jquery fxn for enabling and disabling nodes.
            $.fn.enable = function(isEnabled) {
                return $(this).each(function() {
                    if (isEnabled) {
                        $(this).removeAttr("disabled");
                    } else {
                        $(this).attr("disabled", "disabled");
                    }
                });
            };
        })($);

        self.UI.enableEdit.off().on("click", () => {
            self.toggleUI();
        });
    },

    /**
     * For turning on and off the child elements
     */
    toggleUI: function() {
        var self = this;
        var checked = self.UI.enableEdit.is(":checked");

        if (!checked) {
            self.cancelChanges();
        }

        $.each(self.valuesOfConcern, (key, value) => {
            self.UI[key].enable(checked);
        });
        if (checked) {
            self.UI.saveChanges.show();
            self.UI.cancelChanges.show();
        } else {
            self.UI.saveChanges.hide();
            self.UI.cancelChanges.hide();
        }
    },

    /**
     * Reverting to previous values in case user change their minds
     */
    cancelChanges: function() {
        var self = this;
        var node = self.phyloTree.get("selectedNode");
        if (node) {
            $.each(self.valuesOfConcern, (key, value) => {
                self.UI[key].val(node[key]);
            });
        }
    },

    /**
     * Changing the data in the underlying tree with user-specified values
     */
    updateNodes: function() {
        var self = this;
        var node = self.phyloTree.get("selectedNode");
        if (node) {
            if (
                !self.isAcceptableValue(self.UI.dist, 0, 1) ||
                self.hasIllegalJsonCharacters(self.UI.name) ||
                self.hasIllegalJsonCharacters(self.UI.annotation)
            ) {
                return;
            }
            $.each(self.valuesOfConcern, (key, value) => {
                node[key] = self.UI[key].val();
            });
            self.phyloTree.set("nodeAttrChangedTime", new Date());
        } else {
            alert("No node selected");
        }
    }
});

/**
 * Initializes the search panel on phyloviz and handles its user interaction
 * It allows user to search the entire free based on some qualifer, like dist <= val.
 */
var PhyloVizSearch = UserMenuBase.extend({
    initialize: function() {
        var self = this;

        $("#phyloVizSearchBtn").on("click", () => {
            var searchTerm = $("#phyloVizSearchTerm");

            var searchConditionVal = $("#phyloVizSearchCondition")
                .val()
                .split("-");

            var attr = searchConditionVal[0];
            var condition = searchConditionVal[1];
            self.hasIllegalJsonCharacters(searchTerm);

            if (attr === "dist") {
                self.isAcceptableValue(searchTerm, 0, 1);
            }
            self.searchTree(attr, condition, searchTerm.val());
        });
    },

    /**
     * Searches the entire tree and will highlight the nodes that match the condition in green
     */
    searchTree: function(attr, condition, val) {
        d3.selectAll("g.node").classed("searchHighlight", d => {
            var attrVal = d[attr];
            if (typeof attrVal !== "undefined" && attrVal !== null) {
                if (attr === "dist") {
                    switch (condition) {
                        case "greaterEqual":
                            return attrVal >= +val;
                        case "lesserEqual":
                            return attrVal <= +val;
                        default:
                            return;
                    }
                } else if (attr === "name" || attr === "annotation") {
                    return attrVal.toLowerCase().indexOf(val.toLowerCase()) !== -1;
                }
            }
        });
    }
});
