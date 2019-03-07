import "./jqglobals";
// This is a really annoying hack to get bootstrap/jqui jquery bindings available correctly.
/* global $ */
import * as Backbone from "backbone";
import * as d3 from "d3";
import * as _ from "underscore";
import "../../../../../client/galaxy/scripts/ui/peek-column-selector";
import "../../../../../client/galaxy/scripts/ui/pagination";
import "jquery-ui-bundle";
import "bootstrap";

//TODO: Finish unlinking this from the Galaxy codebase (package it, use that way?)

var Visualization = Backbone.Model.extend({
        /** default attributes for a model */
        defaults: {
            config: {}
        },

        /** override urlRoot to handle prefix */
        urlRoot: function() {
            var apiUrl = "api/visualizations";
            return Galaxy.root_api + apiUrl;
        },

        /** Set up the model, determine if accessible, bind listeners
         *  @see Backbone.Model#initialize
         */
        initialize: function(data) {
            // munge config sub-object here since bbone won't handle defaults with this
            if (_.isObject(data.config) && _.isObject(this.defaults.config)) {
                _.defaults(data.config, this.defaults.config);
            }

            this._setUpListeners();
        },

        /** set up any event listeners */
        _setUpListeners: function() {},

        /** override set to properly allow update and trigger change when setting the sub-obj 'config' */
        set: function(key, val) {
            if (key === "config") {
                var oldConfig = this.get("config");
                if (_.isObject(oldConfig)) {
                    val = _.extend(_.clone(oldConfig), val);
                }
            }
            Backbone.Model.prototype.set.call(this, key, val);
            return this;
        },

        /** String representation */
        toString: function() {
            var idAndTitle = this.get("id") || "";
            if (this.get("title")) {
                idAndTitle += `:${this.get("title")}`;
            }
            return `Visualization(${idAndTitle})`;
        }
    }
);

/**
 *  Two Variable scatterplot visualization using d3
 *      Uses semi transparent circles to show density of data in x, y grid
 *      usage :
 *          var plot = new scatterplot( $( 'svg' ).get(0), config, data )
 */

