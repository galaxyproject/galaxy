// dependencies
define(['utils/utils', 'plugin/library/ui', 'mvc/ui/ui-portlet',
        'plugin/models/group', 'plugin/views/viewport',],
        function(Utils, Ui, Portlet, Group, ViewportView) {

// widget
return Backbone.View.extend(
{
    // initialize
    initialize: function(app, options)
    {
        // link app
        this.app = app;
        
        // link chart
        this.chart = this.app.chart;
        
        // create viewport
        this.viewport_view = new ViewportView(app);
        
        // link this
        var self = this;
        
        // create portlet
        this.portlet = new Portlet.View({
            icon : 'fa-bar-chart-o',
            title: 'Viewport',
            operations: {
                edit_button: new Ui.ButtonIcon({
                    icon    : 'fa-edit',
                    tooltip : 'Customize this chart',
                    title   : 'Customize',
                    onclick : function() {
                        // attempt to load chart editor
                        self._wait (self.chart, function() {
                            self.app.go('editor');
                        });
                    }
                }),
                /*picture_button: new Ui.ButtonIcon({
                    icon    : 'fa-camera',
                    tooltip : 'Download SVG-file',
                    title   : 'Screenshot',
                    onclick : function() {
                        // attempt to load chart editor
                        self._wait (self.chart, function() {
                            self._screenshot();
                        });
                    }
                }),
                settings_button: new Ui.ButtonIcon({
                    icon    : 'fa-gear',
                    tooltip : 'Configure this application',
                    title   : 'Application',
                    onclick : function() {
                        // attempt to load chart editor
                        self._wait (self.chart, function() {
                            self.app.go('editor');
                        });
                    }
                })*/
            }
        });
        
        // append portlet
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
    
    // download svg file
    _screenshot: function() {
        // Encode the SVG
        var serializer = new XMLSerializer();
        var xmlString = serializer.serializeToString(this.viewport_view.svg.node());
        var imgData = 'data:image/svg+xml;base64,' + btoa(xmlString);
        //Use the download attribute (or a shim) to provide a link
        //this.portlet.append('<a href="' + imgData + '" download>Download</a>');
        window.location.href = 'data:application/x-download/;charset=utf-8,' + encodeURIComponent(xmlString);
    },
    
    // wait for chart to be ready
    _wait: function(chart, callback) {
        // get chart
        if (chart.deferred.ready()) {
            callback();
        } else {
            // show modal
            var self = this;
            this.app.modal.show({
                title   : 'Please wait!',
                body    : 'Your chart is currently being processed. Please wait and try again.',
                buttons : {
                    'Close'     : function() {self.app.modal.hide();},
                    'Retry'     : function() {
                        // hide modal
                        self.app.modal.hide();
                        
                        // retry
                        setTimeout(function() { self._wait(chart, callback); }, self.app.config.get('query_timeout'));
                    }
                }
            });
        }
    }
});

});