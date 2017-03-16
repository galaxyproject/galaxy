define( [ 'utilities/utils', 'utilities/sifjson', 'plugins/cytoscape/cytoscape' ], function( Utils, SIF, Cytoscape ) {
    return Backbone.Model.extend({
        initialize: function( options ) {
            var chart    = options.chart,
                dataset  = options.dataset,
                settings = options.chart.settings,
                data_content = null,
                cytoscape = null,
                self = this;
            Utils.get( {
                url     : dataset.download_url,
                success : function( content ) {
                    if( dataset.file_ext === "sif" ) {
                        data_content = SIF.SIFJS.parse( content ).content;
                    }
                    else {
                        data_content = content;
                    }
                    try {
                        cytoscape = Cytoscape({
			    container: document.getElementById( options.targets[ 0 ] ),
			    boxSelectionEnabled: false,
			    autounselectify: true,
			    layout: {
			        name: settings.get( 'layout_name' )
			    },
                            minZoom: parseFloat( settings.get( 'min_zoom' ) ),
                            maxZoom: parseFloat( settings.get( 'max_zoom' ) ),
			    style: [{
			        selector: 'node',
			        style: {
				    'background-color': '#30c9bc',
                                    'height': 20,
                                    'width': 20,
                                    'opacity': 1,
                                    'content': 'data(id)'
			        }
			    },
			    {
			        selector: 'edge',
			        style: {
				    'curve-style': settings.get( 'curve_style' ),
				    'haystack-radius': 0,
				    'width': 5,
				    'opacity': 1,
				    'line-color': '#ddd',
                                    'target-arrow-shape': settings.get( 'directed' )
			        }
			    },
                            {
                                selector: '.bfspath',
			        style: {
				    'background-color': '#336699', // #61bffc
                                    'line-color': '#336699',
                                    'target-arrow-color': '#336699',
                                    'transition-property': 'background-color, line-color, target-arrow-color',
                                    'transition-duration': '0.75s'
			        }
			    }],
                            elements: data_content
                        });
                        
                        // Register tap event on graph nodes
                        // Right now on tapping on any node, BFS starts from that node
                        cytoscape.$('node').on('tap', function( e ) {
                            var ele = e.cyTarget;
                            self.run_bfs(cytoscape, ele.id());
                        });
                        
                        chart.state( 'ok', 'Chart drawn.' );
                        // Re-renders the graph view when window is resized
                        $( window ).resize( function() { cytoscape.layout(); } );
                    } catch( err ) {
                        chart.state( 'failed', err );
                    }
                    options.process.resolve();
                },
                error: function() {
                    chart.state( 'failed', 'Failed to access dataset.' );
                    options.process.resolve();
                }
            });
        },
        run_bfs: function( cytoscape, root_id ) {
            var bfs = cytoscape.elements().bfs('#' + root_id, function(){}, true);
            var i = 0, timeOut = 1500;
            var selectNextElement = function() {
                if( i < bfs.path.length ) {
                    // Add css class for the selected edge
                    bfs.path[i].addClass('bfspath');
                    i++;
                    setTimeout(selectNextElement, timeOut);
                }
            };
            selectNextElement();
        }
    });
});
