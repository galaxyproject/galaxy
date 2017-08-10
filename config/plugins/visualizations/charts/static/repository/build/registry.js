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
/***/ function(module, exports, __webpack_require__) {

	var __WEBPACK_AMD_DEFINE_ARRAY__, __WEBPACK_AMD_DEFINE_RESULT__;!(__WEBPACK_AMD_DEFINE_ARRAY__ = [], __WEBPACK_AMD_DEFINE_RESULT__ = function() { return {nvd3_bar:__webpack_require__( 3 ), nvd3_bar_horizontal:__webpack_require__( 6 ), nvd3_bar_horizontal_stacked:__webpack_require__( 7 ), nvd3_bar_stacked:__webpack_require__( 8 ), nvd3_line:__webpack_require__( 9 ), nvd3_line_focus:__webpack_require__( 10 ), nvd3_scatter:__webpack_require__( 11 ), nvd3_stackedarea:__webpack_require__( 12 ), nvd3_stackedarea_full:__webpack_require__( 13 ), nvd3_stackedarea_stream:__webpack_require__( 14 ), nvd3_pie:__webpack_require__( 15 ), nvd3_histogram:__webpack_require__( 16 ), nvd3_histogram_discrete:__webpack_require__( 17 ), jqplot_bar:__webpack_require__( 18 ), jqplot_boxplot:__webpack_require__( 20 ), jqplot_histogram_discrete:__webpack_require__( 21 ), jqplot_line:__webpack_require__( 22 ), jqplot_scatter:__webpack_require__( 23 ), biojs_msa:__webpack_require__( 24 ), biojs_drawrnajs:__webpack_require__( 25 ), biojs_phylocanvas:__webpack_require__( 26 ), others_example:__webpack_require__( 27 ), others_heatmap:__webpack_require__( 28 ), others_heatmap_cluster:__webpack_require__( 29 ), cytoscape_viewer:__webpack_require__( 30 ), pv_viewer:__webpack_require__( 31 ), benfred_venn:__webpack_require__( 32 ), ngl_viewer:__webpack_require__( 33 ),} }.apply(exports, __WEBPACK_AMD_DEFINE_ARRAY__), __WEBPACK_AMD_DEFINE_RESULT__ !== undefined && (module.exports = __WEBPACK_AMD_DEFINE_RESULT__));

/***/ },
/* 1 */,
/* 2 */,
/* 3 */
/***/ function(module, exports, __webpack_require__) {

	var __WEBPACK_AMD_DEFINE_ARRAY__, __WEBPACK_AMD_DEFINE_RESULT__;!(__WEBPACK_AMD_DEFINE_ARRAY__ = [ __webpack_require__(4) ], __WEBPACK_AMD_DEFINE_RESULT__ = function( nvd3_config ) {
	    return $.extend(true, {}, nvd3_config, {
	        title       : 'Bar diagram',
	        description : 'Renders a regular bar diagram using NVD3 hosted at http://www.nvd3.org.',
	        groups      : {
	            x : {
	                label       : 'Values for x-axis',
	                type        : 'data_column',
	                is_label    : true,
	                is_auto     : true
	            },
	            y : {
	                label       : 'Values for y-axis',
	                type        : 'data_column',
	                is_numeric  : true
	            }
	        }
	    });
	}.apply(exports, __WEBPACK_AMD_DEFINE_ARRAY__), __WEBPACK_AMD_DEFINE_RESULT__ !== undefined && (module.exports = __WEBPACK_AMD_DEFINE_RESULT__));

/***/ },
/* 4 */
/***/ function(module, exports, __webpack_require__) {

	var __WEBPACK_AMD_DEFINE_ARRAY__, __WEBPACK_AMD_DEFINE_RESULT__;!(__WEBPACK_AMD_DEFINE_ARRAY__ = [ __webpack_require__(5) ], __WEBPACK_AMD_DEFINE_RESULT__ = function( default_config ) {
	    return $.extend( true, {}, default_config, {
	        title       : '',
	        library     : 'NVD3',
	        tag         : 'svg',
	        keywords    : 'nvd3 default',
	        exports     : [ 'png', 'svg', 'pdf' ],
	        groups      : {
	            color: {
	                label       : 'Pick a series color',
	                type        : 'color'
	            },
	            tooltip : {
	                label       : 'Data point labels',
	                type        : 'data_column',
	                is_label    : true,
	                is_auto     : true
	            }
	        }
	    });
	}.apply(exports, __WEBPACK_AMD_DEFINE_ARRAY__), __WEBPACK_AMD_DEFINE_RESULT__ !== undefined && (module.exports = __WEBPACK_AMD_DEFINE_RESULT__));

/***/ },
/* 5 */
/***/ function(module, exports, __webpack_require__) {

	var __WEBPACK_AMD_DEFINE_ARRAY__, __WEBPACK_AMD_DEFINE_RESULT__;!(__WEBPACK_AMD_DEFINE_ARRAY__ = [], __WEBPACK_AMD_DEFINE_RESULT__ = function() {
	    var axisLabel = function( name, options ) {
	        options = options || {};
	        prefix  = name.substr( 0, 1 );
	        return {
	            name        : name,
	            label       : prefix.toUpperCase() + '-Axis label',
	            help        : 'Provide a label for the axis.',
	            type        : 'text',
	            value       : options.value || prefix.toUpperCase() + '-axis',
	            placeholder : 'Axis label'
	        }
	    }
	    var axisType = function( name, options ) {
	        options = options || {};
	        prefix  = name.substr( 0, 1 );
	        var axisPrecision = function() {
	            return { name    : 'precision',
	                     label   : 'Axis tick format',
	                     help    : 'Select the tick format for the axis.',
	                     type    : 'select',
	                     value   : options.precision || 1,
	                     data    : [ { label : '0.00001', value : '5' },
	                                 { label : '0.0001',  value : '4' },
	                                 { label : '0.001',   value : '3' },
	                                 { label : '0.01',    value : '2' },
	                                 { label : '0.1',     value : '1' },
	                                 { label : '1',       value : '0' } ] }
	        }
	        return {
	            name        : prefix + '_axis_type',
	            type        : 'conditional',
	            test_param  : {
	                name        : 'type',
	                label       : prefix.toUpperCase() + '-Axis value type',
	                type        : 'select',
	                value       : options.value || 'auto',
	                help        : 'Select the value type of the axis.',
	                data        : [ { value : 'hide',   label : '-- Do not show values --' },
	                                { value : 'auto',   label : 'Auto' },
	                                { value : 'f',      label : 'Float' },
	                                { value : 'd',      label : 'Integer' },
	                                { value : 'e',      label : 'Exponent' },
	                                { value : 'p',      label : 'Percent' },
	                                { value : 's',      label : 'SI-prefix' } ]
	            },
	            cases       : [ { value   : 'hide' },
	                            { value   : 'auto' },
	                            { value   : 'f', inputs: [ axisPrecision() ] },
	                            { value   : 'd' },
	                            { value   : 'e', inputs: [ axisPrecision() ] },
	                            { value   : 'p', inputs: [ axisPrecision() ] },
	                            { value   : 's' } ]
	        }
	    }
	    return {
	        title       : '',
	        library     : '',
	        tag         : '',
	        keywords    : '',
	        datatypes   : [ 'bed', 'bedgraph', 'bedstrict', 'bed6', 'bed12', 'chrint', 'customtrack', 'gff', 'gff3', 'gtf', 'interval', 'encodepeak', 'wig', 'scidx', 'fli', 'csv', 'tsv', 'eland', 'elandmulti', 'picard_interval_list', 'gatk_dbsnp', 'gatk_tranche', 'gatk_recal', 'ct', 'pileup', 'sam', 'taxonomy', 'tabular', 'vcf', 'xls' ],
	        use_panels  : 'both',
	        settings    : {
	            x_axis_label : axisLabel( 'x_axis_label' ),
	            x_axis_type  : axisType( 'x_axis_type' ),
	            y_axis_label : axisLabel( 'y_axis_label' ),
	            y_axis_type  : axisType( 'y_axis_type' ),
	            show_legend  : { type: 'boolean', label: 'Show legend', help: 'Would you like to add a legend?' }
	        },
	        groups      : {
	            key: {
	                label       : 'Provide a label',
	                type        : 'text',
	                placeholder : 'Data label',
	                value       : 'Data label'
	            }
	        }
	    }
	}.apply(exports, __WEBPACK_AMD_DEFINE_ARRAY__), __WEBPACK_AMD_DEFINE_RESULT__ !== undefined && (module.exports = __WEBPACK_AMD_DEFINE_RESULT__));

/***/ },
/* 6 */
/***/ function(module, exports, __webpack_require__) {

	var __WEBPACK_AMD_DEFINE_ARRAY__, __WEBPACK_AMD_DEFINE_RESULT__;!(__WEBPACK_AMD_DEFINE_ARRAY__ = [ __webpack_require__(4) ], __WEBPACK_AMD_DEFINE_RESULT__ = function( nvd3_config ) {
	    return $.extend( true, {}, nvd3_config, {
	        title       : 'Horizontal',
	        description : 'Renders a horizontal bar diagram using NVD3 hosted at http://www.nvd3.org.',
	        groups      : {
	            x : {
	                label       : 'Values for x-axis',
	                type        : 'data_column',
	                is_label    : true,
	                is_auto     : true
	            },
	            y : {
	                label       : 'Values for y-axis',
	                type        : 'data_column',
	                is_numeric  : true
	            }
	        }
	    });
	}.apply(exports, __WEBPACK_AMD_DEFINE_ARRAY__), __WEBPACK_AMD_DEFINE_RESULT__ !== undefined && (module.exports = __WEBPACK_AMD_DEFINE_RESULT__));

/***/ },
/* 7 */
/***/ function(module, exports, __webpack_require__) {

	var __WEBPACK_AMD_DEFINE_ARRAY__, __WEBPACK_AMD_DEFINE_RESULT__;!(__WEBPACK_AMD_DEFINE_ARRAY__ = [ __webpack_require__(4) ], __WEBPACK_AMD_DEFINE_RESULT__ = function( nvd3_config ) {
	    return $.extend( true, {}, nvd3_config, {
	        title       : 'Stacked horizontal',
	        description : 'Renders a stacked horizontal bar diagram using NVD3 hosted at http://www.nvd3.org.',
	        use_panels  : 'no',
	        groups      : {
	            x : {
	                label       : 'Values for x-axis',
	                type        : 'data_column',
	                is_label    : true,
	                is_auto     : true
	            },
	            y : {
	                label       : 'Values for y-axis',
	                type        : 'data_column',
	                is_numeric  : true
	            }
	        }
	    });
	}.apply(exports, __WEBPACK_AMD_DEFINE_ARRAY__), __WEBPACK_AMD_DEFINE_RESULT__ !== undefined && (module.exports = __WEBPACK_AMD_DEFINE_RESULT__));

/***/ },
/* 8 */
/***/ function(module, exports, __webpack_require__) {

	var __WEBPACK_AMD_DEFINE_ARRAY__, __WEBPACK_AMD_DEFINE_RESULT__;!(__WEBPACK_AMD_DEFINE_ARRAY__ = [ __webpack_require__(4) ], __WEBPACK_AMD_DEFINE_RESULT__ = function( nvd3_config ) {
	    return $.extend( true, {}, nvd3_config, {
	        title       : 'Stacked',
	        description : 'Renders a stacked bar diagram using NVD3 hosted at http://www.nvd3.org.',
	        use_panels  : 'no',
	        groups      : {
	            x : {
	                label       : 'Values for x-axis',
	                type        : 'data_column',
	                is_label    : true,
	                is_auto     : true
	            },
	            y : {
	                label       : 'Values for y-axis',
	                type        : 'data_column',
	                is_numeric  : true
	            }
	        }
	    });
	}.apply(exports, __WEBPACK_AMD_DEFINE_ARRAY__), __WEBPACK_AMD_DEFINE_RESULT__ !== undefined && (module.exports = __WEBPACK_AMD_DEFINE_RESULT__));

/***/ },
/* 9 */
/***/ function(module, exports, __webpack_require__) {

	var __WEBPACK_AMD_DEFINE_ARRAY__, __WEBPACK_AMD_DEFINE_RESULT__;!(__WEBPACK_AMD_DEFINE_ARRAY__ = [ __webpack_require__(4) ], __WEBPACK_AMD_DEFINE_RESULT__ = function( nvd3_config ) {
	    return $.extend( true, {}, nvd3_config, {
	        title       : 'Line chart',
	        description : 'Renders a line chart using NVD3 hosted at http://www.nvd3.org.',
	        zoomable    : true,
	        groups      : {
	            x : {
	                label       : 'Values for x-axis',
	                type        : 'data_column',
	                is_label    : true,
	                is_auto     : true
	            },
	            y : {
	                label       : 'Values for y-axis',
	                type        : 'data_column',
	                is_numeric  : true
	            }
	        }
	    });
	}.apply(exports, __WEBPACK_AMD_DEFINE_ARRAY__), __WEBPACK_AMD_DEFINE_RESULT__ !== undefined && (module.exports = __WEBPACK_AMD_DEFINE_RESULT__));

/***/ },
/* 10 */
/***/ function(module, exports, __webpack_require__) {

	var __WEBPACK_AMD_DEFINE_ARRAY__, __WEBPACK_AMD_DEFINE_RESULT__;!(__WEBPACK_AMD_DEFINE_ARRAY__ = [ __webpack_require__(4) ], __WEBPACK_AMD_DEFINE_RESULT__ = function( nvd3_config ) {
	    return $.extend( true, {}, nvd3_config, {
	        title       : 'Line with focus',
	        description : 'Renders a line chart with focus panel using NVD3 hosted at http://www.nvd3.org.',
	        zoomable    : 'native',
	        groups      : {
	            x : {
	                label       : 'Values for x-axis',
	                type        : 'data_column',
	                is_label    : true,
	                is_auto     : true
	            },
	            y : {
	                label       : 'Values for y-axis',
	                type        : 'data_column',
	                is_numeric  : true
	            }
	        }
	    });
	}.apply(exports, __WEBPACK_AMD_DEFINE_ARRAY__), __WEBPACK_AMD_DEFINE_RESULT__ !== undefined && (module.exports = __WEBPACK_AMD_DEFINE_RESULT__));

/***/ },
/* 11 */
/***/ function(module, exports, __webpack_require__) {

	var __WEBPACK_AMD_DEFINE_ARRAY__, __WEBPACK_AMD_DEFINE_RESULT__;!(__WEBPACK_AMD_DEFINE_ARRAY__ = [ __webpack_require__(4) ], __WEBPACK_AMD_DEFINE_RESULT__ = function( nvd3_config ) {
	    return $.extend( true, {}, nvd3_config, {
	        title       : 'Scatter plot',
	        description : 'Renders a scatter plot using NVD3 hosted at http://www.nvd3.org.',
	        zoomable    : true,
	        groups      : {
	            x : {
	                label       : 'Values for x-axis',
	                type        : 'data_column',
	                is_numeric  : true
	            },
	            y : {
	                label       : 'Values for y-axis',
	                type        : 'data_column',
	                is_numeric  : true
	            }
	        }
	    });
	}.apply(exports, __WEBPACK_AMD_DEFINE_ARRAY__), __WEBPACK_AMD_DEFINE_RESULT__ !== undefined && (module.exports = __WEBPACK_AMD_DEFINE_RESULT__));

/***/ },
/* 12 */
/***/ function(module, exports, __webpack_require__) {

	var __WEBPACK_AMD_DEFINE_ARRAY__, __WEBPACK_AMD_DEFINE_RESULT__;!(__WEBPACK_AMD_DEFINE_ARRAY__ = [ __webpack_require__(4) ], __WEBPACK_AMD_DEFINE_RESULT__ = function( nvd3_config ) {
	    return $.extend( true, {}, nvd3_config, {
	        title       : 'Stacked area',
	        zoomable    : true,
	        description : 'Renders a stacked area using NVD3 hosted at http://www.nvd3.org.',
	        keywords    : 'nvd3 default',
	        groups      : {
	            x : {
	                label       : 'Values for x-axis',
	                type        : 'data_column',
	                is_label    : true,
	                is_auto     : true
	            },
	            y : {
	                label       : 'Values for y-axis',
	                type        : 'data_column',
	                is_numeric  : true
	            }
	        }
	    });
	}.apply(exports, __WEBPACK_AMD_DEFINE_ARRAY__), __WEBPACK_AMD_DEFINE_RESULT__ !== undefined && (module.exports = __WEBPACK_AMD_DEFINE_RESULT__));

/***/ },
/* 13 */
/***/ function(module, exports, __webpack_require__) {

	var __WEBPACK_AMD_DEFINE_ARRAY__, __WEBPACK_AMD_DEFINE_RESULT__;!(__WEBPACK_AMD_DEFINE_ARRAY__ = [ __webpack_require__(4) ], __WEBPACK_AMD_DEFINE_RESULT__ = function( nvd3_config ) {
	    return $.extend( true, {}, nvd3_config, {
	        title       : 'Expanded',
	        zoomable    : true,
	        description : 'Renders an expanded stacked area using NVD3 hosted at http://www.nvd3.org.',
	        keywords    : 'nvd3 default',
	        groups      : {
	            x : {
	                label       : 'Values for x-axis',
	                type        : 'data_column',
	                is_label    : true,
	                is_auto     : true
	            },
	            y : {
	                label       : 'Values for y-axis',
	                type        : 'data_column',
	                is_numeric  : true
	            }
	        }
	    });
	}.apply(exports, __WEBPACK_AMD_DEFINE_ARRAY__), __WEBPACK_AMD_DEFINE_RESULT__ !== undefined && (module.exports = __WEBPACK_AMD_DEFINE_RESULT__));

/***/ },
/* 14 */
/***/ function(module, exports, __webpack_require__) {

	var __WEBPACK_AMD_DEFINE_ARRAY__, __WEBPACK_AMD_DEFINE_RESULT__;!(__WEBPACK_AMD_DEFINE_ARRAY__ = [ __webpack_require__(4) ], __WEBPACK_AMD_DEFINE_RESULT__ = function( nvd3_config ) {
	    return $.extend(true, {}, nvd3_config, {
	        title       : 'Stream',
	        description : 'Renders a stream chart using NVD3 hosted at http://www.nvd3.org.',
	        zoomable    : true,
	        keywords    : 'nvd3 default',
	        showmaxmin  : true,
	        groups      : {
	            x : {
	                label       : 'Values for x-axis',
	                type        : 'data_column',
	                is_label    : true,
	                is_auto     : true
	            },
	            y : {
	                label       : 'Values for y-axis',
	                type        : 'data_column',
	                is_numeric  : true
	            }
	        }
	    });
	}.apply(exports, __WEBPACK_AMD_DEFINE_ARRAY__), __WEBPACK_AMD_DEFINE_RESULT__ !== undefined && (module.exports = __WEBPACK_AMD_DEFINE_RESULT__));

/***/ },
/* 15 */
/***/ function(module, exports, __webpack_require__) {

	var __WEBPACK_AMD_DEFINE_ARRAY__, __WEBPACK_AMD_DEFINE_RESULT__;!(__WEBPACK_AMD_DEFINE_ARRAY__ = [ __webpack_require__(5) ], __WEBPACK_AMD_DEFINE_RESULT__ = function( default_config ) {
	    return $.extend( true, {}, default_config, {
	        title       : 'Pie chart',
	        description : 'Renders a pie chart using NVD3 hosted at http://www.nvd3.org.',
	        library     : 'NVD3',
	        tag         : 'svg',
	        keywords    : 'nvd3 default',
	        datatypes   : [ 'tabular', 'csv' ],
	        exports     : [ 'png', 'svg', 'pdf' ],
	        use_panels  : 'yes',
	        groups      : {
	            label : {
	                label       : 'Labels',
	                type        : 'data_column',
	                is_label    : true,
	                is_auto     : true
	            },
	            y : {
	                label       : 'Values',
	                type        : 'data_column',
	                is_numeric  : true
	            }
	        },
	        settings : {
	            donut_ratio : {
	                label       : 'Donut ratio',
	                help        : 'Determine how large the donut hole will be.',
	                type        : 'float',
	                value       : 0.5,
	                max         : 1,
	                min         : 0.0
	            },
	            show_legend : {
	                label       : 'Show legend',
	                help        : 'Would you like to add a legend?',
	                type        : 'select',
	                display     : 'radiobutton',
	                value       : 'false',
	                data        : [ { label : 'Yes', value : 'true'  }, { label : 'No',  value : 'false' } ]
	            },
	            label_type  : {
	                type        : 'conditional',
	                test_param  : {
	                    name        : 'type',
	                    label       : 'Donut label',
	                    type        : 'select',
	                    value       : 'percent',
	                    help        : 'What would you like to show for each slice?',
	                    data        : [ { value : 'hide',    label : '-- Nothing --' },
	                                    { value : 'key',     label : 'Label column' },
	                                    { value : 'percent', label : 'Percentage' } ]
	                },
	                cases       : [ { value   : 'hide' },
	                                { value   : 'key',     inputs: [ { name     : 'label_outside',
	                                                                   label    : 'Show outside',
	                                                                   help     : 'Would you like to show labels outside the donut?',
	                                                                   type     : 'select',
	                                                                   display  : 'radiobutton',
	                                                                   value    : 'true',
	                                                                   data     : [ { label : 'Yes', value : 'true'  },
	                                                                                { label : 'No',  value : 'false' } ] } ] },
	                                { value   : 'percent', inputs: [ { name     : 'label_outside',
	                                                                   label    : 'Show outside',
	                                                                   help     : 'Would you like to show labels outside the donut?',
	                                                                   type     : 'select',
	                                                                   display  : 'radiobutton',
	                                                                   value    : 'true',
	                                                                   data     : [ { label : 'Yes', value : 'true'  },
	                                                                                { label : 'No',  value : 'false' } ] } ] } ]
	            }
	        }
	    });
	}.apply(exports, __WEBPACK_AMD_DEFINE_ARRAY__), __WEBPACK_AMD_DEFINE_RESULT__ !== undefined && (module.exports = __WEBPACK_AMD_DEFINE_RESULT__));

/***/ },
/* 16 */
/***/ function(module, exports, __webpack_require__) {

	var __WEBPACK_AMD_DEFINE_ARRAY__, __WEBPACK_AMD_DEFINE_RESULT__;!(__WEBPACK_AMD_DEFINE_ARRAY__ = [ __webpack_require__(5) ], __WEBPACK_AMD_DEFINE_RESULT__ = function( default_config ) {
	    return $.extend( true, {}, default_config, {
	        library     : 'NVD3',
	        tag         : 'svg',
	        title       : 'Histogram',
	        description : 'Uses the R-based `charts` tool to derive a histogram and displays it as regular or stacked bar diagram using NVD3 hosted at http://www.nvd3.org.',
	        keywords    : 'nvd3 default',
	        datatype    : 'tabular',
	        groups      : {
	            key : {
	                label       : 'Provide a label',
	                type        : 'text',
	                placeholder : 'Data label',
	                value       : 'Data label'
	            },
	            color : {
	                label       : 'Pick a series color',
	                type        : 'color'
	            },
	            y : {
	                label       : 'Observations',
	                type        : 'data_column',
	                is_numeric  : true
	            }
	        }
	    });
	}.apply(exports, __WEBPACK_AMD_DEFINE_ARRAY__), __WEBPACK_AMD_DEFINE_RESULT__ !== undefined && (module.exports = __WEBPACK_AMD_DEFINE_RESULT__));

/***/ },
/* 17 */
/***/ function(module, exports, __webpack_require__) {

	var __WEBPACK_AMD_DEFINE_ARRAY__, __WEBPACK_AMD_DEFINE_RESULT__;!(__WEBPACK_AMD_DEFINE_ARRAY__ = [ __webpack_require__(5) ], __WEBPACK_AMD_DEFINE_RESULT__ = function( default_config ) {
	    return $.extend(true, {}, default_config, {
	        library     : 'NVD3',
	        tag         : 'svg',
	        title       : 'Discrete Histogram',
	        description : 'Uses the R-based `charts` tool to derive a histogram for discrete data e.g. text labels. The result is displayed as regular or stacked bar diagram using NVD3 hosted at http://www.nvd3.org.',
	        keywords    : 'nvd3',
	        datatype    : 'tabular',
	        groups      : {
	            x : {
	                label       : 'Observations',
	                type        : 'data_column',
	                is_label    : true
	            }
	        }
	    });
	}.apply(exports, __WEBPACK_AMD_DEFINE_ARRAY__), __WEBPACK_AMD_DEFINE_RESULT__ !== undefined && (module.exports = __WEBPACK_AMD_DEFINE_RESULT__));

/***/ },
/* 18 */
/***/ function(module, exports, __webpack_require__) {

	var __WEBPACK_AMD_DEFINE_ARRAY__, __WEBPACK_AMD_DEFINE_RESULT__;!(__WEBPACK_AMD_DEFINE_ARRAY__ = [ __webpack_require__(19) ], __WEBPACK_AMD_DEFINE_RESULT__ = function( plot_config ) {
	    return $.extend( true, {}, plot_config, {
	        title       : 'Bar diagram',
	        description : 'Renders a bar diagram using jqPlot hosted at http://www.jqplot.com.',
	        groups      : {
	            x : {
	                label       : 'Values for x-axis',
	                type        : 'data_column',
	                is_label    : true,
	                is_auto     : true
	            },
	            y : {
	                label       : 'Values for y-axis',
	                type        : 'data_column',
	                is_numeric  : true
	            }
	        }
	    });
	}.apply(exports, __WEBPACK_AMD_DEFINE_ARRAY__), __WEBPACK_AMD_DEFINE_RESULT__ !== undefined && (module.exports = __WEBPACK_AMD_DEFINE_RESULT__));

/***/ },
/* 19 */
/***/ function(module, exports, __webpack_require__) {

	var __WEBPACK_AMD_DEFINE_ARRAY__, __WEBPACK_AMD_DEFINE_RESULT__;!(__WEBPACK_AMD_DEFINE_ARRAY__ = [ __webpack_require__(5) ], __WEBPACK_AMD_DEFINE_RESULT__ = function( default_config ) {
	    return $.extend(true, {}, default_config, {
	        title       : '',
	        library     : 'jqPlot',
	        tag         : 'div',
	        zoomable    : true,
	        keywords    : 'jqplot',
	        exports     : [ 'png' ],
	        settings    : {
	            x_axis_grid : {
	                label       : 'Axis grid',
	                help        : 'Would you like to show grid lines for the X axis?',
	                type        : 'boolean'
	            },
	            y_axis_grid : {
	                label       : 'Axis grid',
	                help        : 'Would you like to show grid lines for the Y axis?',
	                type        : 'boolean'
	            }
	        }
	    });
	}.apply(exports, __WEBPACK_AMD_DEFINE_ARRAY__), __WEBPACK_AMD_DEFINE_RESULT__ !== undefined && (module.exports = __WEBPACK_AMD_DEFINE_RESULT__));

/***/ },
/* 20 */
/***/ function(module, exports, __webpack_require__) {

	var __WEBPACK_AMD_DEFINE_ARRAY__, __WEBPACK_AMD_DEFINE_RESULT__;!(__WEBPACK_AMD_DEFINE_ARRAY__ = [ __webpack_require__(19) ], __WEBPACK_AMD_DEFINE_RESULT__ = function( plot_config ) {
	    return $.extend( true, {}, plot_config, {
	        title       : 'Box plot',
	        library     : 'jqPlot',
	        description : 'Processes tabular data using R and renders a box plot using jqPlot hosted at http://www.jqplot.com.',
	        tag         : 'div',
	        keywords    : 'jqplot default',
	        groups      : {
	            y : {
	                label       : 'Observations',
	                type        : 'data_column',
	                is_numeric  : true
	            }
	        }
	    });
	}.apply(exports, __WEBPACK_AMD_DEFINE_ARRAY__), __WEBPACK_AMD_DEFINE_RESULT__ !== undefined && (module.exports = __WEBPACK_AMD_DEFINE_RESULT__));

/***/ },
/* 21 */
/***/ function(module, exports, __webpack_require__) {

	var __WEBPACK_AMD_DEFINE_ARRAY__, __WEBPACK_AMD_DEFINE_RESULT__;!(__WEBPACK_AMD_DEFINE_ARRAY__ = [ __webpack_require__(19) ], __WEBPACK_AMD_DEFINE_RESULT__ = function( default_config ) {
	    return $.extend( true, {}, default_config, {
	        title       : 'Discrete Histogram',
	        description : 'Derives a discrete histogram from tabular data using R and renders a regular bar diagram using jqPlot hosted at http://www.jqplot.com.',
	        keywords    : 'jqplot default',
	        groups      : {
	            x : {
	                label       : 'Observations',
	                type        : 'data_column',
	                is_label    : true
	            }
	        }
	    });
	}.apply(exports, __WEBPACK_AMD_DEFINE_ARRAY__), __WEBPACK_AMD_DEFINE_RESULT__ !== undefined && (module.exports = __WEBPACK_AMD_DEFINE_RESULT__));

/***/ },
/* 22 */
/***/ function(module, exports, __webpack_require__) {

	var __WEBPACK_AMD_DEFINE_ARRAY__, __WEBPACK_AMD_DEFINE_RESULT__;!(__WEBPACK_AMD_DEFINE_ARRAY__ = [ __webpack_require__(19) ], __WEBPACK_AMD_DEFINE_RESULT__ = function( plot_config ) {
	    return $.extend( true, {}, plot_config, {
	        title       : 'Line chart',
	        description : 'Renders a line chart using jqPlot hosted at http://www.jqplot.com.',
	        groups      : {
	            x : {
	                label       : 'Values for x-axis',
	                type        : 'data_column',
	                is_label    : true,
	                is_auto     : true
	            },
	            y : {
	                label       : 'Values for y-axis',
	                type        : 'data_column',
	                is_numeric  : true
	            }
	        }
	    });
	}.apply(exports, __WEBPACK_AMD_DEFINE_ARRAY__), __WEBPACK_AMD_DEFINE_RESULT__ !== undefined && (module.exports = __WEBPACK_AMD_DEFINE_RESULT__));

/***/ },
/* 23 */
/***/ function(module, exports, __webpack_require__) {

	var __WEBPACK_AMD_DEFINE_ARRAY__, __WEBPACK_AMD_DEFINE_RESULT__;!(__WEBPACK_AMD_DEFINE_ARRAY__ = [ __webpack_require__(19) ], __WEBPACK_AMD_DEFINE_RESULT__ = function( plot_config ) {
	    return $.extend( true, {}, plot_config, {
	        title       : 'Scatter plot',
	        description : 'Renders a scatter plot using jqPlot hosted at http://www.jqplot.com.',
	        groups      : {
	            x : {
	                label       : 'Values for x-axis',
	                type        : 'data_column',
	                is_numeric  : true
	            },
	            y : {
	                label       : 'Values for y-axis',
	                type        : 'data_column',
	                is_numeric  : true
	            }
	        }
	    });
	}.apply(exports, __WEBPACK_AMD_DEFINE_ARRAY__), __WEBPACK_AMD_DEFINE_RESULT__ !== undefined && (module.exports = __WEBPACK_AMD_DEFINE_RESULT__));

/***/ },
/* 24 */
/***/ function(module, exports, __webpack_require__) {

	var __WEBPACK_AMD_DEFINE_ARRAY__, __WEBPACK_AMD_DEFINE_RESULT__;!(__WEBPACK_AMD_DEFINE_ARRAY__ = [], __WEBPACK_AMD_DEFINE_RESULT__ = function() {
	    return {
	        title       : 'Multiple Sequence Alignment',
	        library     : 'BioJS',
	        datatypes   : [ 'txt' ],
	        keywords    : 'biojs',
	        description : 'The MSA viewer is a modular, reusable component to visualize large MSAs interactively on the web.',
	        settings    : {
	            conserv: { label :'Show conservation', help : 'Do you want to display a bar diagram indicating sequence conservation?', type : 'boolean', value: 'true' },
	            overviewbox: { label :'Show overview box', help : 'Do you want to display the overview box below the sequence alignments?', type : 'boolean', value: 'true' },
	            menu: { label :'Show interactive menu', help : 'Do you want to show a menu for interactive configuration?', type : 'boolean', value: 'true' }
	        }
	    }
	}.apply(exports, __WEBPACK_AMD_DEFINE_ARRAY__), __WEBPACK_AMD_DEFINE_RESULT__ !== undefined && (module.exports = __WEBPACK_AMD_DEFINE_RESULT__));

/***/ },
/* 25 */
/***/ function(module, exports, __webpack_require__) {

	var __WEBPACK_AMD_DEFINE_ARRAY__, __WEBPACK_AMD_DEFINE_RESULT__;!(__WEBPACK_AMD_DEFINE_ARRAY__ = [], __WEBPACK_AMD_DEFINE_RESULT__ = function() {
	    return {
	        title       : 'RNA Structure Viewer',
	        library     : 'BioJS',
	        datatypes   : [ 'dbn' ],
	        keywords    : 'biojs',
	        description : 'Renders RNA structures hosted at https://github.com/bene200/drawrnajs.'
	    }
	}.apply(exports, __WEBPACK_AMD_DEFINE_ARRAY__), __WEBPACK_AMD_DEFINE_RESULT__ !== undefined && (module.exports = __WEBPACK_AMD_DEFINE_RESULT__));

/***/ },
/* 26 */
/***/ function(module, exports, __webpack_require__) {

	var __WEBPACK_AMD_DEFINE_ARRAY__, __WEBPACK_AMD_DEFINE_RESULT__;!(__WEBPACK_AMD_DEFINE_ARRAY__ = [], __WEBPACK_AMD_DEFINE_RESULT__ = function() {
	    return {
	        title       : 'Phylogenetic Tree Visualization',
	        library     : 'BioJS',
	        datatypes   : [ 'nhx' ],
	        keywords    : 'biojs phylogenetic tree',
	        description : 'A performant, reusable, and extensible tree visualisation library for the web hosted at: http://biojs.io/d/phylocanvas',
	        settings    : {
	           tree_type : {
	                label   : 'Tree types',
	                help    : 'Select a tree type.',
	                type    : 'select',
	                display : 'radio',
	                value   : 'rectangular',
	                data    : [ { label : 'Circular', value : 'circular' },
	                            { label : 'Diagonal', value: 'diagonal' },
	                            { label : 'Hierarchial', value : 'hierarchical' },
	                            { label : 'Radial', value : 'radial' },
	                            { label : 'Rectangular', value : 'rectangular' } ]
	            },
	            edge_color : {
	                label : 'Select a color for the tree',
	                type  : 'color',
	                value : '#548DB8'
	            },
	            highlighted_color: {
	                label : 'Select a color for the highlighted branch of tree',
	                type  : 'color',
	                value : '#548DB8'
	            },
	            selected_color: {
	                label : 'Select a color for the selected branch of tree',
	                type  : 'color',
	                value : '#00b050'
	            },
	            collapse_branch : {
	                label   : 'Collapse the selected branch',
	                help    : 'Select true to collapse the selected branch.',
	                type    : 'select',
	                display : 'radio',
	                value   : 'false',
	                data    : [ { label : 'True', value : 'true' },
	                            { label : 'False', value : 'false' } ]
	            },
	            prune_branch : {
	                label   : 'Prune the selected branch',
	                help    : 'Select true to prune the selected branch.',
	                type    : 'select',
	                display : 'radio',
	                value   : 'false',
	                data    : [ { label : 'True', value : 'true' },
	                            { label : 'False', value : 'false' } ]
	            },
	            show_labels: {
	                label   : 'Show/Hide labels',
	                help    : 'Select false to hide labels.',
	                type    : 'select',
	                display : 'radio',
	                value   : 'true',
	                data    : [ { label : 'True', value : 'true' },
	                            { label : 'False', value : 'false' } ]
	            },
	            align_labels: {
	                label   : 'Align labels',
	                help    : 'Select to align the labels of tree. Supported with rectangular, circular, and hierarchical tree types.',
	                type    : 'select',
	                display : 'radio',
	                value   : 'true',
	                data    : [ { label : 'True', value : 'true' },
	                            { label : 'False', value : 'false' } ]
	            },
	            show_bootstrap : {
	                label   : 'Show bootstrap confidence values',
	                help    : 'Select true to show bootstrap confidence values.',
	                type    : 'select',
	                display : 'radio',
	                value   : 'false',
	                data    : [ { label : 'True', value : 'true' },
	                            { label : 'False', value : 'false' } ]
	            },
	            node_shape : {
	                label   : 'Node shapes for leaves',
	                help    : 'Select a node shape for leaves.',
	                type    : 'select',
	                display : 'radio',
	                value   : 'circle',
	                data    : [ { label : 'Circle', value : 'circle' },
	                            { label : 'Square', value: 'square' },
	                            { label : 'Star', value : 'star' },
	                            { label : 'Triangle', value : 'triangle' } ]
	            }
	        }
	    }
	}.apply(exports, __WEBPACK_AMD_DEFINE_ARRAY__), __WEBPACK_AMD_DEFINE_RESULT__ !== undefined && (module.exports = __WEBPACK_AMD_DEFINE_RESULT__));


/***/ },
/* 27 */
/***/ function(module, exports, __webpack_require__) {

	var __WEBPACK_AMD_DEFINE_ARRAY__, __WEBPACK_AMD_DEFINE_RESULT__;!(__WEBPACK_AMD_DEFINE_ARRAY__ = [], __WEBPACK_AMD_DEFINE_RESULT__ = function() {
	    return {
	        title       : 'Example',
	        library     : 'Custom',
	        tag         : 'svg',
	        keywords    : 'others',
	        datatypes   : [ 'tabular', 'csv' ],
	        use_panels  : 'both',
	        description : 'This is a developer example which demonstrates how to implement and configure a basic d3-based plugin for charts.',
	        groups      : {
	            x : { type : 'data_column', is_numeric : true, label : 'Bubble x-position' },
	            y : { type : 'data_column', is_numeric : true, label : 'Bubble y-position' },
	            z : { type : 'data_column', is_numeric : true, label : 'Bubble size' }
	        }
	    }
	}.apply(exports, __WEBPACK_AMD_DEFINE_ARRAY__), __WEBPACK_AMD_DEFINE_RESULT__ !== undefined && (module.exports = __WEBPACK_AMD_DEFINE_RESULT__));

/***/ },
/* 28 */
/***/ function(module, exports, __webpack_require__) {

	var __WEBPACK_AMD_DEFINE_ARRAY__, __WEBPACK_AMD_DEFINE_RESULT__;!(__WEBPACK_AMD_DEFINE_ARRAY__ = [ __webpack_require__(5) ], __WEBPACK_AMD_DEFINE_RESULT__ = function( default_config ) {
	    return $.extend( true, {}, default_config, {
	        title       : 'Heatmap',
	        description : 'Renders a heatmap from matrix data provided in 3-column format (x, y, observation).',
	        library     : 'Custom',
	        tag         : 'svg',
	        keywords    : 'others default',
	        zoomable    : true,
	        exports     : [ 'png', 'svg', 'pdf' ],
	        use_panels  : 'yes',
	        groups      : {
	            x : {
	                label       : 'Column labels',
	                type        : 'data_column',
	                is_label    : true,
	                is_numeric  : true
	            },
	            y : {
	                label       : 'Row labels',
	                type        : 'data_column',
	                is_label    : true,
	                is_numeric  : true
	            },
	            z : {
	                label       : 'Observation',
	                type        : 'data_column',
	                is_numeric  : true
	            }
	        },
	        settings    : {
	            color_set : {
	                label       : 'Color scheme',
	                help        : 'Select a color scheme for your heatmap',
	                type        : 'select',
	                value       : 'jet',
	                data        : [ { label : 'Cold-to-Hot',                value : 'hot' },
	                                { label : 'Cool',                       value : 'cool' },
	                                { label : 'Copper',                     value : 'copper' },
	                                { label : 'Gray scale',                 value : 'gray' },
	                                { label : 'Jet',                        value : 'jet' },
	                                { label : 'No-Green',                   value : 'no_green' },
	                                { label : 'Ocean',                      value : 'ocean' },
	                                { label : 'Polar',                      value : 'polar' },
	                                { label : 'Red-to-Green',               value : 'redgreen' },
	                                { label : 'Red-to-green (saturated)',   value : 'red2green' },
	                                { label : 'Relief',                     value : 'relief' },
	                                { label : 'Seismograph',                value : 'seis' },
	                                { label : 'Sealand',                    value : 'sealand' },
	                                { label : 'Split',                      value : 'split' },
	                                { label : 'Wysiwyg',                    value : 'wysiwyg' } ]
	            },
	            url_template: {
	                label       : 'Url template',
	                help        : 'Enter a url to link the labels with external sources. Use __LABEL__ as placeholder.',
	                type        : 'text',
	                value       : '',
	                placeholder : 'http://someurl.com?id=__LABEL__'
	            }
	        }
	    });
	}.apply(exports, __WEBPACK_AMD_DEFINE_ARRAY__), __WEBPACK_AMD_DEFINE_RESULT__ !== undefined && (module.exports = __WEBPACK_AMD_DEFINE_RESULT__));

/***/ },
/* 29 */
/***/ function(module, exports, __webpack_require__) {

	var __WEBPACK_AMD_DEFINE_ARRAY__, __WEBPACK_AMD_DEFINE_RESULT__;!(__WEBPACK_AMD_DEFINE_ARRAY__ = [ __webpack_require__(28) ], __WEBPACK_AMD_DEFINE_RESULT__ = function( default_config ) {
	    return $.extend( true, {}, default_config, {
	        title       : 'Clustered Heatmap',
	        description : 'Applies hierarchical clustering to a matrix using R. The data has to be provided in 3-column format. The result is displayed as clustered heatmap.',
	        keywords    : 'others default'
	    });
	}.apply(exports, __WEBPACK_AMD_DEFINE_ARRAY__), __WEBPACK_AMD_DEFINE_RESULT__ !== undefined && (module.exports = __WEBPACK_AMD_DEFINE_RESULT__));

/***/ },
/* 30 */
/***/ function(module, exports, __webpack_require__) {

	var __WEBPACK_AMD_DEFINE_ARRAY__, __WEBPACK_AMD_DEFINE_RESULT__;!(__WEBPACK_AMD_DEFINE_ARRAY__ = [], __WEBPACK_AMD_DEFINE_RESULT__ = function() {
	    return {
	        title       : 'Cytoscape',
	        library     : 'Cytoscape',
	        datatypes   : [ 'sif', 'json' ],
	        keywords    : 'cytoscape graph nodes edges',
	        description : 'A viewer based on graph theory/ network library for analysis and visualisation hosted at http://js.cytoscape.org.',
	        settings    : {
	            curve_style : {
	                label   : 'Curve style',
	                help    : 'Select a curving method used to separate two or more edges between two nodes.',
	                type    : 'select',
	                display : 'radio',
	                value   : 'haystack',
	                data    : [ { label : 'Haystack', value : 'haystack' },
	                            { label : 'Bezier', value : 'bezier' },
	                            { label : 'Unbundled bezier', value : 'unbundled-bezier' },
	                            { label : 'Segments', value: 'segments' } ]
	            },
	            layout_name : {
	                label   : 'Layout name',
	                help    : 'Select a kind of position of nodes in graph.',
	                type    : 'select',
	                display : 'radio',
	                value   : 'haystack',
	                data    : [ { label : 'Breadth First', value : 'breadthfirst' },
	                            { label : 'Circle', value : 'circle' },
	                            { label : 'Concentric', value : 'concentric' },
	                            { label : 'Cose', value : 'cose' },
	                            { label : 'Grid', value : 'grid' },
	                            { label : 'Null', value: 'null' },
	                            { label : 'Preset', value : 'preset' },
	                            { label : 'Random', value : 'random' } ]
	            },
	            directed : {
	                label   : 'Directed/Undirected',
	                help    : 'Select a kind of edge.',
	                type    : 'select',
	                display : 'radio',
	                value   : '',
	                data    : [ { label : 'Directed', value : 'triangle' },
	                            { label : 'Undirected', value : '' } ]
	            },
	            search_algorithm : {
	                label   : 'Graph algorithms',
	                help    : 'Select a search algorithm. For Breadth First Search and Depth First Search, please click on any node of the graph. For A*, please click on two nodes, one for the root and another for the destination.',
	                type    : 'select',
	                display : 'radio',
	                value   : '',
	                data    : [ { label : 'Breadth First Search', value : 'bfs' },
	                            { label : 'Depth First Search', value : 'dfs' },
	                            { label : 'Minimum Spanning Tree (Kruskal)', value : 'kruskal' },
	                            { label : 'A*', value : 'astar' },
	                            { label : 'None', value : '' } ]
	            },
	            graph_traversal: {
	                label   : 'Graph traversal',
	                help    : 'To select a graph traversal type, please click on any node of the graph',
	                type    : 'select',
	                display : 'radio',
	                value   : '',
	                data    : [ { label : 'Successors', value : 'successors' },
	                            { label : 'Predecessors', value : 'predecessors' },
	                            { label : 'Outgoers', value : 'outgoers' },
	                            { label : 'Incomers', value : 'incomers' },
	                            { label : 'Roots', value : 'roots' },
	                            { label : 'Leaves', value : 'leaves' },
	                            { label : 'None', value : '' } ]
	            },
	            color_picker_nodes : {
	                label : 'Select a color for nodes',
	                type  : 'color',
	                value : '#548DB8'
	            },
	            color_picker_edges : {
	                label : 'Select a color for edges',
	                type  : 'color',
	                value : '#A5A5A5'
	            },
	            color_picker_highlighted : {
	                label : 'Select a color for highlighted nodes and edges',
	                type  : 'color',
	                value : '#C00000'
	            }
	        }
	    }
	}.apply(exports, __WEBPACK_AMD_DEFINE_ARRAY__), __WEBPACK_AMD_DEFINE_RESULT__ !== undefined && (module.exports = __WEBPACK_AMD_DEFINE_RESULT__));


/***/ },
/* 31 */
/***/ function(module, exports, __webpack_require__) {

	var __WEBPACK_AMD_DEFINE_ARRAY__, __WEBPACK_AMD_DEFINE_RESULT__;!(__WEBPACK_AMD_DEFINE_ARRAY__ = [], __WEBPACK_AMD_DEFINE_RESULT__ = function() {
	    return {
	        title       : 'PV Protein Viewer',
	        library     : 'PV',
	        datatypes   : [ 'pdb' ],
	        keywords    : 'pv protein viewer pdb structure',
	        description : 'PV is a pdb/protein viewer hosted at https://biasmv.github.io/pv/.',
	        settings    : {
	            quality : {
	                label   : 'Quality',
	                help    : 'Select the rendering quality.',
	                type    : 'select',
	                display : 'radio',
	                value   : 'medium',
	                data    : [ { label : 'High', value : 'high' }, { label : 'Medium', value : 'medium' }, { label : 'Low', value : 'low' } ]
	            },
	            viewer : {
	                type        : 'conditional',
	                test_param  : {
	                    name    : 'mode',
	                    label   : 'Display mode',
	                    type    : 'select',
	                    display : 'radio',
	                    value   : 'cartoon',
	                    help    : 'Select the rendering mode.',
	                    data    : [ { label : 'Cartoon',        value : 'cartoon' },
	                                { label : 'Lines',          value : 'lines' },
	                                { label : 'Points',         value : 'points' },
	                                { label : 'Spheres',        value : 'spheres' },
	                                { label : 'Trace',          value : 'trace' },
	                                { label : 'Trace (line)',   value : 'lineTrace' },
	                                { label : 'Trace (smooth)', value : 'sline' },
	                                { label : 'Tube',           value : 'tube' } ]
	                },
	                cases       : [ { value : 'cartoon', inputs: [ {
	                                    name  : 'radius',
	                                    label : 'Radius',
	                                    help  : 'Radius of tube profile. Also influences the profile thickness for helix and strand profiles.',
	                                    type  : 'float',
	                                    min   : 0.1,
	                                    max   : 3,
	                                    value : 0.3
	                                } ] },
	                                { value : 'lines', inputs: [ {
	                                    name  : 'lineWidth',
	                                    label : 'Line width',
	                                    help  : 'Specify the line width.',
	                                    type  : 'float',
	                                    min   : 0.1,
	                                    max   : 10,
	                                    value : 4
	                                } ] },
	                                { value : 'points', inputs: [ {
	                                    name  : 'pointSize',
	                                    label : 'Point size',
	                                    help  : 'Specify the point size.',
	                                    type  : 'float',
	                                    min   : 0.1,
	                                    max   : 10,
	                                    value : 1
	                                } ] },
	                                { value : 'spheres' },
	                                { value : 'trace', inputs: [ {
	                                    name  : 'radius',
	                                    label : 'Radius',
	                                    help  : 'Specify the tube radius.',
	                                    type  : 'float',
	                                    min   : 0.1,
	                                    max   : 3,
	                                    value : 0.3
	                                } ] },
	                                { value : 'lineTrace', inputs: [ {
	                                    name  : 'lineWidth',
	                                    label : 'Line width',
	                                    help  : 'Specify the line width.',
	                                    type  : 'float',
	                                    min   : 0.1,
	                                    max   : 10,
	                                    value : 4
	                                } ] },
	                                { value : 'sline', inputs: [ {
	                                    name  : 'lineWidth',
	                                    label : 'Line width',
	                                    help  : 'Specify the line width.',
	                                    type  : 'float',
	                                    min   : 0.1,
	                                    max   : 10,
	                                    value : 4
	                                } ] },
	                                { value : 'tube', inputs: [ {
	                                    name  : 'radius',
	                                    label : 'Radius',
	                                    help  : 'Specify the tube radius.',
	                                    type  : 'float',
	                                    min   : 0.1,
	                                    max   : 3,
	                                    value : 0.3
	                                } ] }
	                            ]
	            }
	        }
	    }
	}.apply(exports, __WEBPACK_AMD_DEFINE_ARRAY__), __WEBPACK_AMD_DEFINE_RESULT__ !== undefined && (module.exports = __WEBPACK_AMD_DEFINE_RESULT__));

/***/ },
/* 32 */
/***/ function(module, exports, __webpack_require__) {

	var __WEBPACK_AMD_DEFINE_ARRAY__, __WEBPACK_AMD_DEFINE_RESULT__;!(__WEBPACK_AMD_DEFINE_ARRAY__ = [], __WEBPACK_AMD_DEFINE_RESULT__ = function() {
	    return {
	        title       : 'Venn Diagram',
	        library     : 'benfred',
	        tag         : 'svg',
	        datatypes   : [ 'tabular', 'csv' ],
	        keywords    : 'default venn overlap circle',
	        description : 'A javascript library for laying out area proportional venn and euler diagrams hosted at https://github.com/benfred/venn.js.',
	        exports     : [ 'png', 'svg', 'pdf' ],
	        groups      : {
	            key: {
	                label       : 'Provide a label',
	                type        : 'text',
	                placeholder : 'Data label',
	                value       : 'Data label'
	            },
	            observation : {
	                label       : 'Column with observations',
	                type        : 'data_column',
	                is_label    : true
	            }
	        }
	    }
	}.apply(exports, __WEBPACK_AMD_DEFINE_ARRAY__), __WEBPACK_AMD_DEFINE_RESULT__ !== undefined && (module.exports = __WEBPACK_AMD_DEFINE_RESULT__));

/***/ },
/* 33 */
/***/ function(module, exports, __webpack_require__) {

	var __WEBPACK_AMD_DEFINE_ARRAY__, __WEBPACK_AMD_DEFINE_RESULT__;!(__WEBPACK_AMD_DEFINE_ARRAY__ = [], __WEBPACK_AMD_DEFINE_RESULT__ = function() {
	    return {
	        title       : 'NGL Viewer',
	        library     : 'NGL',
	        datatypes   : [ 'pdb' ],
	        keywords    : 'NGL protein viewer pdb',
	        description : 'NGL Viewer is a WebGL based molecular visualization hosted at http://arose.github.io/ngl/.',
	        settings    : {
	            quality : {
	                label   : 'Quality',
	                help    : 'Select the rendering quality.',
	                type    : 'select',
	                display : 'radio',
	                value   : 'medium',
	                data    : [ { label : 'High', value : 'high' }, { label : 'Medium', value : 'medium' }, { label : 'Low', value : 'low' } ]
	            },
	            viewer : {
	                type        : 'conditional',
	                test_param  : {
	                    name    : 'mode',
	                    label   : 'Display mode',
	                    type    : 'select',
	                    display : 'radio',
	                    value   : 'cartoon',
	                    help    : '',
	                    data    : [ { label : 'Axes', value : 'axes' },
	                                { label : 'Base', value : 'base' },
	                                { label : 'Backbone', value : 'backbone' },
	                                { label : 'Ball+Stick', value : 'ball+stick' },
	                                { label : 'Cartoon', value : 'cartoon' },
	                                { label : 'Contact', value : 'contact' },
	                                { label : 'Helixorient', value : 'helixorient' },
	                                { label : 'Hyperball', value : 'hyperball' },
	                                { label : 'Label', value : 'label' },
	                                { label : 'Licorice', value : 'licorice' },
	                                { label : 'Line', value : 'line' },
	                                { label : 'Point', value : 'point' },
	                                { label : 'Ribbon', value : 'ribbon' },
	                                { label : 'Rocket', value : 'rocket' },
	                                { label : 'Rope', value : 'rope' },
	                                { label : 'Spacefill', value : 'spacefill' },
	                                { label : 'Surface', value : 'surface' },
	                                { label : 'Trace', value : 'trace' },
	                                { label : 'Tube', value : 'tube' },
	                                { label : 'Unitcell', value : 'unitcell' } ]
	                }
	            },
	            radius: {
	                name  : 'radius',
	                label : 'Radius',
	                help  : 'Select a number providing a fixed radius used for rendering the representation.',
	                type  : 'float',
	                min   : 0.001,
	                max   : 10.0,
	                value : 0.05
	            },
	            scale: {
	                name  : 'scale',
	                label : 'Scale',
	                help  : 'Select a number that scales the value defined by the *radius* parameter.',
	                type  : 'float',
	                min   : 0.001,
	                max   : 10.0,
	                value : 0.7
	            },
	            colorscheme : {
	                label   : 'Color Scheme',
	                help    : 'Select color scheme of the molecule scene.',
	                type    : 'select',
	                display : 'radio',
	                value   : 'atomindex',
	                data    : [ { label : 'Element', value : 'element' },
	                            { label : 'Picking', value : 'picking' },
	                            { label : 'Random', value : 'random' },
	                            { label : 'Uniform', value : 'uniform' },
	                            { label : 'Atomindex', value : 'atomindex' },
	                            { label : 'Residue Index', value : 'residueindex' },
	                            { label : 'Chain Index', value : 'chainindex' },
	                            { label : 'Chain Name', value : 'chainname' },
	                            { label : 'Chain Id', value : 'chainid' },
	                            { label : 'Polymer', value : 'polymer' },
	                            { label : 'Model Index', value : 'modelindex' },
	                            { label : 'Entity Type', value : 'entitytype' },
	                            { label : 'Molecule Type', value : 'moleculetype' },
	                            { label : 'Secondary Structure', value : 'sstruc' },
	                            { label : 'Bfactor', value : 'bfactor' },
	                            { label : 'Resname', value : 'resname' },
	                            { label : 'Hydrophobicity', value : 'hydrophobicity' },
	                            { label : 'Value', value : 'value' },
	                            { label : 'Volume', value : 'volume' },
	                            { label : 'Occupancy', value : 'occupancy' } ]
	            },
	            backcolor : {
	                label   : 'Background Color',
	                help    : 'Select background color of the viewer.',
	                type    : 'select',
	                display : 'radio',
	                value   : 'white',
	                data    : [ { label : 'Light', value : 'white' }, { label : 'Dark', value : 'black' } ]
	            },
	            spin : {
	                label   : 'Spin',
	                help    : 'Spin the molecule view.',
	                type    : 'select',
	                display : 'radio',
	                value   : false,
	                data    : [ { label : 'On', value : true }, { label : 'Off', value : false } ]
	            },
	            assembly : {
	                label   : 'Assembly',
	                help    : 'Select a name of an assembly object.',
	                type    : 'select',
	                display : 'radio',
	                value   : 'default',
	                data    : [ { label : 'Default', value : 'default' }, { label : 'AU', value : '' },
	                            { label : 'BU1', value : 'BU1' }, { label : 'UNITCELL', value : 'UNITCELL' },
	                            { label : 'SUPERCELL', value: 'SUPERCELL' } ]
	            },
	            opacity : {
	                name  : 'opacity',
	                label : 'Opacity',
	                help  : 'Select opacity for the molecule scene.',
	                type  : 'float',
	                min   : 0.0,
	                max   : 1.0,
	                value : 1.0
	
	            }
	        }
	    }
	}.apply(exports, __WEBPACK_AMD_DEFINE_ARRAY__), __WEBPACK_AMD_DEFINE_RESULT__ !== undefined && (module.exports = __WEBPACK_AMD_DEFINE_RESULT__));


/***/ }
/******/ ])});;
//# sourceMappingURL=registry.js.map