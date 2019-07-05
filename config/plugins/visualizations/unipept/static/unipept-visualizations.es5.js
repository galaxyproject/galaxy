"use strict";

var _typeof2 = typeof Symbol === "function" && typeof Symbol.iterator === "symbol" ? function (obj) { return typeof obj; } : function (obj) { return obj && typeof Symbol === "function" && obj.constructor === Symbol && obj !== Symbol.prototype ? "symbol" : typeof obj; };

/******/(function (modules) {
	// webpackBootstrap
	/******/ // The module cache
	/******/var installedModules = {};
	/******/
	/******/ // The require function
	/******/function __webpack_require__(moduleId) {
		/******/
		/******/ // Check if module is in cache
		/******/if (installedModules[moduleId])
			/******/return installedModules[moduleId].exports;
		/******/
		/******/ // Create a new module (and put it into the cache)
		/******/var module = installedModules[moduleId] = {
			/******/exports: {},
			/******/id: moduleId,
			/******/loaded: false
			/******/ };
		/******/
		/******/ // Execute the module function
		/******/modules[moduleId].call(module.exports, module, module.exports, __webpack_require__);
		/******/
		/******/ // Flag the module as loaded
		/******/module.loaded = true;
		/******/
		/******/ // Return the exports of the module
		/******/return module.exports;
		/******/
	}
	/******/
	/******/
	/******/ // expose the modules object (__webpack_modules__)
	/******/__webpack_require__.m = modules;
	/******/
	/******/ // expose the module cache
	/******/__webpack_require__.c = installedModules;
	/******/
	/******/ // __webpack_public_path__
	/******/__webpack_require__.p = "";
	/******/
	/******/ // Load entry module and return exports
	/******/return __webpack_require__(0);
	/******/
})(
/************************************************************************/
/******/[
/* 0 */
/***/function (module, exports, __webpack_require__) {

	"use strict";

	var _treeview = __webpack_require__(1);

	var _treeview2 = _interopRequireDefault(_treeview);

	var _treemap = __webpack_require__(5);

	var _treemap2 = _interopRequireDefault(_treemap);

	var _sunburst = __webpack_require__(7);

	var _sunburst2 = _interopRequireDefault(_sunburst);

	function _interopRequireDefault(obj) {
		return obj && obj.__esModule ? obj : { default: obj };
	}

	/***/
},
/* 1 */
/***/function (module, exports, __webpack_require__) {

	"use strict";

	Object.defineProperty(exports, "__esModule", {
		value: true
	});

	var _typeof = typeof Symbol === "function" && _typeof2(Symbol.iterator) === "symbol" ? function (obj) {
		return typeof obj === "undefined" ? "undefined" : _typeof2(obj);
	} : function (obj) {
		return obj && typeof Symbol === "function" && obj.constructor === Symbol && obj !== Symbol.prototype ? "symbol" : typeof obj === "undefined" ? "undefined" : _typeof2(obj);
	};

	var _extends = Object.assign || function (target) {
		for (var i = 1; i < arguments.length; i++) {
			var source = arguments[i];for (var key in source) {
				if (Object.prototype.hasOwnProperty.call(source, key)) {
					target[key] = source[key];
				}
			}
		}return target;
	}; /**
     * Zoomable treeview, inspiration from
     * - http://bl.ocks.org/mbostock/4339083
     * - https://gist.github.com/robschmuecker/7880033
     * - http://www.brightpointinc.com/interactive/budget/index.html?source=d3js
     */

	exports.default = TreeView;

	var _univis = __webpack_require__(2);

	var _univis2 = _interopRequireDefault(_univis);

	var _treeviewNode = __webpack_require__(3);

	var _treeviewNode2 = _interopRequireDefault(_treeviewNode);

	function _interopRequireDefault(obj) {
		return obj && obj.__esModule ? obj : { default: obj };
	}

	function TreeView(element, data) {
		var options = arguments.length > 2 && arguments[2] !== undefined ? arguments[2] : {};

		var that = {};

		var MARGIN = {
			top: 5,
			right: 5,
			bottom: 5,
			left: 5
		},
		    DURATION = 750,
		    COLOR_SCALE = d3.scale.category10(),
		    DEFAULTS = {
			height: 300,
			width: 600,
			nodeDistance: 180,
			levelsToExpand: 2,
			minNodeSize: 2,
			maxNodeSize: 105,

			countAccessor: function countAccessor(d) {
				return d.data.count;
			},

			colors: function colors(d) {
				return COLOR_SCALE(d.name);
			},
			nodeFillColor: nodeFillColor,
			nodeStrokeColor: nodeStrokeColor,
			linkStrokeColor: linkStrokeColor,

			enableInnerArcs: true,
			enableExpandOnClick: true,
			enableRightClick: true,

			enableLabels: true,
			getLabel: function getLabel(d) {
				return d.name;
			},

			enableTooltips: true,
			getTooltip: getTooltip,
			getTooltipTitle: _univis2.default.getTooltipTitle,
			getTooltipText: _univis2.default.getTooltipText
		};

		var settings = void 0;

		var visibleRoot = void 0,
		    tooltipTimer = void 0;

		var nodeId = 0,
		    root = void 0;

		var tree = void 0,
		    tooltip = void 0,
		    diagonal = void 0,
		    widthScale = void 0,
		    innerArc = void 0,
		    zoomListener = void 0,
		    svg = void 0;

		function init() {
			settings = _extends({}, DEFAULTS, options);
			_treeviewNode2.default.settings = settings;

			settings.width = settings.width - MARGIN.right - MARGIN.left;
			settings.height = settings.height - MARGIN.top - MARGIN.bottom;

			if (settings.enableTooltips) {
				initTooltip();
			}

			if (settings.enableInnerArcs) {
				initInnerArcs();
			}

			tree = d3.layout.tree().nodeSize([2, 10]).separation(function (a, b) {
				var width = nodeSize(a) + nodeSize(b),
				    distance = width / 2 + 4;
				return a.parent === b.parent ? distance : distance + 4;
			});

			diagonal = d3.svg.diagonal().projection(function (d) {
				return [d.y, d.x];
			});

			widthScale = d3.scale.linear().range([settings.minNodeSize, settings.maxNodeSize]);

			// define the zoomListener which calls the zoom function on the "zoom" event constrained within the scaleExtents
			zoomListener = d3.behavior.zoom().scaleExtent([0.1, 3]).on("zoom", function () {
				svg.attr("transform", "translate(" + d3.event.translate + ")scale(" + d3.event.scale + ")");
			});

			svg = d3.select(element).append("svg").attr("version", "1.1").attr("xmlns", "http://www.w3.org/2000/svg").attr("viewBox", "0 0 " + (settings.width + MARGIN.right + MARGIN.left) + " " + (settings.height + MARGIN.top + MARGIN.bottom)).attr("width", settings.width + MARGIN.right + MARGIN.left).attr("height", settings.height + MARGIN.top + MARGIN.bottom).call(zoomListener).append("g").attr("transform", "translate(" + MARGIN.left + "," + MARGIN.top + ")").append("g");

			draw(_treeviewNode2.default.createNode(data));
		}

		function initTooltip() {
			tooltip = d3.select("body").append("div").attr("id", element.id + "-tooltip").attr("class", "tip").style("position", "absolute").style("z-index", "10").style("visibility", "hidden").style("background-color", "white").style("padding", "2px").style("border", "1px solid #dddddd").style("border-radius", "3px;");
		}

		function initInnerArcs() {
			var arcScale = d3.scale.linear().range([0, 2 * Math.PI]);

			innerArc = d3.svg.arc().outerRadius(nodeSize).startAngle(0).endAngle(function (d) {
				return arcScale(d.data.self_count / d.data.count) || 0;
			});
		}

		function draw(data) {
			var _this = this;

			widthScale.domain([0, data.data.count]);

			root = data;
			root.x0 = settings.height / 2;
			root.y0 = 0;

			// set everything visible
			root.setSelected(true);

			root.children.forEach(function (d, i) {
				d.color = d3.functor(settings.colors).call(_this, d, i);
				d.setRecursiveProperty("color", d.color);
			});

			if (settings.enableExpandOnClick) {
				root.collapseAll();
				root.expand();
			} else {
				root.expandAll();
			}

			update(root);
			centerNode(root);
		}

		function update(source) {
			// Compute the new tree layout.
			var nodes = tree.nodes(root).reverse(),
			    links = tree.links(nodes);

			// Normalize for fixed-depth.
			nodes.forEach(function (d) {
				d.y = d.depth * settings.nodeDistance;
			});

			// Update the nodes…
			var node = svg.selectAll("g.node").data(nodes, function (d) {
				return d.id || (d.id = ++nodeId);
			});

			// Enter any new nodes at the parent's previous position.
			var nodeEnter = node.enter().append("g").attr("class", "node").style("cursor", "pointer").attr("transform", function (d) {
				return "translate(" + (source.y || 0) + "," + (source.x0 || 0) + ")";
			}).on("click", click).on("mouseover", tooltipIn).on("mouseout", tooltipOut).on("contextmenu", rightClick);

			nodeEnter.append("circle").attr("r", 1e-6).style("stroke-width", "1.5px").style("stroke", settings.nodeStrokeColor).style("fill", settings.nodeFillColor);

			if (settings.enableInnerArcs) {
				nodeEnter.append("path").attr("d", innerArc).style("fill", settings.nodeStrokeColor).style("fill-opacity", 0);
			}

			if (settings.enableLabels) {
				nodeEnter.append("text").attr("x", function (d) {
					return d.isLeaf() ? 10 : -10;
				}).attr("dy", ".35em").attr("text-anchor", function (d) {
					return d.isLeaf() ? "start" : "end";
				}).text(settings.getLabel).style("font", "10px sans-serif").style("fill-opacity", 1e-6);
			}

			// Transition nodes to their new position.
			var nodeUpdate = node.transition().duration(DURATION).attr("transform", function (d) {
				return "translate(" + d.y + "," + d.x + ")";
			});

			nodeUpdate.select("circle").attr("r", nodeSize).style("fill-opacity", function (d) {
				return d._children ? 1 : 0;
			}).style("stroke", settings.nodeStrokeColor).style("fill", settings.nodeFillColor);

			if (settings.enableLabels) {
				nodeUpdate.select("text").style("fill-opacity", 1);
			}

			if (settings.enableInnerArcs) {
				nodeUpdate.select("path").duration(DURATION).attr("d", innerArc).style("fill-opacity", 0.8);
			}

			// Transition exiting nodes to the parent's new position.
			var nodeExit = node.exit().transition().duration(DURATION).attr("transform", function (d) {
				return "translate(" + source.y + "," + source.x + ")";
			}).remove();

			nodeExit.select("circle").attr("r", 1e-6);

			nodeExit.select("path").style("fill-opacity", 1e-6);

			nodeExit.select("text").style("fill-opacity", 1e-6);

			// Update the links…
			var link = svg.selectAll("path.link").data(links, function (d) {
				return d.target.id;
			});

			// Enter any new links at the parent's previous position.
			link.enter().insert("path", "g").attr("class", "link").style("fill", "none").style("stroke-opacity", "0.5").style("stroke-linecap", "round").style("stroke", settings.linkStrokeColor).style("stroke-width", 1e-6).attr("d", function (d) {
				var o = {
					x: source.x0 || 0,
					y: source.y0 || 0
				};
				return diagonal({
					source: o,
					target: o
				});
			});

			// Transition links to their new position.
			link.transition().duration(DURATION).attr("d", diagonal).style("stroke", settings.linkStrokeColor).style("stroke-width", function (d) {
				if (d.source.selected) {
					return widthScale(d.target.data.count) + "px";
				} else {
					return "4px";
				}
			});

			// Transition exiting nodes to the parent's new position.
			link.exit().transition().duration(DURATION).style("stroke-width", 1e-6).attr("d", function (d) {
				var o = {
					x: source.x,
					y: source.y
				};
				return diagonal({
					source: o,
					target: o
				});
			}).remove();

			// Stash the old positions for transition.
			nodes.forEach(function (d) {
				var _ref = [d.x, d.y];
				d.x0 = _ref[0];
				d.y0 = _ref[1];
			});
		}

		function nodeSize(d) {
			if (d.selected) {
				return widthScale(d.data.count) / 2;
			} else {
				return 2;
			}
		}

		// Toggle children on click.
		function click(d) {
			if (!settings.enableExpandOnClick) {
				return;
			}

			// check if click is triggered by panning on a node
			if (d3.event.defaultPrevented) {
				return;
			}

			if (d3.event.shiftKey) {
				d.expandAll();
			} else if (d.children) {
				d.collapse();
			} else {
				d.expand();
			}
			update(d);
			centerNode(d);
		}

		function rightClick(d) {
			if (settings.enableRightClick) {
				reroot(d);
			}
		}

		// Sets the width of the right clicked node to 100%
		function reroot(d) {
			if (d === visibleRoot && d !== root) {
				reroot(root);
				return;
			}
			visibleRoot = d;

			// set Selection properties
			root.setSelected(false);
			d.setSelected(true);

			// scale the lines
			widthScale.domain([0, d.data.count]);

			d.expand();

			// redraw
			if (d3.event !== null) {
				d3.event.preventDefault();
			}
			update(d);
			centerNode(d);
		}

		// Center a node
		function centerNode(source) {
			var scale = zoomListener.scale(),
			    x = -source.y0,
			    y = -source.x0;

			x = x * scale + settings.width / 4;
			y = y * scale + settings.height / 2;
			svg.transition().duration(DURATION).attr("transform", "translate(" + x + "," + y + ")scale(" + scale + ")");
			zoomListener.scale(scale);
			zoomListener.translate([x, y]);
		}

		// tooltip functions
		function tooltipIn(d, i) {
			if (!settings.enableTooltips) {
				return;
			}
			tooltip.html(settings.getTooltip(d)).style("top", d3.event.pageY - 5 + "px").style("left", d3.event.pageX + 15 + "px");

			tooltipTimer = setTimeout(function () {
				tooltip.style("visibility", "visible");
			}, 1000);
		}

		function tooltipOut(d, i) {
			if (!settings.enableTooltips) {
				return;
			}
			clearTimeout(tooltipTimer);
			tooltip.style("visibility", "hidden");
		}

		/** ************ Default methods ***************/
		// set fill color
		function nodeFillColor(d) {
			if (d.selected) {
				return d._children ? d.color || "#aaa" : "#fff";
			} else {
				return "#aaa";
			}
		}

		// set node stroke color
		function nodeStrokeColor(d) {
			if (d.selected) {
				return d.color || "#aaa";
			} else {
				return "#aaa";
			}
		}

		// set link stroke color
		function linkStrokeColor(d) {
			if (d.source.selected) {
				return d.target.color;
			} else {
				return "#aaa";
			}
		}

		function getTooltip(d) {
			return "<h3 class='tip-title'>" + settings.getTooltipTitle(d) + "</h3><p>" + settings.getTooltipText(d) + "</p>";
		}

		/** ************* Public methods ***************/
		that.reset = function reset() {
			zoomListener.scale(1);
			reroot(root);
		};

		// initialize the object
		init();

		// return the object
		return that;
	}

	function Plugin(userData, option) {
		return this.each(function () {
			var $this = $(this);
			var data = $this.data("vis.treeview");
			var options = $.extend({}, $this.data(), (typeof option === "undefined" ? "undefined" : _typeof(option)) === "object" && option);

			if (!data) {
				$this.data("vis.treeview", data = new TreeView(this, userData, options));
			}
			if (typeof option === "string") {
				data[option]();
			}
		});
	}

	$.fn.treeview = Plugin;
	$.fn.treeview.Constructor = TreeView;

	/***/
},
/* 2 */
/***/function (module, exports) {

	"use strict";

	Object.defineProperty(exports, "__esModule", {
		value: true
	});

	var _createClass = function () {
		function defineProperties(target, props) {
			for (var i = 0; i < props.length; i++) {
				var descriptor = props[i];descriptor.enumerable = descriptor.enumerable || false;descriptor.configurable = true;if ("value" in descriptor) descriptor.writable = true;Object.defineProperty(target, descriptor.key, descriptor);
			}
		}return function (Constructor, protoProps, staticProps) {
			if (protoProps) defineProperties(Constructor.prototype, protoProps);if (staticProps) defineProperties(Constructor, staticProps);return Constructor;
		};
	}();

	function _classCallCheck(instance, Constructor) {
		if (!(instance instanceof Constructor)) {
			throw new TypeError("Cannot call a class as a function");
		}
	}

	var Univis = function () {
		function Univis() {
			_classCallCheck(this, Univis);
		}

		_createClass(Univis, null, [{
			key: "stringHash",

			/**
    * Hash function for strings from
    * http://stackoverflow.com/a/15710692/865696
    */
			value: function stringHash(s) {
				return s.split("").reduce(function (a, b) {
					var c = (a << 5) - a + b.charCodeAt(0);
					return c & c;
				}, 0);
			}

			/*
    * Returns the readable text color based on the brightness of a given backgroud color
    */

		}, {
			key: "getReadableColorFor",
			value: function getReadableColorFor(color) {
				var textColor = "#000";
				try {
					textColor = Univis.brightness(d3.rgb(color)) < 125 ? "#eee" : "#000";
				} catch (err) {/* go on */}
				return textColor;
			}

			/*
    * Returns the brightness of an rgb-color
    * from: http:// www.w3.org/WAI/ER/WD-AERT/#color-contrast
    */

		}, {
			key: "brightness",
			value: function brightness(rgb) {
				return rgb.r * 0.299 + rgb.g * 0.587 + rgb.b * 0.114;
			}
		}, {
			key: "getTooltipTitle",
			value: function getTooltipTitle(d) {
				return d.name;
			}
		}, {
			key: "getTooltipText",
			value: function getTooltipText(d) {
				return d.data.count + " hits";
			}
		}]);

		return Univis;
	}();

	exports.default = Univis;

	/***/
},
/* 3 */
/***/function (module, exports, __webpack_require__) {

	"use strict";

	Object.defineProperty(exports, "__esModule", {
		value: true
	});

	var _createClass = function () {
		function defineProperties(target, props) {
			for (var i = 0; i < props.length; i++) {
				var descriptor = props[i];descriptor.enumerable = descriptor.enumerable || false;descriptor.configurable = true;if ("value" in descriptor) descriptor.writable = true;Object.defineProperty(target, descriptor.key, descriptor);
			}
		}return function (Constructor, protoProps, staticProps) {
			if (protoProps) defineProperties(Constructor.prototype, protoProps);if (staticProps) defineProperties(Constructor, staticProps);return Constructor;
		};
	}();

	var _node = __webpack_require__(4);

	var _node2 = _interopRequireDefault(_node);

	function _interopRequireDefault(obj) {
		return obj && obj.__esModule ? obj : { default: obj };
	}

	function _classCallCheck(instance, Constructor) {
		if (!(instance instanceof Constructor)) {
			throw new TypeError("Cannot call a class as a function");
		}
	}

	function _possibleConstructorReturn(self, call) {
		if (!self) {
			throw new ReferenceError("this hasn't been initialised - super() hasn't been called");
		}return call && ((typeof call === "undefined" ? "undefined" : _typeof2(call)) === "object" || typeof call === "function") ? call : self;
	}

	function _inherits(subClass, superClass) {
		if (typeof superClass !== "function" && superClass !== null) {
			throw new TypeError("Super expression must either be null or a function, not " + (typeof superClass === "undefined" ? "undefined" : _typeof2(superClass)));
		}subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, enumerable: false, writable: true, configurable: true } });if (superClass) Object.setPrototypeOf ? Object.setPrototypeOf(subClass, superClass) : subClass.__proto__ = superClass;
	}

	var TreeviewNode = function (_Node) {
		_inherits(TreeviewNode, _Node);

		function TreeviewNode() {
			var node = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : {};

			_classCallCheck(this, TreeviewNode);

			var _this = _possibleConstructorReturn(this, (TreeviewNode.__proto__ || Object.getPrototypeOf(TreeviewNode)).call(this, node));

			_this.settings = TreeviewNode.settings;
			_this.setCount();
			return _this;
		}

		_createClass(TreeviewNode, [{
			key: "setCount",
			value: function setCount() {
				if (this.settings.countAccessor(this)) {
					this.data.count = this.settings.countAccessor(this);
				} else if (this.children) {
					this.data.count = this.children.reduce(function (sum, c) {
						return sum + c.data.count;
					}, 0);
				} else {
					this.data.count = 0;
				}
			}
		}, {
			key: "setSelected",
			value: function setSelected(value) {
				this.setRecursiveProperty("selected", value);
			}

			// collapse everything

		}, {
			key: "collapseAll",
			value: function collapseAll() {
				if (this.children && this.children.length === 0) {
					this.children = null;
				}
				if (this.children) {
					this._children = this.children;
					this._children.forEach(function (c) {
						c.collapseAll();
					});
					this.children = null;
				}
			}

			// Collapses a node

		}, {
			key: "collapse",
			value: function collapse() {
				if (this.children) {
					this._children = this.children;
					this.children = null;
				}
			}
		}, {
			key: "expandAll",
			value: function expandAll() {
				this.expand(100);
			}

			// Expands a node and its children

		}, {
			key: "expand",
			value: function expand() {
				var i = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : this.settings.levelsToExpand;

				if (i > 0) {
					if (this._children) {
						this.children = this._children;
						this._children = null;
					}
					if (this.children) {
						this.children.forEach(function (c) {
							c.expand(i - 1);
						});
					}
				}
			}
		}], [{
			key: "new",
			value: function _new() {
				var node = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : {};

				return new TreeviewNode(node);
			}
		}, {
			key: "createNode",
			value: function createNode(node) {
				return _node2.default.createNode(node, TreeviewNode.new);
			}
		}]);

		return TreeviewNode;
	}(_node2.default);

	exports.default = TreeviewNode;

	/***/
},
/* 4 */
/***/function (module, exports) {

	"use strict";

	Object.defineProperty(exports, "__esModule", {
		value: true
	});

	var _extends = Object.assign || function (target) {
		for (var i = 1; i < arguments.length; i++) {
			var source = arguments[i];for (var key in source) {
				if (Object.prototype.hasOwnProperty.call(source, key)) {
					target[key] = source[key];
				}
			}
		}return target;
	};

	var _createClass = function () {
		function defineProperties(target, props) {
			for (var i = 0; i < props.length; i++) {
				var descriptor = props[i];descriptor.enumerable = descriptor.enumerable || false;descriptor.configurable = true;if ("value" in descriptor) descriptor.writable = true;Object.defineProperty(target, descriptor.key, descriptor);
			}
		}return function (Constructor, protoProps, staticProps) {
			if (protoProps) defineProperties(Constructor.prototype, protoProps);if (staticProps) defineProperties(Constructor, staticProps);return Constructor;
		};
	}();

	function _classCallCheck(instance, Constructor) {
		if (!(instance instanceof Constructor)) {
			throw new TypeError("Cannot call a class as a function");
		}
	}

	var Node = function () {
		function Node() {
			var node = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : {};

			_classCallCheck(this, Node);

			this.data = {};
			_extends(this, node);
		}

		_createClass(Node, [{
			key: "setRecursiveProperty",

			// sets a property for a node and all its children
			value: function setRecursiveProperty(property, value) {
				this[property] = value;
				if (this.children) {
					this.children.forEach(function (c) {
						c.setRecursiveProperty(property, value);
					});
				} else if (this._children) {
					this._children.forEach(function (c) {
						c.setRecursiveProperty(property, value);
					});
				}
			}

			// Returns true if a node is a leaf

		}, {
			key: "isLeaf",
			value: function isLeaf() {
				return !this.children && !this._children || this.children && this.children.length === 0 || this._children && this._children.length === 0;
			}
		}, {
			key: "getHeight",
			value: function getHeight() {
				if (this._height === undefined) {
					if (this.isLeaf()) {
						this._height = 0;
					} else {
						this._height = d3.max(this.children, function (c) {
							return c.getHeight();
						}) + 1;
					}
				}
				return this._height;
			}
		}, {
			key: "getDepth",
			value: function getDepth() {
				if (this._depth === undefined) {
					if (this.parent === undefined) {
						this._depth = 0;
					} else {
						this._depth = this.parent.getDepth() + 1;
					}
				}
				return this._depth;
			}
		}], [{
			key: "new",
			value: function _new() {
				var node = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : {};

				return new Node(node);
			}
		}, {
			key: "createNode",
			value: function createNode(node) {
				var construct = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : Node.new;

				if (node.children) {
					node.children = node.children.map(function (n) {
						return Node.createNode(n, construct);
					});
				}
				return construct.call(null, node);
			}
		}]);

		return Node;
	}();

	exports.default = Node;

	/***/
},
/* 5 */
/***/function (module, exports, __webpack_require__) {

	"use strict";

	Object.defineProperty(exports, "__esModule", {
		value: true
	});

	var _typeof = typeof Symbol === "function" && _typeof2(Symbol.iterator) === "symbol" ? function (obj) {
		return typeof obj === "undefined" ? "undefined" : _typeof2(obj);
	} : function (obj) {
		return obj && typeof Symbol === "function" && obj.constructor === Symbol && obj !== Symbol.prototype ? "symbol" : typeof obj === "undefined" ? "undefined" : _typeof2(obj);
	};

	var _extends = Object.assign || function (target) {
		for (var i = 1; i < arguments.length; i++) {
			var source = arguments[i];for (var key in source) {
				if (Object.prototype.hasOwnProperty.call(source, key)) {
					target[key] = source[key];
				}
			}
		}return target;
	}; /**
     * Interactive treemap
     */

	exports.default = TreeMap;

	var _univis = __webpack_require__(2);

	var _univis2 = _interopRequireDefault(_univis);

	var _treemapNode = __webpack_require__(6);

	var _treemapNode2 = _interopRequireDefault(_treemapNode);

	function _interopRequireDefault(obj) {
		return obj && obj.__esModule ? obj : { default: obj };
	}

	function TreeMap(element, data) {
		var options = arguments.length > 2 && arguments[2] !== undefined ? arguments[2] : {};

		var that = {};

		var MARGIN = {
			top: 0,
			right: 0,
			bottom: 0,
			left: 0
		},
		    DEFAULTS = {
			height: 300,
			width: 600,

			className: "unipept-treemap",
			levels: undefined,
			getLevel: function getLevel(d) {
				return d.getDepth();
			},

			countAccessor: function countAccessor(d) {
				return d.data.self_count;
			},
			rerootCallback: undefined,

			getBreadcrumbTooltip: function getBreadcrumbTooltip(d) {
				return d.name;
			},
			colorRoot: "#104B7D",
			colorLeaf: "#fdffcc",
			colorBreadcrumbs: "#FF8F00",

			labelHeight: 10,
			getLabel: function getLabel(d) {
				return d.name;
			},

			enableTooltips: true,
			getTooltip: getTooltip,
			getTooltipTitle: _univis2.default.getTooltipTitle,
			getTooltipText: _univis2.default.getTooltipText
		};

		var settings = void 0;

		var root = void 0,
		    nodeId = 0,
		    current = void 0,
		    treemapLayout = void 0,
		    breadcrumbs = void 0,
		    treemap = void 0,
		    tooltip = void 0,
		    colorScale = void 0;

		/**
   * Initializes Treemap
   */
		function init() {
			settings = _extends({}, DEFAULTS, options);

			root = _treemapNode2.default.createNode(data);

			settings.width = settings.width - MARGIN.right - MARGIN.left;
			settings.height = settings.height - MARGIN.top - MARGIN.bottom;

			settings.levels = settings.levels || root.getHeight();

			if (settings.enableTooltips) {
				initTooltip();
			}

			initCSS();

			// setup the visualisation
			draw(root);
			reroot(root, false);
		}

		function initTooltip() {
			tooltip = d3.select("body").append("div").attr("id", element.id + "-tooltip").attr("class", "tip").style("position", "absolute").style("z-index", "10").style("visibility", "hidden").style("background-color", "white").style("padding", "2px").style("border", "1px solid #dddddd").style("border-radius", "3px;");
		}

		function initCSS() {
			var elementClass = settings.className;
			$(element).addClass(elementClass);
			$("<style>").prop("type", "text/css").html("\n                    ." + elementClass + " {\n                        font-family: Roboto,'Helvetica Neue',Helvetica,Arial,sans-serif;\n                    }\n                    ." + elementClass + " .node {\n                        font-size: 9px;\n                        line-height: 10px;\n                        overflow: hidden;\n                        position: absolute;\n                        text-indent: 2px;\n                        text-align: center;\n                        text-overflow: ellipsis;\n                        cursor: pointer;\n                    }\n                    ." + elementClass + " .node:hover {\n                        outline: 1px solid white;\n                    }\n                    ." + elementClass + " .breadcrumbs {\n                        font-size: 11px;\n                        line-height: 20px;\n                        padding-left: 5px;\n                        font-weight: bold;\n                        color: white;\n                        box-sizing: border-box;\n                    }\n                    .full-screen ." + elementClass + " .breadcrumbs {\n                        width: 100% !important;\n                    }\n                    ." + elementClass + " .crumb {\n                        cursor: pointer;\n                    }\n                    ." + elementClass + " .crumb .link:hover {\n                        text-decoration: underline;\n                    }\n                    ." + elementClass + " .breadcrumbs .crumb + .crumb::before {\n                        content: \" > \";\n                        cursor: default;\n                    }\n                ").appendTo("head");
		}

		function draw(data) {
			$(element).empty();

			treemapLayout = d3.layout.treemap().size([settings.width + 1, settings.height + 1]).padding([settings.labelHeight, 0, 0, 0]).value(settings.countAccessor);

			colorScale = d3.scale.linear().domain([0, settings.levels]).range([settings.colorRoot, settings.colorLeaf]).interpolate(d3.interpolateLab);

			breadcrumbs = d3.select(element).append("div").attr("class", "breadcrumbs").style("position", "relative").style("width", settings.width + "px").style("height", "20px").style("background-color", settings.colorBreadcrumbs);

			treemap = d3.select(element).append("div").style("position", "relative").style("width", settings.width + "px").style("height", settings.height + "px").style("left", MARGIN.left + "px").style("top", MARGIN.top + "px");
		}

		function setBreadcrumbs() {
			var crumbs = [];
			var temp = current;
			while (temp) {
				crumbs.push(temp);
				temp = temp.parent;
			}
			crumbs.reverse();
			breadcrumbs.html("");
			breadcrumbs.selectAll(".crumb").data(crumbs).enter().append("span").attr("class", "crumb").attr("title", settings.getBreadcrumbTooltip).html(function (d) {
				return "<span class='link'>" + d.name + "</span>";
			}).on("click", function (d) {
				reroot(d);
			});
		}

		function reroot(data) {
			var triggerCallback = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : true;

			current = data;

			setBreadcrumbs();

			var nodes = treemap.selectAll(".node").data(treemapLayout.nodes(data), function (d) {
				return d.id || (d.id = ++nodeId);
			});

			nodes.enter().append("div").attr("class", "node").style("background", function (d) {
				return colorScale(settings.getLevel(d));
			}).style("color", function (d) {
				return _univis2.default.getReadableColorFor(colorScale(settings.getLevel(d)));
			}).style("left", "0px").style("top", "0px").style("width", "0px").style("height", "0px").text(settings.getLabel).on("click", function (d) {
				reroot(d);
			}).on("contextmenu", function (d) {
				d3.event.preventDefault();
				if (current.parent) {
					reroot(current.parent);
				}
			}).on("mouseover", tooltipIn).on("mousemove", tooltipMove).on("mouseout", tooltipOut);

			nodes.order().transition().call(position);

			nodes.exit().remove();

			if (triggerCallback && settings.rerootCallback) {
				settings.rerootCallback.call(null, current);
			}
		}

		function update() {
			var nodes = treemap.selectAll(".node").data(treemapLayout.nodes(data), function (d) {
				return d.id;
			}).order().transition().call(position);
		}

		/**
   * sets the position of a square
   */
		function position() {
			this.style("left", function (d) {
				return d.x + "px";
			}).style("top", function (d) {
				return d.y + "px";
			}).style("width", function (d) {
				return Math.max(0, d.dx - 1) + "px";
			}).style("height", function (d) {
				return Math.max(0, d.dy - 1) + "px";
			});
		}

		/**
   * Resizes the treemap for a given width and height
   */
		function resize(width, height) {
			treemapLayout = d3.layout.treemap().size([width + 1, height + 1]).padding([10, 0, 0, 0]).value(settings.countAccessor);
			update();
		}

		// tooltip functions
		function tooltipIn(d, i) {
			if (!settings.enableTooltips) {
				return;
			}
			tooltip.html(settings.getTooltip(d)).style("top", d3.event.pageY - 5 + "px").style("left", d3.event.pageX + 15 + "px").style("visibility", "visible");
		}

		function tooltipOut(d, i) {
			if (!settings.enableTooltips) {
				return;
			}
			tooltip.style("visibility", "hidden");
		}

		function tooltipMove(d, i) {
			if (!settings.enableTooltips) {
				return;
			}
			tooltip.style("top", d3.event.pageY - 5 + "px").style("left", d3.event.pageX + 15 + "px");
		}

		function getTooltip(d) {
			return "<h3 class='tip-title'>" + settings.getTooltipTitle(d) + "</h3><p>" + settings.getTooltipText(d) + "</p>";
		}

		/** ************* Public methods ***************/
		/**
   * Resets the treemap to its initial position
   */
		that.reset = function reset() {
			reroot(root);
		};

		/**
   * Sets the visualisation in full screen mode
   *
   * @param <boolean> isFullScreen indicates if we're in full screen mode
   */
		that.setFullScreen = function setFullScreen(isFullScreen) {
			// the delay is because the event fires before we're in fullscreen
			// so the height en width functions don't give a correct result
			// without the delay
			setTimeout(function () {
				var _ref = [settings.width, settings.height],
				    w = _ref[0],
				    h = _ref[1];

				if (isFullScreen) {
					w = $(window).width();
					h = $(window).height() - 44;
				}
				resize(w, h);
			}, 1000);
		};

		// initialize the object
		init();

		return that;
	}

	function Plugin(userData, option) {
		return this.each(function () {
			var $this = $(this);
			var data = $this.data("vis.treemap");
			var options = $.extend({}, $this.data(), (typeof option === "undefined" ? "undefined" : _typeof(option)) === "object" && option);

			if (!data) {
				$this.data("vis.treemap", data = new TreeMap(this, userData, options));
			}
			if (typeof option === "string") {
				data[option]();
			}
		});
	}

	$.fn.treemap = Plugin;
	$.fn.treemap.Constructor = TreeMap;

	/***/
},
/* 6 */
/***/function (module, exports, __webpack_require__) {

	"use strict";

	Object.defineProperty(exports, "__esModule", {
		value: true
	});

	var _createClass = function () {
		function defineProperties(target, props) {
			for (var i = 0; i < props.length; i++) {
				var descriptor = props[i];descriptor.enumerable = descriptor.enumerable || false;descriptor.configurable = true;if ("value" in descriptor) descriptor.writable = true;Object.defineProperty(target, descriptor.key, descriptor);
			}
		}return function (Constructor, protoProps, staticProps) {
			if (protoProps) defineProperties(Constructor.prototype, protoProps);if (staticProps) defineProperties(Constructor, staticProps);return Constructor;
		};
	}();

	var _node = __webpack_require__(4);

	var _node2 = _interopRequireDefault(_node);

	function _interopRequireDefault(obj) {
		return obj && obj.__esModule ? obj : { default: obj };
	}

	function _classCallCheck(instance, Constructor) {
		if (!(instance instanceof Constructor)) {
			throw new TypeError("Cannot call a class as a function");
		}
	}

	function _possibleConstructorReturn(self, call) {
		if (!self) {
			throw new ReferenceError("this hasn't been initialised - super() hasn't been called");
		}return call && ((typeof call === "undefined" ? "undefined" : _typeof2(call)) === "object" || typeof call === "function") ? call : self;
	}

	function _inherits(subClass, superClass) {
		if (typeof superClass !== "function" && superClass !== null) {
			throw new TypeError("Super expression must either be null or a function, not " + (typeof superClass === "undefined" ? "undefined" : _typeof2(superClass)));
		}subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, enumerable: false, writable: true, configurable: true } });if (superClass) Object.setPrototypeOf ? Object.setPrototypeOf(subClass, superClass) : subClass.__proto__ = superClass;
	}

	var TreemapNode = function (_Node) {
		_inherits(TreemapNode, _Node);

		function TreemapNode() {
			_classCallCheck(this, TreemapNode);

			return _possibleConstructorReturn(this, (TreemapNode.__proto__ || Object.getPrototypeOf(TreemapNode)).apply(this, arguments));
		}

		_createClass(TreemapNode, null, [{
			key: "new",
			value: function _new() {
				var node = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : {};

				return new TreemapNode(node);
			}
		}, {
			key: "createNode",
			value: function createNode(node) {
				return _node2.default.createNode(node, TreemapNode.new);
			}
		}]);

		return TreemapNode;
	}(_node2.default);

	exports.default = TreemapNode;

	/***/
},
/* 7 */
/***/function (module, exports, __webpack_require__) {

	"use strict";

	Object.defineProperty(exports, "__esModule", {
		value: true
	});

	var _typeof = typeof Symbol === "function" && _typeof2(Symbol.iterator) === "symbol" ? function (obj) {
		return typeof obj === "undefined" ? "undefined" : _typeof2(obj);
	} : function (obj) {
		return obj && typeof Symbol === "function" && obj.constructor === Symbol && obj !== Symbol.prototype ? "symbol" : typeof obj === "undefined" ? "undefined" : _typeof2(obj);
	};

	var _extends = Object.assign || function (target) {
		for (var i = 1; i < arguments.length; i++) {
			var source = arguments[i];for (var key in source) {
				if (Object.prototype.hasOwnProperty.call(source, key)) {
					target[key] = source[key];
				}
			}
		}return target;
	};

	var _createClass = function () {
		function defineProperties(target, props) {
			for (var i = 0; i < props.length; i++) {
				var descriptor = props[i];descriptor.enumerable = descriptor.enumerable || false;descriptor.configurable = true;if ("value" in descriptor) descriptor.writable = true;Object.defineProperty(target, descriptor.key, descriptor);
			}
		}return function (Constructor, protoProps, staticProps) {
			if (protoProps) defineProperties(Constructor.prototype, protoProps);if (staticProps) defineProperties(Constructor, staticProps);return Constructor;
		};
	}(); /**
       * Interactive Sunburst
       */

	var _univis = __webpack_require__(2);

	var _univis2 = _interopRequireDefault(_univis);

	var _sunburstNode = __webpack_require__(8);

	var _sunburstNode2 = _interopRequireDefault(_sunburstNode);

	function _interopRequireDefault(obj) {
		return obj && obj.__esModule ? obj : { default: obj };
	}

	function _toConsumableArray(arr) {
		if (Array.isArray(arr)) {
			for (var i = 0, arr2 = Array(arr.length); i < arr.length; i++) {
				arr2[i] = arr[i];
			}return arr2;
		} else {
			return Array.from(arr);
		}
	}

	function _classCallCheck(instance, Constructor) {
		if (!(instance instanceof Constructor)) {
			throw new TypeError("Cannot call a class as a function");
		}
	}

	var Sunburst = function () {
		function Sunburst(element, data) {
			var _this = this;

			var options = arguments.length > 2 && arguments[2] !== undefined ? arguments[2] : {};

			_classCallCheck(this, Sunburst);

			this.element = element;
			this.data = data;
			this.settings = _extends({}, Sunburst.DEFAULTS, options);

			this.settings.width = this.settings.width - Sunburst.MARGIN.right - Sunburst.MARGIN.left;
			this.settings.height = this.settings.height - Sunburst.MARGIN.top - Sunburst.MARGIN.bottom;

			this.colorCounter = -1;

			// prepare data
			this.data.children = this.addEmptyChildren(this.data.children, this.settings.countAccessor.call(null, this.data));

			if (this.settings.enableTooltips) {
				this.initTooltip();
			}

			this.initCSS();

			// draw everything
			this.redraw();

			// fake click on the center node
			setTimeout(function () {
				return _this.reset();
			}, 1000);
		}

		_createClass(Sunburst, [{
			key: "initTooltip",
			value: function initTooltip() {
				this.tooltip = d3.select("body").append("div").attr("id", this.element.id + "-tooltip").attr("class", "tip").style("position", "absolute").style("z-index", "10").style("visibility", "hidden").style("background-color", "white").style("padding", "2px").style("border", "1px solid #dddddd").style("border-radius", "3px;");
			}
		}, {
			key: "initCSS",
			value: function initCSS() {
				var elementClass = this.settings.className;
				$(this.element).addClass(elementClass);
				$("<style>").prop("type", "text/css").html("\n." + elementClass + " {\n    font-family: Roboto,'Helvetica Neue',Helvetica,Arial,sans-serif;\n    width: " + (this.settings.width + this.settings.breadcrumbWidth) + "px;\n}\n." + elementClass + " .sunburst-breadcrumbs {\n    width: 176px;\n    float: right;\n    margin-top: 10px;\n    padding-left: 5px;\n}\n." + elementClass + " .sunburst-breadcrumbs ul {\n    padding-left: 0;\n    list-style: none;\n}\n." + elementClass + " .sunburst-breadcrumbs .crumb {\n    margin-bottom: 5px;\n    cursor: pointer;\n}\n." + elementClass + " .sunburst-breadcrumbs .crumb svg {\n    float: left;\n    margin-right: 3px;\n}\n." + elementClass + " .sunburst-breadcrumbs .crumb p {\n    white-space: nowrap;\n    text-overflow: ellipsis;\n    overflow: hidden;\n    margin: 0;\n    font-size: 14px;\n}\n." + elementClass + " .sunburst-breadcrumbs .crumb .percentage {\n    font-size: 11px;\n}").appendTo("head");
			}

			/** ****** private functions ********/
			/**
    * Adds data for the peptides on the self level
    * Is called recursively
    *
    * @param <Array> children A list of children
    * @param <int> count The number of peptides that should be the sum of the
    *          children count
    * @return <Array> The modified list of children
    */

		}, {
			key: "addEmptyChildren",
			value: function addEmptyChildren(children, count) {
				for (var i = 0; i < children.length; i++) {
					if (typeof children[i].children !== "undefined") {
						children[i].children = this.addEmptyChildren(children[i].children, this.settings.countAccessor.call(null, children[i]));
					}
				}
				if (children.length > 0 && count !== 0 && count !== undefined) {
					children.push({
						id: -1,
						name: "empty",
						data: {
							count: count,
							self_count: count
						}
					});
				}
				return children;
			}

			/**
    * Redraws the pancore graph
    */

		}, {
			key: "redraw",
			value: function redraw() {
				var _this2 = this;

				// clear everything
				$(this.element).empty();

				this.breadcrumbs = d3.select(this.element).append("div").attr("id", this.element.id + "-breadcrumbs").attr("class", "sunburst-breadcrumbs").append("ul");

				this.x = d3.scale.linear().range([0, 2 * Math.PI]); // use full circle
				this.y = d3.scale.linear().domain([0, 1]).range([0, this.settings.radius]);
				this.currentMaxLevel = 4;

				var vis = d3.select(this.element).append("svg").attr("version", "1.1").attr("xmlns", "http://www.w3.org/2000/svg").attr("viewBox", "0 0 " + (this.settings.width + Sunburst.MARGIN.right + Sunburst.MARGIN.left) + " " + (this.settings.height + Sunburst.MARGIN.top + Sunburst.MARGIN.bottom)).attr("width", this.settings.width + Sunburst.MARGIN.right + Sunburst.MARGIN.left).attr("height", this.settings.height + Sunburst.MARGIN.top + Sunburst.MARGIN.bottom).attr("overflow", "hidden").style("font-family", "'Helvetica Neue', Helvetica, Arial, sans-serif");
				vis.append("style").attr("type", "text/css").html(".hidden{ visibility: hidden;}");
				vis = vis.append("g").attr("transform", "translate(" + this.settings.radius + "," + this.settings.radius + ")"); // set origin to radius center

				var partition = d3.layout.partition() // creates a new partition layout
				.sort(null) // don't sort,  use tree traversal order
				.value(this.settings.countAccessor); // set the size of the pieces

				// calculate arcs out of partition coordinates
				this.arc = d3.svg.arc().startAngle(function (d) {
					return Math.max(0, Math.min(2 * Math.PI, _this2.x(d.x)));
				}).endAngle(function (d) {
					return Math.max(0, Math.min(2 * Math.PI, _this2.x(d.x + d.dx)));
				})
				// prevent y-calculation on 0
				.innerRadius(function (d) {
					return Math.max(0, d.y ? _this2.y(d.y) : d.y);
				}).outerRadius(function (d) {
					return Math.max(0, _this2.y(d.y + d.dy)) + 1;
				});

				// run the partition layout
				var nodes = partition.nodes(this.data);

				this.path = vis.selectAll("path").data(nodes);
				this.path.enter().append("path") // for every node, draw an arc
				.attr("class", "arc").attr("id", function (d, i) {
					return "path-" + i;
				}) // id based on index
				.attr("d", this.arc) // path data
				.attr("fill-rule", "evenodd") // fill rule
				.style("fill", function (d) {
					return _this2.colour(d, _this2);
				}) // call function for colour
				.on("click", function (d) {
					if (d.depth < _this2.currentMaxLevel) {
						_this2.click(d);
					}
				}) // call function on click
				.on("mouseover", function (d, i) {
					return _this2.tooltipIn(d, i);
				}).on("mousemove", function (d, i) {
					return _this2.tooltipMove(d, i);
				}).on("mouseout", function (d, i) {
					return _this2.tooltipOut(d, i);
				});

				// put labels on the nodes
				this.text = vis.selectAll("text").data(nodes);

				// hack for the getComputedTextLength
				var that = this;

				this.text.enter().append("text").style("fill", function (d) {
					return _univis2.default.getReadableColorFor(_this2.colour(d, _this2));
				}).style("fill-opacity", 0).style("font-family", "font-family: Helvetica, 'Super Sans', sans-serif").style("pointer-events", "none") // don't invoke mouse events
				.attr("dy", ".2em").text(this.settings.getLabel).style("font-size", function (d) {
					return Math.floor(Math.min(that.settings.radius / that.settings.levels / this.getComputedTextLength() * 10 + 1, 12)) + "px";
				});
			}

			/**
    *  Interpolate the scales!
    * Defines new scales based on the clicked item
    *
    * @param <Object> d The clicked item
    * @return <Scale> new scales
    */

		}, {
			key: "arcTween",
			value: function arcTween(d, that) {
				var my = Math.min(Sunburst.maxY(d), d.y + that.settings.levels * d.dy),
				    xd = d3.interpolate(that.x.domain(), [d.x, d.x + d.dx]),
				    yd = d3.interpolate(that.y.domain(), [d.y, my]),
				    yr = d3.interpolate(that.y.range(), [d.y ? 20 : 0, that.settings.radius]);
				return function (d) {
					return function (t) {
						that.x.domain(xd(t));
						that.y.domain(yd(t)).range(yr(t));
						return that.arc(d);
					};
				};
			}
		}, {
			key: "setBreadcrumbs",
			value: function setBreadcrumbs(d) {
				var _this3 = this;

				// breadcrumbs
				var crumbs = [];
				var temp = d;
				while (temp) {
					crumbs.push(temp);
					temp = temp.parent;
				}
				crumbs.reverse().shift();
				var breadArc = d3.svg.arc().innerRadius(0).outerRadius(15).startAngle(0).endAngle(function (d) {
					return 2 * Math.PI * d.data.count / d.parent.data.count;
				});
				var bc = this.breadcrumbs.selectAll(".crumb").data(crumbs);
				bc.enter().append("li").on("click", function (d) {
					_this3.click(d.parent);
				}).attr("class", "crumb").style("opacity", "0").attr("title", function (d) {
					return "[" + d.data.rank + "] " + d.name;
				}).html(function (d) {
					return "\n<p class='name'>" + d.name + "</p>\n<p class='percentage'>" + Math.round(100 * d.data.count / d.parent.data.count) + "% of " + d.parent.name + "</p>";
				}).insert("svg", ":first-child").attr("width", 30).attr("height", 30).append("path").attr("d", breadArc).attr("transform", "translate(15, 15)").attr("fill", function (d) {
					return _this3.colour(d, _this3);
				});
				bc.transition().duration(this.settings.duration).style("opacity", "1");
				bc.exit().transition().duration(this.settings.duration).style("opacity", "0").remove();
			}

			/**
    * Defines what happens after a node is clicked
    *
    * @param <Object> d The data object of the clicked arc
    */

		}, {
			key: "click",
			value: function click(d) {
				var _this4 = this;

				if (d.name === "empty") {
					return;
				}

				this.setBreadcrumbs(d);

				if (this.settings.rerootCallback) {
					this.settings.rerootCallback.call(null, d);
				}

				// perform animation
				this.currentMaxLevel = d.depth + this.settings.levels;
				this.path.transition().duration(this.settings.duration).attrTween("d", this.arcTween(d, this)).attr("class", function (d) {
					return d.depth >= _this4.currentMaxLevel ? "arc toHide" : "arc";
				}).attr("fill-opacity", function (d) {
					return d.depth >= _this4.currentMaxLevel ? 0.2 : 1;
				});

				var that = this;

				// Somewhat of a hack as we rely on arcTween updating the scales.
				this.text.style("visibility", function (e) {
					return Sunburst.isParentOf(d, e, that.currentMaxLevel) ? null : d3.select(this).style("visibility");
				}).transition().duration(this.settings.duration).attrTween("text-anchor", function (d) {
					return function () {
						return that.x(d.x + d.dx / 2) > Math.PI ? "end" : "start";
					};
				}).attrTween("dx", function (d) {
					return function () {
						return that.x(d.x + d.dx / 2) > Math.PI ? "-4px" : "4px";
					};
				}).attrTween("transform", function (d) {
					return function () {
						var angle = that.x(d.x + d.dx / 2) * 180 / Math.PI - 90;
						return "rotate(" + angle + ")translate(" + that.y(d.y) + ")rotate(" + (angle > 90 ? -180 : 0) + ")";
					};
				}).style("fill-opacity", function (e) {
					return Sunburst.isParentOf(d, e, that.currentMaxLevel) ? 1 : 1e-6;
				}).each("end", function (e) {
					d3.select(this).style("visibility", Sunburst.isParentOf(d, e, that.currentMaxLevel) ? null : "hidden");
				});
			}

			/**
    * Calculates the color of an arc based on the color of his children
    *
    * @param <Object> d The node for which we want the color
    * @return <Color> The calculated color
    */

		}, {
			key: "colour",
			value: function colour(d, that) {
				if (d.name === "empty") {
					return "white";
				}
				if (that.settings.useFixedColors) {
					return that.settings.fixedColors[Math.abs(_univis2.default.stringHash(d.name + " " + d.data.rank)) % that.settings.fixedColors.length];
				} else {
					if (d.children) {
						var colours = d.children.map(function (c) {
							return that.colour(c, that);
						}),
						    a = d3.hsl(colours[0]),
						    b = d3.hsl(colours[1]),
						    singleChild = d.children.length === 1 || d.children[1].name === "empty";
						// if we only have one child, return a slightly darker variant of the child color
						if (singleChild) {
							return d3.hsl(a.h, a.s, a.l * 0.98);
						}
						// if we have 2 children or more, take the average of the first two children
						return d3.hsl((a.h + b.h) / 2, (a.s + b.s) / 2, (a.l + b.l) / 2);
					}
					// if we don't have children, pick a new color
					if (!d.color) {
						d.color = that.getColor();
					}
					return d.color;
				}
			}

			/**
    * color generation function
    * iterates over fixed list of colors
    *
    * @return <Color> The generated color
    */

		}, {
			key: "getColor",
			value: function getColor() {
				this.colorCounter = (this.colorCounter + 1) % this.settings.colors.length;
				return this.settings.colors[this.colorCounter];
			}

			// tooltip functions

		}, {
			key: "tooltipIn",
			value: function tooltipIn(d, i) {
				if (!this.settings.enableTooltips) {
					return;
				}
				if (d.depth < this.currentMaxLevel && d.name !== "empty") {
					this.tooltip.html(this.settings.getTooltip(d)).style("top", d3.event.pageY - 5 + "px").style("left", d3.event.pageX + 15 + "px").style("visibility", "visible");
				}
			}
		}, {
			key: "tooltipOut",
			value: function tooltipOut(d, i) {
				if (!this.settings.enableTooltips) {
					return;
				}
				this.tooltip.style("visibility", "hidden");
			}
		}, {
			key: "tooltipMove",
			value: function tooltipMove(d, i) {
				if (!this.settings.enableTooltips) {
					return;
				}
				this.tooltip.style("top", d3.event.pageY - 5 + "px").style("left", d3.event.pageX + 15 + "px");
			}
		}, {
			key: "getTooltip",
			value: function getTooltip(d) {
				return "<h3 class='tip-title'>" + this.settings.getTooltipTitle(d) + "</h3><p>" + this.settings.getTooltipText(d) + "</p>";
			}

			/** ****** util methods *************/
			/**
    * Calculates if p is a parent of c
    * Returns true is label must be drawn
    */

		}, {
			key: "reset",

			/** ************* Public methods ***************/

			/**
    * Resets the sunburst to its initial position
    */
			value: function reset() {
				this.click(this.data);
			}

			/**
    * redraws the colors of the sunburst
    */

		}, {
			key: "redrawColors",
			value: function redrawColors() {
				var _this5 = this;

				d3.selectAll(".crumb path").transition().style("fill", function (d) {
					return _this5.colour(d, _this5);
				});
				this.path.transition().style("fill", function (d) {
					return _this5.colour(d, _this5);
				});
				this.text.transition().style("fill", function (d) {
					return _univis2.default.getReadableColorFor(_this5.colour(d, _this5));
				});
			}

			/**
    * Sets the visualisation in full screen mode
    *
    * @param <boolean> isFullScreen indicates if we're in full screen mode
    */

		}, {
			key: "setFullScreen",
			value: function setFullScreen(isFullScreen) {
				// the delay is because the event fires before we're in fullscreen
				// so the height en width functions don't give a correct result
				// without the delay
				setTimeout(function () {
					var size = 740;
					if (isFullScreen) {
						size = Math.min($(window).height() - 44, $(window).width() - 250);
					}
					$(this.element).children("svg").attr("width", size).attr("height", size);
				}, 1000);
			}
		}], [{
			key: "isParentOf",
			value: function isParentOf(p, c, ml) {
				if (c.depth >= ml) {
					return false;
				}
				if (p === c) {
					return true;
				}
				if (p.children) {
					return p.children.some(function (d) {
						return Sunburst.isParentOf(d, c, ml);
					});
				}
				return false;
			}

			/**
    * calculate the max-y of the clicked item
    *
    * @param <Object> d The clicked item
    * @return <Number> The maximal y-value
    */

		}, {
			key: "maxY",
			value: function maxY(d) {
				return d.children ? Math.max.apply(Math, _toConsumableArray(d.children.map(Sunburst.maxY))) : d.y + d.dy;
			}

			/** ****** class constants **********/

		}, {
			key: "MARGIN",
			get: function get() {
				return {
					top: 0,
					right: 0,
					bottom: 0,
					left: 0
				};
			}
		}, {
			key: "COLORS",
			get: function get() {
				return ["#f9f0ab", "#e8e596", "#f0e2a3", "#ede487", "#efd580", "#f1cb82", "#f1c298", "#e8b598", "#d5dda1", "#c9d2b5", "#aec1ad", "#a7b8a8", "#b49a3d", "#b28647", "#a97d32", "#b68334", "#d6a680", "#dfad70", "#a2765d", "#9f6652", "#b9763f", "#bf6e5d", "#af643c", "#9b4c3f", "#72659d", "#8a6e9e", "#8f5c85", "#934b8b", "#9d4e87", "#92538c", "#8b6397", "#716084", "#2e6093", "#3a5988", "#4a5072", "#393e64", "#aaa1cc", "#e0b5c9", "#e098b0", "#ee82a2", "#ef91ac", "#eda994", "#eeb798", "#ecc099", "#f6d5aa", "#f0d48a", "#efd95f", "#eee469", "#dbdc7f", "#dfd961", "#ebe378", "#f5e351"];
			}
		}, {
			key: "FIXED_COLORS",
			get: function get() {
				return ["#1f77b4", "#aec7e8", "#ff7f0e", "#ffbb78", "#2ca02c", "#98df8a", "#d62728", "#ff9896", "#9467bd", "#c5b0d5", "#8c564b", "#c49c94", "#e377c2", "#f7b6d2", "#7f7f7f", "#c7c7c7", "#bcbd22", "#dbdb8d", "#17becf", "#9edae5", "#393b79", "#5254a3", "#6b6ecf", "#9c9ede", "#637939", "#8ca252", "#b5cf6b", "#cedb9c", "#8c6d31", "#bd9e39", "#e7ba52", "#e7cb94", "#843c39", "#ad494a", "#d6616b", "#e7969c", "#7b4173", "#a55194", "#ce6dbd", "#de9ed6", "#3182bd", "#6baed6", "#9ecae1", "#c6dbef", "#e6550d", "#fd8d3c", "#fdae6b", "#fdd0a2", "#31a354", "#74c476", "#a1d99b", "#c7e9c0", "#756bb1", "#9e9ac8", "#bcbddc", "#dadaeb", "#636363", "#969696", "#bdbdbd", "#d9d9d9"];
			}
		}, {
			key: "DEFAULTS",
			get: function get() {
				return {
					height: 600,
					width: 600,
					breadcrumbWidth: 200,
					radius: 300,

					className: "unipept-sunburst",
					levels: 4,
					getLevel: function getLevel(d) {
						return d.getDepth();
					},

					duration: 1000,
					colors: Sunburst.COLORS,
					fixedColors: Sunburst.FIXED_COLORS,
					useFixedColors: false,

					countAccessor: function countAccessor(d) {
						return d.data.self_count;
					},
					rerootCallback: undefined,

					getLabel: function getLabel(d) {
						return d.name === "empty" ? "" : d.name;
					},

					enableTooltips: true,
					getTooltip: this.getTooltip,
					getTooltipTitle: _univis2.default.getTooltipTitle,
					getTooltipText: _univis2.default.getTooltipText
				};
			}
		}]);

		return Sunburst;
	}();

	exports.default = Sunburst;

	function Plugin(userData, option) {
		return this.each(function () {
			var $this = $(this);
			var data = $this.data("vis.sunburst");
			var options = $.extend({}, $this.data(), (typeof option === "undefined" ? "undefined" : _typeof(option)) === "object" && option);

			if (!data) {
				$this.data("vis.sunburst", data = new Sunburst(this, userData, options));
			}
			if (typeof option === "string") {
				data[option]();
			}
		});
	}

	$.fn.sunburst = Plugin;
	$.fn.sunburst.Constructor = Sunburst;

	/***/
},
/* 8 */
/***/function (module, exports, __webpack_require__) {

	"use strict";

	Object.defineProperty(exports, "__esModule", {
		value: true
	});

	var _createClass = function () {
		function defineProperties(target, props) {
			for (var i = 0; i < props.length; i++) {
				var descriptor = props[i];descriptor.enumerable = descriptor.enumerable || false;descriptor.configurable = true;if ("value" in descriptor) descriptor.writable = true;Object.defineProperty(target, descriptor.key, descriptor);
			}
		}return function (Constructor, protoProps, staticProps) {
			if (protoProps) defineProperties(Constructor.prototype, protoProps);if (staticProps) defineProperties(Constructor, staticProps);return Constructor;
		};
	}();

	var _node = __webpack_require__(4);

	var _node2 = _interopRequireDefault(_node);

	function _interopRequireDefault(obj) {
		return obj && obj.__esModule ? obj : { default: obj };
	}

	function _classCallCheck(instance, Constructor) {
		if (!(instance instanceof Constructor)) {
			throw new TypeError("Cannot call a class as a function");
		}
	}

	function _possibleConstructorReturn(self, call) {
		if (!self) {
			throw new ReferenceError("this hasn't been initialised - super() hasn't been called");
		}return call && ((typeof call === "undefined" ? "undefined" : _typeof2(call)) === "object" || typeof call === "function") ? call : self;
	}

	function _inherits(subClass, superClass) {
		if (typeof superClass !== "function" && superClass !== null) {
			throw new TypeError("Super expression must either be null or a function, not " + (typeof superClass === "undefined" ? "undefined" : _typeof2(superClass)));
		}subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, enumerable: false, writable: true, configurable: true } });if (superClass) Object.setPrototypeOf ? Object.setPrototypeOf(subClass, superClass) : subClass.__proto__ = superClass;
	}

	var SunburstNode = function (_Node) {
		_inherits(SunburstNode, _Node);

		function SunburstNode() {
			_classCallCheck(this, SunburstNode);

			return _possibleConstructorReturn(this, (SunburstNode.__proto__ || Object.getPrototypeOf(SunburstNode)).apply(this, arguments));
		}

		_createClass(SunburstNode, null, [{
			key: "new",
			value: function _new() {
				var node = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : {};

				return new SunburstNode(node);
			}
		}, {
			key: "createNode",
			value: function createNode(node) {
				return _node2.default.createNode(node, SunburstNode.new);
			}
		}]);

		return SunburstNode;
	}(_node2.default);

	exports.default = SunburstNode;

	/***/
}]
/******/);
//# sourceMappingURL=unipept-visualizations.js.map
//# sourceMappingURL=unipept-visualizations.es5.js.map
