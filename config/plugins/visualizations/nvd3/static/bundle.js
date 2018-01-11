define(function() { return /******/ (function(modules) { // webpackBootstrap
/******/ 	// The module cache
/******/ 	var installedModules = {};
/******/
/******/ 	// The require function
/******/ 	function __webpack_require__(moduleId) {
/******/
/******/ 		// Check if module is in cache
/******/ 		if(installedModules[moduleId])
/******/ 			return installedModules[moduleId].exports;
/******/
/******/ 		// Create a new module (and put it into the cache)
/******/ 		var module = installedModules[moduleId] = {
/******/ 			exports: {},
/******/ 			id: moduleId,
/******/ 			loaded: false
/******/ 		};
/******/
/******/ 		// Execute the module function
/******/ 		modules[moduleId].call(module.exports, module, module.exports, __webpack_require__);
/******/
/******/ 		// Flag the module as loaded
/******/ 		module.loaded = true;
/******/
/******/ 		// Return the exports of the module
/******/ 		return module.exports;
/******/ 	}
/******/
/******/
/******/ 	// expose the modules object (__webpack_modules__)
/******/ 	__webpack_require__.m = modules;
/******/
/******/ 	// expose the module cache
/******/ 	__webpack_require__.c = installedModules;
/******/
/******/ 	// __webpack_public_path__
/******/ 	__webpack_require__.p = "";
/******/
/******/ 	// Load entry module and return exports
/******/ 	return __webpack_require__(0);
/******/ })
/************************************************************************/
/******/ ([
/* 0 */
/***/ (function(module, exports, __webpack_require__) {

	var __WEBPACK_AMD_DEFINE_ARRAY__, __WEBPACK_AMD_DEFINE_RESULT__;/** This is the common wrapper for nvd3 based visualizations. */
	!(__WEBPACK_AMD_DEFINE_ARRAY__ = [ !(function webpackMissingModule() { var e = new Error("Cannot find module \"utilities/tabular-utilities\""); e.code = 'MODULE_NOT_FOUND'; throw e; }()), !(function webpackMissingModule() { var e = new Error("Cannot find module \"plugin/nv.d3\""); e.code = 'MODULE_NOT_FOUND'; throw e; }()), !(function webpackMissingModule() { var e = new Error("Cannot find module \"style!css!plugin/nv.d3.css\""); e.code = 'MODULE_NOT_FOUND'; throw e; }()) ], __WEBPACK_AMD_DEFINE_RESULT__ = function( Utilities ) {
	    var CommonWrapper = Backbone.View.extend({
	        initialize: function( options ) {
	            var self = this;
	            this.options = options;
	            options.render = function( canvas_id, groups ) {
	                return self.render( canvas_id, groups )
	            };
	            Utilities.panelHelper( options );
	        },
	        render: function( canvas_id, groups ) {
	            var self = this;
	            var chart       = this.options.chart;
	            var type        = this.options.type;
	            var makeConfig  = this.options.makeConfig;
	            var d3chart = nv.models[ type ]();
	            nv.addGraph( function() {
	                try {
	                    d3chart.xAxis.axisLabel( chart.settings.get( 'x_axis_label' ) );
	                    d3chart.yAxis.axisLabel( chart.settings.get( 'y_axis_label' ) ).axisLabelDistance( 30 );
	                    d3chart.options( { showControls: false } );
	                    d3chart.showLegend && d3chart.showLegend(chart.settings.get('show_legend') == 'true');
	                    self._makeAxes( d3chart, groups, chart.settings );
	                    makeConfig && makeConfig( d3chart );
	                    chart.settings.get( '__use_panels' ) === 'true' && d3chart.options( { showControls: false } );
	                    d3chart.xAxis.showMaxMin( false );
	                    d3chart.yAxis.showMaxMin( chart.definition.showmaxmin );
	                    d3chart.tooltipContent( function( key, x, y, graph ) {
	                        return '<h3>' + ( graph.point.tooltip || key ) + '</h3>';
	                    });
	                    if ( $( '#' + canvas_id ).length > 0 ) {
	                        var canvas = d3.select( '#' + canvas_id );
	                        canvas.datum( groups ).call( d3chart );
	                        if ( chart.definition.zoomable && chart.definition.zoomable != 'native' ) {
	                            d3chart.clipEdge && d3chart.clipEdge( true );
	                            Utilities.addZoom({
	                                xAxis  : d3chart.xAxis,
	                                yAxis  : d3chart.yAxis,
	                                yDomain: d3chart.yDomain,
	                                xDomain: d3chart.xDomain,
	                                redraw : function() { d3chart.update() },
	                                svg    : canvas
	                            });
	                        }
	                        nv.utils.windowResize( d3chart.update );
	                    }
	                } catch ( err ) {
	                    chart.state( 'failed', err );
	                }
	            });
	            return true;
	        },
	
	        /** Format axes ticks */
	        _makeAxes: function( d3chart, groups, settings ) {
	            var categories = Utilities.makeCategories( groups, [ 'x', 'y' ] );
	            function makeTickFormat( id ) {
	                Utilities.makeTickFormat({
	                    categories  : categories.array[ id ],
	                    type        : settings.get( id + '_axis_type|type' ),
	                    precision   : settings.get( id + '_axis_type|precision' ),
	                    formatter   : function( formatter ) {
	                        formatter && d3chart[ id + 'Axis' ].tickFormat( function( value ) {
	                            return formatter( value );
	                        });
	                    }
	                });
	            };
	            makeTickFormat( 'x' );
	            makeTickFormat( 'y' );
	        }
	    });
	
	    return {
	        nvd3_bar: function(options) {
	            options.type = 'multiBarChart';
	            new CommonWrapper( options );
	        }
	    }
	}.apply(exports, __WEBPACK_AMD_DEFINE_ARRAY__), __WEBPACK_AMD_DEFINE_RESULT__ !== undefined && (module.exports = __WEBPACK_AMD_DEFINE_RESULT__));

/***/ })
/******/ ])});;
//# sourceMappingURL=bundle.js.map