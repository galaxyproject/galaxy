/** Frame manager uses the ui-frames to create the scratch book masthead icon and functionality **/
define([ 'mvc/ui/ui-frames' ], function( Frames ) {
return Backbone.View.extend({
    initialize : function( options ) {
        var self = this;
        options = options || {};
        this.frames = new Frames.View({ visible : false });
        this.setElement( this.frames.$el );
        this.buttonActive = options.collection.add({
            id              : 'enable-scratchbook',
            icon            : 'fa-th',
            tooltip         : 'Enable/Disable Scratchbook',
            onclick         : function() {
                self.active = !self.active;
                self.buttonActive.set({
                    toggle    : self.active,
                    show_note : self.active,
                    note_cls  : self.active && 'fa fa-check'
                });
                !self.active && self.frames.hide();
            },
            onbeforeunload  : function() {
                if ( self.frames.length() > 0 ) {
                    return 'You opened ' + self.frames.length() + ' frame(s) which will be lost.';
                }
            }
        });
        this.buttonLoad = options.collection.add({
            id              : 'show-scratchbook',
            icon            : 'fa-eye',
            tooltip         : 'Show/Hide Scratchbook',
            show_note       : true,
            visible         : false,
            onclick         : function( e ) {
                self.frames.visible ? self.frames.hide() : self.frames.show();
            }
        });
        this.frames.on( 'add remove', function() {
            this.visible && this.length() == 0 && this.hide();
            self.buttonLoad.set( { 'note': this.length(), 'visible': this.length() > 0 } );
        }).on( 'show hide ', function() {
            self.buttonLoad.set( { 'toggle': this.visible, 'icon': this.visible && 'fa-eye' || 'fa-eye-slash' } );
        });
    },

    /** Add a dataset to the frames */
    addDataset: function( dataset_id ) {
        var self = this;
        require([ 'mvc/dataset/data' ], function( DATA ) {
            var dataset = new DATA.Dataset( { id : dataset_id } );
            $.when( dataset.fetch() ).then( function() {
                // Construct frame config based on dataset's type.
                var frame_config = {
                        title: dataset.get('name')
                    },
                    // HACK: For now, assume 'tabular' and 'interval' are the only
                    // modules that contain tabular files. This needs to be replaced
                    // will a is_datatype() function.
                    is_tabular = _.find( [ 'tabular', 'interval' ] , function( data_type ) {
                        return dataset.get( 'data_type' ).indexOf( data_type ) !== -1;
                    });

                // Use tabular chunked display if dataset is tabular; otherwise load via URL.
                if ( is_tabular ) {
                    var tabular_dataset = new DATA.TabularDataset( dataset.toJSON() );
                    _.extend( frame_config, {
                        content: function( parent_elt ) {
                            DATA.createTabularDatasetChunkedView({
                                model       : tabular_dataset,
                                parent_elt  : parent_elt,
                                embedded    : true,
                                height      : '100%'
                            });
                        }
                    });
                }
                else {
                    _.extend( frame_config, {
                        url: Galaxy.root + 'datasets/' + dataset.id + '/display/?preview=True'
                    });
                }
                self.add( frame_config );
            });
        });
    },

    /** Add a trackster visualization to the frames. */
    addTrackster: function(viz_id) {
        var self = this;
        require(['viz/visualization', 'viz/trackster'], function(visualization, trackster) {
            var viz = new visualization.Visualization({id: viz_id});
            $.when( viz.fetch() ).then( function() {
                var ui = new trackster.TracksterUI(Galaxy.root);

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

    /** Add and display a new frame/window based on options. */
    add: function( options ) {
        if ( options.target == '_blank' ) {
            window.open( options.url );
        } else if ( options.target == '_top' || options.target == '_parent' || options.target == '_self' ) {
            window.location = options.url;
        } else if ( !this.active ) {
            var $galaxy_main = $( window.parent.document ).find( '#galaxy_main' );
            if ( options.target == 'galaxy_main' || options.target == 'center' ){
                if ( $galaxy_main.length === 0 ){
                    var href = options.url;
                    if ( href.indexOf( '?' ) == -1 )
                        href += '?';
                    else
                        href += '&';
                    href += 'use_panels=True';
                    window.location = href;
                } else {
                    $galaxy_main.attr( 'src', options.url );
                }
            } else
                window.location = options.url;
        } else {
            this.frames.add( options );
        }
    }
});

});