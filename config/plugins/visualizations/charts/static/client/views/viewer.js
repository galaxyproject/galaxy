/** This class renders the chart viewer which encapsulates the chart viewport. */
define( [ 'utils/utils', 'mvc/ui/ui-misc', 'mvc/ui/ui-portlet', 'plugin/views/viewport', 'plugin/components/screenshot' ],
    function( Utils, Ui, Portlet, Viewport, Screenshot ) {
    return Backbone.View.extend({
        initialize: function(app, options){
            var self = this;
            this.app = app;
            this.chart = this.app.chart;
            this.viewport = new Viewport( app );
            this.message = new Ui.Message();
            this.export_button = new Ui.ButtonMenu({
                icon    : 'fa-camera',
                title   : 'Export',
                tooltip : 'Export/Download Visualization'
            });
            this.export_button.addMenu({
                key         : 'png',
                title       : 'Save as PNG',
                icon        : 'fa-file',
                onclick     : function() {
                    self._wait( self.chart, function() {
                        Screenshot.createPNG({
                            $el     : self.viewport.$el,
                            title   : self.chart.get( 'title' ),
                            error   : function( err ) {
                                self.message.update( { message: err, status: 'danger' } );
                            }
                        });
                    });
                }
            });
            this.export_button.addMenu({
                key         : 'svg',
                title       : 'Save as SVG',
                icon        : 'fa-file-text-o',
                onclick     : function() {
                    self._wait( self.chart, function() {
                        Screenshot.createSVG({
                            $el     : self.viewport.$el,
                            title   : self.chart.get( 'title' ),
                            error   : function( err ) {
                                self.message.update( { message: err, status: 'danger' } );
                            }
                        });
                    });
                }
            });
            this.export_button.addMenu({
                key         : 'pdf',
                title       : 'Save as PDF',
                icon        : 'fa-file-o',
                onclick     : function() {
                    self.app.modal.show({
                        title   : 'Send visualization data for PDF creation',
                        body    : 'Galaxy does not provide integrated PDF export scripts. You may click \'Continue\' to create the PDF by using a 3rd party service (https://export.highcharts.com).',
                        buttons : {
                            'Cancel' : function() { self.app.modal.hide() },
                            'Continue' : function() {
                                self.app.modal.hide();
                                self._wait( self.chart, function() {
                                    Screenshot.createPDF({
                                        $el     : self.viewport.$el,
                                        title   : self.chart.get( 'title' ),
                                        error   : function( err ) {
                                            self.message.update( { message: err, status: 'danger' } );
                                        }
                                    });
                                });
                            }
                        }
                    });
                }
            });
            this.portlet = new Portlet.View({
                icon : 'fa-bar-chart-o',
                title: 'Viewport',
                cls  : 'ui-portlet charts-viewer',
                operations: {
                    edit_button: new Ui.ButtonIcon({
                        icon    : 'fa-edit',
                        tooltip : 'Customize this Visualization',
                        title   : 'Editor',
                        onclick : function() {
                            self._wait( self.chart, function() {
                                self.app.go( 'editor' );
                            });
                        }
                    }),
                    export_button: this.export_button,
                    save_button: new Ui.ButtonIcon({
                        icon    : 'fa-save',
                        tooltip : 'Save this Visualization',
                        title   : 'Save',
                        onclick : function() {
                            self.message.update( { message: 'Saving \'' + self.chart.get( 'title' ) + '\'. It will appear in the list of \'Saved Visualizations\'.', status: 'success' } );
                            self.chart.save( { error : function() { self.message.update( { message: 'Could not save visualization.', status: 'danger' } ) } } );
                        }
                    })
                }
            });
            this.portlet.append( this.message.$el );
            this.portlet.append( this.viewport.$el.addClass( 'ui-margin-top' ) );
            this.setElement( this.portlet.$el );
            this.listenTo( this.chart, 'change', function() { self.render() } );
        },

        /** Show and refresh viewer */
        show: function() {
            this.$el.show();
            $( window ).trigger( 'resize' );
        },

        /** Hide viewer */
        hide: function() {
            this.$el.hide();
        },

        /** Change title */
        render: function() {
            var title = this.chart.get( 'title' );
            this.portlet.title( title );
            var exports = this.chart.definition && this.chart.definition.exports || [];
            this.export_button.collection.each( function( model ) {
                model.set( 'visible', exports.indexOf( model.get( 'key' ) ) !== -1 );
            });
        },

        /** Check if chart is ready for export */
        _wait: function( chart, callback ) {
            if ( this.app.deferred.ready() ) {
                callback();
            } else {
                this.message.update( { message: 'Your visualization is currently being processed. Please wait and try again.' } );
            }
        }
    });
});