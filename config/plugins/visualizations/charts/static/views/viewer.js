// dependencies
define(['utils/utils', 'mvc/ui/ui-misc', 'mvc/ui/ui-portlet',
        'plugin/views/viewport', 'plugin/library/screenshot'],
        function(Utils, Ui, Portlet, ViewportView, Screenshot) {

/**
 *  This class renders the chart viewer which encapsulates the chart viewport.
 */
return Backbone.View.extend({
    // initialize
    initialize: function(app, options){
        // link app
        this.app = app;
        
        // link chart
        this.chart = this.app.chart;
        
        // create viewport
        this.viewport_view = new ViewportView(app);
        
        // link this
        var self = this;
        
        // message element
        this.message = new Ui.Message();
        
        // button menu
        var picture_button_menu = new Ui.ButtonMenu({
            icon    : 'fa-camera',
            title   : 'Screenshot',
            tooltip : 'Download as PNG, SVG or PDF file'
        });
        
        // add png option
        picture_button_menu.addMenu({
            id          : 'button-png',
            title       : 'Save as PNG',
            icon        : 'fa-file',
            onclick     : function() {
                self._wait (self.chart, function() {
                    Screenshot.createPNG({
                        $el     : self.viewport_view.$el,
                        title   : self.chart.get('title'),
                        error   : function(err) {
                            self.message.update({ message: err, status: 'danger' });
                        }
                    });
                });
            }
        });
        
        // add png option
        picture_button_menu.addMenu({
            id          : 'button-svg',
            title       : 'Save as SVG',
            icon        : 'fa-file-text-o',
            onclick     : function() {
                self._wait (self.chart, function() {
                    Screenshot.createSVG({
                        $el     : self.viewport_view.$el,
                        title   : self.chart.get('title'),
                        error   : function(err) {
                            self.message.update({ message: err, status: 'danger' });
                        }
                    });
                });
            }
        });
        
        // add png option
        picture_button_menu.addMenu({
            id          : 'button-png',
            title       : 'Save as PDF',
            icon        : 'fa-file-o',
            onclick     : function() {
                self.app.modal.show({
                    title   : 'Send chart data for PDF creation',
                    body    : 'Galaxy does not provide integrated PDF export scripts. You may click \'Continue\' to create the PDF by using a 3rd party service (https://export.highcharts.com).',
                    buttons : {
                        'Cancel' : function() {self.app.modal.hide()},
                        'Continue' : function() {
                            self.app.modal.hide();
                            self._wait (self.chart, function() {
                                Screenshot.createPDF({
                                    $el     : self.viewport_view.$el,
                                    title   : self.chart.get('title'),
                                    error   : function(err) {
                                        self.message.update({ message: err, status: 'danger' });
                                    }
                                });
                            });
                        }
                    }
                });
            }
        });

        // create portlet
        this.portlet = new Portlet.View({
            icon : 'fa-bar-chart-o',
            title: 'Viewport',
            scrollable: false,
            operations: {
                edit_button: new Ui.ButtonIcon({
                    icon    : 'fa-edit',
                    tooltip : 'Customize this chart',
                    title   : 'Editor',
                    onclick : function() {
                        self._wait (self.chart, function() {
                            self.app.go('editor');
                        });
                    }
                }),
                picture_button_menu: picture_button_menu
            }
        });
        
        // append portlet
        this.portlet.append(this.message.$el);
        this.portlet.append(this.viewport_view.$el);
        
        // set element
        this.setElement(this.portlet.$el);
        
        // events
        var self = this;
        this.chart.on('change:title', function() {
            self._refreshTitle();
        });
    },

    // show
    show: function() {
        // show element
        this.$el.show();
        
        // trigger resize to refresh d3 element
        $(window).trigger('resize');
    },
        
    // hide
    hide: function() {
        this.$el.hide();
    },
    
    // refresh title
    _refreshTitle: function() {
        var title = this.chart.get('title');
        this.portlet.title(title);
    },
    
    // wait for chart to be ready
    _wait: function(chart, callback) {
        // get chart
        if (this.app.deferred.ready()) {
            callback();
        } else {
            this.message.update({message: 'Your chart is currently being processed. Please wait and try again.'});
        }
    }
});

});