export function scatterplot(renderTo, config, data) {
    //console.log( 'scatterplot', config );

    var translateStr = function(x, y) {
            return "translate(" + x + "," + y + ")";
        },
        rotateStr = function(d, x, y) {
            return "rotate(" + d + "," + x + "," + y + ")";
        },
        getX = function(d, i) {
            //console.debug( d[ config.xColumn ] );
            return d[config.xColumn];
        },
        getY = function(d, i) {
            //console.debug( d[ config.yColumn ] );
            return d[config.yColumn];
        };

    // .................................................................... scales
    var stats = {
        x: { extent: d3.extent(data, getX) },
        y: { extent: d3.extent(data, getY) }
    };

    //TODO: set pan/zoom limits
    //  from http://stackoverflow.com/questions/10422738/limiting-domain-when-zooming-or-panning-in-d3-js
    //self.x.domain([Math.max(self.x.domain()[0], self.options.xmin), Math.min(self.x.domain()[1], self.options.xmax)]);
    //self.y.domain([Math.max(self.y.domain()[0], self.options.ymin), Math.min(self.y.domain()[1], self.options.ymax)]);
    var interpolaterFns = {
        x: d3.scale
            .linear()
            .domain(stats.x.extent)
            .range([0, config.width]),
        y: d3.scale
            .linear()
            .domain(stats.y.extent)
            .range([config.height, 0])
    };

    // .................................................................... main components
    var zoom = d3.behavior
        .zoom()
        .x(interpolaterFns.x)
        .y(interpolaterFns.y)
        .scaleExtent([1, 30])
        .scale(config.scale || 1)
        .translate(config.translate || [0, 0]);

    //console.debug( renderTo );
    var svg = d3
        .select(renderTo)
        .attr("class", "scatterplot")
        //.attr( "width",  config.width  + ( config.margin.right + config.margin.left ) )
        .attr("width", "100%")
        .attr("height", config.height + (config.margin.top + config.margin.bottom));

    var content = svg
        .append("g")
        .attr("class", "content")
        .attr("transform", translateStr(config.margin.left, config.margin.top))
        .call(zoom);

    // a BIG gotcha - zoom (or any mouse/touch event in SVG?) requires the pointer to be over an object
    //  create a transparent rect to be that object here
    content
        .append("rect")
        .attr("class", "zoom-rect")
        .attr("width", config.width)
        .attr("height", config.height)
        .style("fill", "transparent");

    //console.log( 'svg:', svg, 'content:', content );

    // .................................................................... axes
    var axis = { x: {}, y: {} };
    //console.log( 'xTicks:', config.xTicks );
    //console.log( 'yTicks:', config.yTicks );
    axis.x.fn = d3.svg
        .axis()
        .orient("bottom")
        .scale(interpolaterFns.x)
        .ticks(config.xTicks)
        // this will convert thousands -> k, millions -> M, etc.
        .tickFormat(d3.format("s"));

    axis.y.fn = d3.svg
        .axis()
        .orient("left")
        .scale(interpolaterFns.y)
        .ticks(config.yTicks)
        .tickFormat(d3.format("s"));

    axis.x.g = content
        .append("g")
        .attr("class", "x axis")
        .attr("transform", translateStr(0, config.height))
        .call(axis.x.fn);
    //console.log( 'axis.x.g:', axis.x.g );

    axis.y.g = content
        .append("g")
        .attr("class", "y axis")
        .call(axis.y.fn);
    //console.log( 'axis.y.g:', axis.y.g );

    // ................................ axis labels
    var padding = 6;
    // x-axis label
    axis.x.label = svg
        .append("text")
        .attr("id", "x-axis-label")
        .attr("class", "axis-label")
        .text(config.xLabel)
        // align to the top-middle
        .attr("text-anchor", "middle")
        .attr("dominant-baseline", "text-after-edge")
        .attr("x", config.width / 2 + config.margin.left)
        // place 4 pixels below the axis bounds
        .attr("y", config.height + config.margin.bottom + config.margin.top - padding);
    //console.log( 'axis.x.label:', axis.x.label );

    //TODO: anchor to left of x margin/graph
    // y-axis label
    // place 4 pixels left of the axis.y.g left edge
    axis.y.label = svg
        .append("text")
        .attr("id", "y-axis-label")
        .attr("class", "axis-label")
        .text(config.yLabel)
        // align to bottom-middle
        .attr("text-anchor", "middle")
        .attr("dominant-baseline", "text-before-edge")
        .attr("x", padding)
        .attr("y", config.height / 2)
        // rotate around the alignment point
        .attr("transform", rotateStr(-90, padding, config.height / 2));
    //console.log( 'axis.y.label:', axis.y.label );

    axis.redraw = function _redrawAxis() {
        svg.select(".x.axis").call(axis.x.fn);
        svg.select(".y.axis").call(axis.y.fn);
    };

    // .................................................................... grid
    function renderGrid() {
        var grid = { v: {}, h: {} };
        // vertical
        grid.v.lines = content
            .selectAll("line.v-grid-line")
            // data are the axis ticks; enter, update, exit
            .data(interpolaterFns.x.ticks(axis.x.fn.ticks()[0]));
        // enter: append any extra lines needed (more ticks)
        grid.v.lines
            .enter()
            .append("svg:line")
            .classed("grid-line v-grid-line", true);
        // update: set coords
        grid.v.lines
            .attr("x1", interpolaterFns.x)
            .attr("x2", interpolaterFns.x)
            .attr("y1", 0)
            .attr("y2", config.height);
        // exit: just remove them
        grid.v.lines.exit().remove();
        //console.log( 'grid.v.lines:', grid.v.lines );

        // horizontal
        grid.h.lines = content.selectAll("line.h-grid-line").data(interpolaterFns.y.ticks(axis.y.fn.ticks()[0]));
        grid.h.lines
            .enter()
            .append("svg:line")
            .classed("grid-line h-grid-line", true);
        grid.h.lines
            .attr("x1", 0)
            .attr("x2", config.width)
            .attr("y1", interpolaterFns.y)
            .attr("y2", interpolaterFns.y);
        grid.h.lines.exit().remove();
        //console.log( 'grid.h.lines:', grid.h.lines );
        return grid;
    }
    renderGrid();

    //// .................................................................... datapoints
    var datapoints = content
        .selectAll(".glyph")
        .data(data)
        // enter - NEW data to be added as glyphs
        .enter()
        .append("svg:circle")
        .classed("glyph", true)
        .attr("cx", function(d, i) {
            return interpolaterFns.x(getX(d, i));
        })
        .attr("cy", function(d, i) {
            return interpolaterFns.y(getY(d, i));
        })
        .attr("r", 0);

    // for all EXISTING glyphs and those that need to be added: transition anim to final state
    datapoints
        .transition()
        .duration(config.animDuration)
        .attr("r", config.datapointSize);
    //console.log( 'datapoints:', datapoints );

    function _redrawDatapointsClipped() {
        return (
            datapoints
                //TODO: interpolates twice
                .attr("cx", function(d, i) {
                    return interpolaterFns.x(getX(d, i));
                })
                .attr("cy", function(d, i) {
                    return interpolaterFns.y(getY(d, i));
                })
                .style("display", "block")
                // filter out points now outside the graph content area and hide them
                .filter(function(d, i) {
                    var cx = d3.select(this).attr("cx"),
                        cy = d3.select(this).attr("cy");
                    if (cx < 0 || cx > config.width) {
                        return true;
                    }
                    if (cy < 0 || cy > config.height) {
                        return true;
                    }
                    return false;
                })
                .style("display", "none")
        );
    }
    _redrawDatapointsClipped();

    // .................................................................... behaviors
    function zoomed(scale, translateX, translateY) {
        //console.debug( 'zoom', this, zoom.scale(), zoom.translate() );

        // re-render axis, grid, and datapoints
        $(".chart-info-box").remove();
        axis.redraw();
        _redrawDatapointsClipped();
        renderGrid();

        $(svg.node()).trigger("zoom.scatterplot", {
            scale: zoom.scale(),
            translate: zoom.translate()
        });
    }
    //TODO: programmatically set zoom/pan and save in config
    //TODO: set pan/zoom limits
    zoom.on("zoom", zoomed);

    function infoBox(top, left, d) {
        // create an abs pos. element containing datapoint data (d) near the point (top, left)
        //  with added padding to clear the mouse pointer
        left += 8;
        return $(
            [
                '<div class="chart-info-box" style="position: absolute">',
                config.idColumn !== undefined ? "<div>" + d[config.idColumn] + "</div>" : "",
                "<div>",
                getX(d),
                "</div>",
                "<div>",
                getY(d),
                "</div>",
                "</div>"
            ].join("")
        ).css({ top: top, left: left, "z-index": 2 });
    }

    datapoints.on("mouseover", function(d, i) {
        var datapoint = d3.select(this);
        datapoint
            .classed("highlight", true)
            .style("fill", "red")
            .style("fill-opacity", 1);

        // create horiz line to axis
        content
            .append("line")
            .attr("stroke", "red")
            .attr("stroke-width", 1)
            // start not at center, but at the edge of the circle - to prevent mouseover thrashing
            .attr("x1", datapoint.attr("cx") - config.datapointSize)
            .attr("y1", datapoint.attr("cy"))
            .attr("x2", 0)
            .attr("y2", datapoint.attr("cy"))
            .classed("hoverline", true);

        // create vertical line to axis - if not on the x axis
        if (datapoint.attr("cy") < config.height) {
            content
                .append("line")
                .attr("stroke", "red")
                .attr("stroke-width", 1)
                .attr("x1", datapoint.attr("cx"))
                // attributes are strings so, (accrd. to js) '3' - 1 = 2 but '3' + 1 = '31': coerce
                .attr("y1", +datapoint.attr("cy") + config.datapointSize)
                .attr("x2", datapoint.attr("cx"))
                .attr("y2", config.height)
                .classed("hoverline", true);
        }

        // show the info box and trigger an event
        var bbox = this.getBoundingClientRect();
        $("body").append(infoBox(bbox.top, bbox.right, d));
        $(svg.node()).trigger("mouseover-datapoint.scatterplot", [this, d, i]);
    });

    datapoints.on("mouseout", function() {
        // return the point to normal, remove hoverlines and info box
        d3
            .select(this)
            .classed("highlight", false)
            .style("fill", "black")
            .style("fill-opacity", 0.2);
        content.selectAll(".hoverline").remove();
        $(".chart-info-box").remove();
    });
}

