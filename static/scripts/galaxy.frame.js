// dependencies
define(["galaxy.masthead", "mvc/ui/ui-frames"], function(mod_masthead, Frames) {

/** Frame manager uses the ui-frames to create the scratch book masthead icon and functionality **/
var GalaxyFrame = Backbone.View.extend({
    // base element
    el_main: 'body',
        
    // frame active/disabled
    active: false,
    
    // button active
    button_active: null,
    
    // button load
    button_load  : null,
    
    // initialize
    initialize : function(options) {
        // add to masthead menu
        var self = this;
        
        // create frames
        this.frames = new Frames.View({
            visible: false,
        });

        // add activate icon
        this.button_active = new mod_masthead.GalaxyMastheadIcon({
            icon        : 'fa-th',
            tooltip     : 'Enable/Disable Scratchbook',
            onclick     : function() { self._activate(); },
            onunload    : function() {
                if (self.frames.length() > 0) {
                    return "You opened " + self.frames.length() + " frame(s) which will be lost.";
                }
            }
        });
        
        // add to masthead
        Galaxy.masthead.append(this.button_active);

        // add load icon
        this.button_load = new mod_masthead.GalaxyMastheadIcon({
            icon        : 'fa-eye',
            tooltip     : 'Show/Hide Scratchbook',
            onclick     : function(e) {
                if (self.frames.visible) {
                    self.frames.hide();
                } else {
                    self.frames.show();
                }
            },
            with_number : true
        });

        // add to masthead
        Galaxy.masthead.append(this.button_load);
        
        // create
        this.setElement(this.frames.$el);
        
        // append to main
        $(this.el_main).append(this.$el);
        
        // refresh menu
        this.frames.setOnChange(function() {
            self._refresh();
        });
        this._refresh();
    },

    /**
     * Add a dataset to the frames.
     */
    add_dataset: function(dataset_id) {
        var self = this;
        require(['mvc/data'], function(DATA) {
            var dataset = new DATA.Dataset({ id: dataset_id });
            $.when( dataset.fetch() ).then( function() {
                // Construct frame config based on dataset's type.
                var frame_config = {
                        title: dataset.get('name')
                    },
                    // HACK: For now, assume 'tabular' and 'interval' are the only 
                    // modules that contain tabular files. This needs to be replaced
                    // will a is_datatype() function.
                    is_tabular = _.find(['tabular', 'interval'], function(data_type) { 
                        return dataset.get('data_type').indexOf(data_type) !== -1;
                    });

                // Use tabular chunked display if dataset is tabular; otherwise load via URL.
                if (is_tabular) {
                    var tabular_dataset = new DATA.TabularDataset(dataset.toJSON());
                    _.extend(frame_config, {
                        type: 'other',
                        content: function( parent_elt ) {
                            DATA.createTabularDatasetChunkedView({
                                model: tabular_dataset,
                                parent_elt: parent_elt,
                                embedded: true,
                                height: '100%'
                            });
                        }
                    });
                }
                else {
                    _.extend(frame_config, {
                        type: 'url',
                        content: galaxy_config.root + 'datasets/' + 
                                 dataset.id + '/display/?preview=True'
                    });
                }

                self.add(frame_config);

            });
        });

    },

    /**
     * Add a trackster visualization to the frames.
     */
    add_trackster_viz: function(viz_id) {
        var self = this;
        require(['viz/visualization', 'viz/trackster'], function(visualization, trackster) {
            var viz = new visualization.Visualization({id: viz_id});
            $.when( viz.fetch() ).then( function() {
                var ui = new trackster.TracksterUI(galaxy_config.root);

                // Construct frame config based on dataset's type.
                var frame_config = {
                        title: viz.get('name'),
                        type: 'other',
                        content: function(parent_elt) {
                            // Create view config.
                            var view_config = {
                                container: parent_elt,
                                name: viz.get('title'),
                                id: viz.id,
                                // FIXME: this will not work with custom builds b/c the dbkey needed to be encoded.
                                dbkey: viz.get('dbkey'),
                                stand_alone: false
                            },
                            latest_revision = viz.get('latest_revision'),
                            drawables = latest_revision.config.view.drawables;

                            // Set up datasets in drawables.
                            _.each(drawables, function(d) {
                                d.dataset = {
                                    hda_ldda: d.hda_ldda,
                                    id: d.dataset_id
                                };
                            });

                            view = ui.create_visualization(view_config,
                                                           latest_revision.config.viewport,
                                                           latest_revision.config.view.drawables,
                                                           latest_revision.config.bookmarks,
                                                           false);
                        }
                    };

                self.add(frame_config);
            });
        });
    },
    
    /**
     * Add and display a new frame/window based on options.
     */
    add: function(options){
        // open new tab
        if (options.target == '_blank'){
            window.open(options.content);
            return;
        }
        
        // reload entire window
        if (options.target == '_top' || options.target == '_parent' || options.target == '_self'){
            window.location = options.content;
            return;
        }
        
        // validate
        if (!this.active){
            // fix url if main frame is unavailable
            var $galaxy_main = $(window.parent.document).find('#galaxy_main');
            if (options.target == 'galaxy_main' || options.target == 'center'){
                if ($galaxy_main.length === 0){
                    var href = options.content;
                    if (href.indexOf('?') == -1)
                        href += '?';
                    else
                        href += '&';
                    href += 'use_panels=True';
                    window.location = href;
                } else {
                    $galaxy_main.attr('src', options.content);
                }
            } else
                window.location = options.content;
                
            // stop
            return;
        }

        // add to frames view
        this.frames.add(options);
    },
    
    // activate/disable panel
    _activate: function (){
        // check
        if (this.active){
            // disable
            this.active = false;

            // toggle
            this.button_active.untoggle();
    
            // hide panel
            this.frames.hide();
        } else {
            // activate
            this.active = true;
        
            // untoggle
            this.button_active.toggle();
        }
    },
    
    // update frame counter
    _refresh: function(){
        // update on screen counter
        this.button_load.number(this.frames.length());
        
        // check
        if(this.frames.length() === 0)
            this.button_load.hide();
        else
            this.button_load.show();
            
        // check
        if (this.frames.visible) {
            this.button_load.toggle();
        } else {
            this.button_load.untoggle();
        }
    }
});

// return
return {
    GalaxyFrame: GalaxyFrame
};

});