//==============================================================================
/* =============================================================================
todo:
    localize
    import button(display), func(model) - when user doesn't match
    Move margins into wid/hi calcs (so final svg dims are w/h)
    Better separation of AJAX in scatterplot.js (maybe pass in function?)
    Labels should auto fill in chart control when dataset has column_names
    Allow column selection/config using the peek output as a base for UI
    Allow setting perPage in chart controls
    Allow option to auto set width/height based on screen real estate avail.
    Handle large number of pages better (Known genes hg19)
    Use d3.nest to allow grouping, pagination/filtration by group (e.g. chromCol)
    Semantic HTML (figure, caption)
    Save as SVG/png
    Does it work w/ Galaxy.Frame?
    Embedding
    Small multiples
    Drag & Drop other splots onto current (redraw with new axis and differentiate the datasets)
    Remove 'chart' namessave
    Somehow link out from info box?

    Subclass on specific datatypes? (vcf, cuffdiff, etc.)
    What can be common/useful to other visualizations?

============================================================================= */
/**
 *  Scatterplot config control UI as a backbone view
 *      handles:
 *          configuring which data will be used
 *          configuring the plot display
 */
var ScatterplotConfigEditor = Backbone.View.extend({
    //TODO: !should be a view on a visualization model
    //logger      : console,
    className: "scatterplot-control-form",

    /** initialize requires a configuration Object containing a dataset Object */
    initialize: function(attributes) {
        if (!this.model) {
            this.model = new Visualization({ type: "scatterplot" });
        }
        //this.log( this + '.initialize, attributes:', attributes );

        if (!attributes || !attributes.dataset) {
            throw new Error("ScatterplotConfigEditor requires a dataset");
        }
        this.dataset = attributes.dataset;
        //this.log( 'dataset:', this.dataset );

        this.display = new ScatterplotDisplay({
            dataset: attributes.dataset,
            model: this.model
        });
    },

    // ------------------------------------------------------------------------- CONTROLS RENDERING
    render: function() {
        //console.log( this + '.render' );
        // render the tab controls, areas and loading indicator
        this.$el.empty().append(ScatterplotConfigEditor.templates.mainLayout({}));
        if (this.model.id) {
            this.$el.find(".copy-btn").show();
            this.$el.find(".save-btn").text("Update saved");
        }
        this.$el.find("[title]").tooltip();

        // render the tab content
        this._render_dataControl();
        this._render_chartControls();
        this._render_chartDisplay();

        // set up behaviours

        // auto render if given both x, y column choices
        var config = this.model.get("config");
        if (this.model.id && _.isFinite(config.xColumn) && _.isFinite(config.yColumn)) {
            this.renderChart();
        }
        return this;
    },

    /** get an object with arrays keyed with possible column types (numeric, text, all)
     *      and if metadata_column_types is set on the dataset, add the indeces of each
     *      column into the appropriate array.
     *  Used to disable certain columns from being selected for x, y axes.
     */
    _getColumnIndecesByType: function() {
        //TODO: not sure these contraints are necc. now
        var types = {
            numeric: [],
            text: [],
            all: []
        };
        _.each(this.dataset.metadata_column_types || [], function(type, i) {
            if (type === "int" || type === "float") {
                types.numeric.push(i);
            } else if (type === "str" || type === "list") {
                types.text.push(i);
            }
            types.all.push(i);
        });
        if (types.numeric.length < 2) {
            types.numeric = [];
        }
        //console.log( 'types:', JSON.stringify( types ) );
        return types;
    },

    /** controls for which columns are used to plot datapoints (and ids/additional info to attach if desired) */
    _render_dataControl: function($where) {
        $where = $where || this.$el;
        var editor = this,
            //column_names = dataset.metadata_column_names || [],
            config = this.model.get("config"),
            columnTypes = this._getColumnIndecesByType();

        // render the html
        var $dataControl = $where.find(".tab-pane#data-control");
        $dataControl.html(
            ScatterplotConfigEditor.templates.dataControl({
                peek: this.dataset.peek
            })
        );

        $dataControl
            .find(".peek")
            .peekColumnSelector({
                controls: [
                    { label: "X Column", id: "xColumn", selected: config.xColumn, disabled: columnTypes.text },
                    { label: "Y Column", id: "yColumn", selected: config.yColumn, disabled: columnTypes.text },
                    { label: "ID Column", id: "idColumn", selected: config.idColumn }
                ]
                //renameColumns       : true
            })
            .on("peek-column-selector.change", function(ev, data) {
                //console.info( 'new selection:', data );
                editor.model.set("config", data);
            })
            .on("peek-column-selector.rename", function(ev, data) {
                //console.info( 'new column names', data );
            });

        $dataControl.find("[title]").tooltip();
        return $dataControl;
    },

    /** tab content to control how the chart is rendered (data glyph size, chart size, etc.) */
    _render_chartControls: function($where) {
        //TODO: as controls on actual chart
        $where = $where || this.$el;
        var editor = this,
            config = this.model.get("config"),
            $chartControls = $where.find("#chart-control");

        // ---- skeleton/form for controls
        $chartControls.html(ScatterplotConfigEditor.templates.chartControl(config));
        //console.debug( '$chartControl:', $chartControls );

        // ---- slider controls
        // limits for controls (by control/chartConfig id)
        var controlRanges = {
            datapointSize: { min: 2, max: 10, step: 1 },
            width: { min: 200, max: 800, step: 20 },
            height: { min: 200, max: 800, step: 20 }
        };

        function onSliderChange() {
            // set the model config when changed and update the slider output text
            var $this = $(this),
                //note: returns a number nicely enough
                newVal = $this.slider("value");
            // parent of slide event target has html5 attr data-config-key
            editor.model.set("config", _.object([[$this.parent().data("config-key"), newVal]]));
            $this.siblings(".slider-output").text(newVal);
        }

        //console.debug( 'numeric sliders:', $chartControls.find( '.numeric-slider-input' ) );
        $chartControls.find(".numeric-slider-input").each(function() {
            // set up the slider with control ranges, change event; set output text to initial value
            var $this = $(this),
                configKey = $this.attr("data-config-key"),
                sliderSettings = _.extend(controlRanges[configKey], {
                    value: config[configKey],
                    change: onSliderChange,
                    slide: onSliderChange
                });
            //console.debug( configKey + ' slider settings:', sliderSettings );
            $this.find(".slider").slider(sliderSettings);
            $this.children(".slider-output").text(config[configKey]);
        });

        // ---- axes labels
        var columnNames = this.dataset.metadata_column_names || [];
        var xLabel = config.xLabel || columnNames[config.xColumn] || "X";
        var yLabel = config.yLabel || columnNames[config.yColumn] || "Y";
        // set label inputs to current x, y metadata_column_names (if any)
        $chartControls
            .find('input[name="X-axis-label"]')
            .val(xLabel)
            .on("change", function() {
                editor.model.set("config", { xLabel: $(this).val() });
            });
        $chartControls
            .find('input[name="Y-axis-label"]')
            .val(yLabel)
            .on("change", function() {
                editor.model.set("config", { yLabel: $(this).val() });
            });

        //console.debug( '$chartControls:', $chartControls );
        $chartControls.find("[title]").tooltip();
        return $chartControls;
    },

    /** render the tab content where the chart is displayed (but not the chart itself) */
    _render_chartDisplay: function($where) {
        $where = $where || this.$el;
        var $chartDisplay = $where.find(".tab-pane#chart-display");
        this.display.setElement($chartDisplay);
        this.display.render();

        $chartDisplay.find("[title]").tooltip();
        return $chartDisplay;
    },

    // ------------------------------------------------------------------------- EVENTS
    events: {
        "change #include-id-checkbox": "toggleThirdColumnSelector",
        "click #data-control .render-button": "renderChart",
        "click #chart-control .render-button": "renderChart",
        "click .save-btn": "saveVisualization"
        //'click .copy-btn'                       : function(e){ this.model.save(); }
    },

    saveVisualization: function() {
        var editor = this;
        this.model
            .save()
            .fail(function(xhr, status, message) {
                console.error(xhr, status, message);
                editor.trigger("save:error", this);
                alert("Error loading data:\n" + xhr.responseText);
            })
            .then(function() {
                editor.display.render();
            });
    },

    toggleThirdColumnSelector: function() {
        // show/hide the id selector on the data settings panel
        this.$el
            .find('select[name="idColumn"]')
            .parent()
            .toggle();
    },

    // ------------------------------------------------------------------------- CHART/STATS RENDERING
    renderChart: function() {
        //console.log( this + '.renderChart' );
        // fetch the data, (re-)render the chart
        this.$el.find(".nav li.disabled").removeClass("disabled");
        this.$el
            .find("ul.nav")
            .find('a[href="#chart-display"]')
            .tab("show");
        this.display.fetchData();
        //console.debug( this.display.$el );
    },

    toString: function() {
        return "ScatterplotConfigEditor(" + (this.dataset ? this.dataset.id : "") + ")";
    }
});

ScatterplotConfigEditor.templates = {
    // tabbed, main layout for the editor (not used for scatterplot-display)
    mainLayout: _.template(
        [
            '<div class="scatterplot-editor tabbable tabs-left">',
            // tab buttons/headers using Bootstrap
            '<ul class="nav nav-tabs">',
            // start with the data controls as the displayed tab
            '<li class="nav-item active">',
            '<a class="nav-link" title="Use this tab to change which data are used"',
            'href="#data-control" data-toggle="tab">Data Controls</a>',
            '</li>',
            '<li class="nav-item">',
            '<a class="nav-link" title="Use this tab to change how the chart is drawn"',
            'href="#chart-control" data-toggle="tab" >Chart Controls</a>',
            '</li>',
            // chart starts as disabled since there's no info yet
            '<li class="nav-item disabled">',
            '<a class="nav-link" title="This tab will display the chart"',
            'href="#chart-display" data-toggle="tab">Chart</a>',
            '</li>',
            // button for saving the visualization config on the server
            '<li class="nav-item">',
            '<a class="save-btn nav-link">Save</a>',
            '</li>',
            '</ul>',

            // data form, chart config form, chart all get their own tab
            '<div class="tab-content">',
            // tab for data settings form
            '<div id="data-control" class="scatterplot-config-control tab-pane active"></div>',

            // tab for chart graphics control form
            '<div id="chart-control" class="scatterplot-config-control tab-pane"></div>',

            // tab for actual chart
            '<div id="chart-display" class="scatterplot-display tab-pane"></div>',

            "</div>",
            "</div>"
        ].join("")
    ),

    // the controls for data selection (this is mostly done with column selector now)
    // TODO: this could be moved to the main template above
    // TODO: localize
    dataControl: _.template(
        [
            '<p class="help-text">',
            "Use the following control to change which columns are used by the chart. Click any cell ",
            "from the last three rows of the table to select the column for the appropriate data. ",
            "Use the 'Draw' button to render (or re-render) the chart with the current settings. ",
            "</p>",

            '<ul class="help-text" style="margin-left: 8px">',
            "<li><b>X Column</b>: which column values will be used for the x axis of the chart.</li>",
            "<li><b>Y Column</b>: which column values will be used for the y axis of the chart.</li>",
            "<li><b>ID Column</b>: an additional column value displayed when the user hovers over a data point. ",
            "It may be useful to select unique or categorical identifiers here (such as gene ids).",
            "</li>",
            "</ul>",

            '<div class="column-selection">',
            // the only dynamic thing
            '<pre class="peek"><%= peek %></pre>',
            "</div>",

            '<p class="help-text help-text-small">',
            "<b>Note</b>: If it can be determined from the dataset's filetype that a column is not numeric, ",
            "that column choice may be disabled for either the x or y axis.",
            "</p>",

            '<button class="render-button btn btn-primary active">Draw</button>'
        ].join("")
    ),

    chartControl: _.template(
        [
            '<p class="help-text">',
            "Use the following controls to how the chart is displayed. The slide controls can be moved ",
            "by the mouse or, if the 'handle' is in focus, your keyboard's arrow keys. ",
            "Move the focus between controls by using the tab or shift+tab keys on your keyboard. ",
            "Use the 'Draw' button to render (or re-render) the chart with the current settings. ",
            "</p>",

            '<div data-config-key="datapointSize" class="form-input numeric-slider-input">',
            '<label for="datapointSize">Size of data point: </label>',
            '<div class="slider-output"><%- datapointSize %></div>',
            '<div class="slider"></div>',
            '<p class="form-help help-text-small">',
            "Size of the graphic representation of each data point",
            "</p>",
            "</div>",

            '<div data-config-key="width" class="form-input numeric-slider-input">',
            '<label for="width">Chart width: </label>',
            '<div class="slider-output"><%- width %></div>',
            '<div class="slider"></div>',
            '<p class="form-help help-text-small">',
            "(not including chart margins and axes)",
            "</p>",
            "</div>",

            '<div data-config-key="height" class="form-input numeric-slider-input">',
            '<label for="height">Chart height: </label>',
            '<div class="slider-output"><%- height %></div>',
            '<div class="slider"></div>',
            '<p class="form-help help-text-small">',
            "(not including chart margins and axes)",
            "</p>",
            "</div>",

            '<div data-config-key="X-axis-label"class="text-input form-input">',
            '<label for="X-axis-label">Re-label the X axis: </label>',
            '<input type="text" name="X-axis-label" id="X-axis-label" value="<%- xLabel %>" />',
            '<p class="form-help help-text-small"></p>',
            "</div>",

            '<div data-config-key="Y-axis-label" class="text-input form-input">',
            '<label for="Y-axis-label">Re-label the Y axis: </label>',
            '<input type="text" name="Y-axis-label" id="Y-axis-label" value="<%- yLabel %>" />',
            '<p class="form-help help-text-small"></p>',
            "</div>",

            '<button class="render-button btn btn-primary active">Draw</button>'
        ].join("")
    )

    // mainLayout      : scatterplot.editor,
    // dataControl     : scatterplot.datacontrol,
    // chartControl    : scatterplot.chartcontrol
};

//==============================================================================
// =============================================================================
/**
 *  Scatterplot display control UI as a backbone view
 *      handles:
 *          fetching the data (if needed)
 *          computing and displaying data stats
 *          controls for pagination of data (if needed)
 */
var ScatterplotDisplay = Backbone.View.extend({
    initialize: function(attributes) {
        this.data = null;
        this.dataset = attributes.dataset;
        this.lineCount = this.dataset.metadata_data_lines || null;
    },

    fetchData: function() {
        this.showLoadingIndicator();
        //console.debug( 'currPage', this.config.pagination.currPage );
        var view = this,
            config = this.model.get("config"),
            //TODO: very tied to datasets - should be generalized eventually
            baseUrl = window.parent && window.parent.galaxy_config ? window.parent.galaxy_config.root : "/",
            xhr = $.getJSON(baseUrl + "api/datasets/" + this.dataset.id, {
                data_type: "raw_data",
                provider: "dataset-column",
                limit: config.pagination.perPage,
                offset: config.pagination.currPage * config.pagination.perPage
            });
        xhr.done(function(data) {
            // no need to hide loading indicator, line info will write over that
            view.data = data.data;
            view.trigger("data:fetched", view);
            view.renderData();
        });
        xhr.fail(function(xhr, status, message) {
            console.error(xhr, status, message);
            view.trigger("data:error", view);
            alert("Error loading data:\n" + xhr.responseText);
        });
        return xhr;
    },

    showLoadingIndicator: function() {
        // display the loading indicator over the tab panels if hidden, update message (if passed)
        this.$el
            .find(".scatterplot-data-info")
            .html(
                [
                    '<div class="loading-indicator">',
                    '<span class="fa fa-spinner fa-spin"></span>',
                    '<span class="loading-indicator-message">loading...</span>',
                    "</div>"
                ].join("")
            );
    },

    template: function() {
        var html = [
            '<div class="controls clear">',
            '<div class="right">',
            '<p class="scatterplot-data-info"></p>',
            '<button class="stats-toggle-btn">Stats</button>',
            '<button class="rerender-btn">Redraw</button>',
            "</div>",
            '<div class="left">',
            '<div class="page-control"></div>',
            "</div>",
            "</div>",
            "<svg/>", //TODO: id
            '<div class="stats-display"></div>'
        ].join("");
        return html;
    },

    render: function() {
        this.$el.addClass("scatterplot-display").html(this.template());
        if (this.data) {
            this.renderData();
        }
        return this;
    },

    renderData: function() {
        this.renderLeftControls();
        this.renderRightControls();
        this.renderPlot(this.data);
        this.getStats();
    },

    renderLeftControls: function() {
        var display = this,
            config = this.model.get("config");

        this.$el
            .find(".controls .left .page-control")
            .pagination({
                startingPage: config.pagination.currPage,
                perPage: config.pagination.perPage,
                totalDataSize: this.lineCount,
                currDataSize: this.data.length

                //TODO: move to named function and remove only named
            })
            .off()
            .on("pagination.page-change", function(event, page) {
                //console.debug( 'pagination:page-change', page );
                config.pagination.currPage = page;
                display.model.set("config", { pagination: config.pagination });
                //console.debug( pagination, display.model.get( 'config' ).pagination );
                display.resetZoom();
                display.fetchData();
            });
        return this;
    },

    renderRightControls: function() {
        var view = this;
        this.setLineInfo(this.data);
        // clear prev. handlers due to closure around data
        this.$el
            .find(".stats-toggle-btn")
            .off()
            .click(function() {
                view.toggleStats();
            });
        this.$el
            .find(".rerender-btn")
            .off()
            .click(function() {
                view.resetZoom();
                view.renderPlot(this.data);
            });
    },

    /** render and show the d3 plot into the svg node of the view */
    renderPlot: function() {
        var view = this,
            $svg = this.$el.find("svg");
        // turn off stats, clear previous svg, and make it visible
        this.toggleStats(false);
        $svg
            .off()
            .empty()
            .show()
            // set up listeners for events from plot
            .on("zoom.scatterplot", function(ev, zoom) {
                //TODO: possibly throttle this
                //console.debug( 'zoom.scatterplot', zoom.scale, zoom.translate );
                view.model.set("config", zoom);
            });
        //TODO: may not be necessary to off/on this more than the initial on
        // call the sep. d3 function to generate the plot
        scatterplot($svg.get(0), this.model.get("config"), this.data);
    },

    setLineInfo: function(data, contents) {
        if (data) {
            var config = this.model.get("config"),
                totalLines = this.lineCount || "an unknown total",
                lineStart = config.pagination.currPage * config.pagination.perPage,
                lineEnd = lineStart + data.length;
            this.$el
                .find(".controls p.scatterplot-data-info")
                .text([lineStart + 1, "to", lineEnd, "of", totalLines].join(" "));
        } else {
            this.$el.find(".controls p.scatterplot-data-info").html(contents || "");
        }

        return this;
    },

    resetZoom: function(scale, translate) {
        scale = scale !== undefined ? scale : 1;
        translate = translate !== undefined ? translate : [0, 0];
        this.model.set("config", { scale: scale, translate: translate });
        return this;
    },

    // ------------------------------------------------------------------------ statistics display
    /** create a webworker to calc stats for data given */
    getStats: function() {
        if (!this.data) {
            return;
        }
        var view = this;
        var config = this.model.get("config");
        var meanWorker = new window.Worker("worker-stats.js");
        meanWorker.postMessage({
            data: this.data,
            keys: [config.xColumn, config.yColumn]
        });
        meanWorker.onerror = function(event) {
            meanWorker.terminate();
        };
        meanWorker.onmessage = function(event) {
            view.renderStats(event.data);
        };
    },

    renderStats: function(stats, error) {
        //console.debug( 'renderStats:', stats, error );
        //console.debug( JSON.stringify( stats, null, '  ' ) );
        var config = this.model.get("config"),
            $statsTable = this.$el.find(".stats-display"),
            xLabel = config.xLabel,
            yLabel = config.yLabel,
            $table = $("<table/>")
                .addClass("table")
                .append(["<thead><th></th><th>", xLabel, "</th><th>", yLabel, "</th></thead>"].join(""))
                .append(
                    _.map(stats, function(stat, key) {
                        return $(["<tr><td>", key, "</td><td>", stat[0], "</td><td>", stat[1], "</td></tr>"].join(""));
                    })
                );
        $statsTable.empty().append($table);
    },

    toggleStats: function(showStats) {
        var $statsDisplay = this.$el.find(".stats-display");
        showStats = showStats === undefined ? $statsDisplay.is(":hidden") : showStats;
        if (showStats) {
            this.$el.find("svg").hide();
            $statsDisplay.show();
            this.$el.find(".controls .stats-toggle-btn").text("Plot");
        } else {
            $statsDisplay.hide();
            this.$el.find("svg").show();
            this.$el.find(".controls .stats-toggle-btn").text("Stats");
        }
    },

    toString: function() {
        return "ScatterplotView()";
    }
});
var ScatterplotModel = Visualization.extend({
    defaults: {
        type: "scatterplot",

        config: {
            // shouldn't be needed for properly saved splots - also often incorrect
            //xColumn : 0,
            //yColumn : 1,

            pagination: {
                currPage: 0,
                perPage: 3000
            },

            // graph style
            width: 400,
            height: 400,

            margin: {
                top: 16,
                right: 16,
                bottom: 40,
                left: 54
            },

            xTicks: 10,
            xLabel: "X",
            yTicks: 10,
            yLabel: "Y",

            datapointSize: 4,
            animDuration: 500,

            scale: 1,
            translate: [0, 0]
        }
    }
});

window.ScatterplotModel = ScatterplotModel;
window.ScatterplotConfigEditor = ScatterplotConfigEditor;
