/** Upload app contains the upload progress button and upload modal, compiles model data for API request **/
define([ 'utils/utils', 'mvc/ui/ui-modal', 'mvc/ui/ui-tabs', 'mvc/upload/upload-button', 'mvc/upload/default/default-view', 'mvc/upload/composite/composite-view'],
function( Utils, Modal, Tabs, UploadButton, UploadViewDefault, UploadViewComposite ) {
    return Backbone.View.extend({
        options : {
            nginx_upload_path   : '',
            ftp_upload_site     : 'n/a',
            default_genome      : '?',
            default_extension   : 'auto',
            height              : 500,
            width               : 900,
            auto                : {
                id          : 'auto',
                text        : 'Auto-detect',
                description : 'This system will try to detect the file type automatically. If your file is not detected properly as one of the known formats, it most likely means that it has some format problems (e.g., different number of columns on different rows). You can still coerce the system to set your data to the format you think it should be.  You can also upload compressed files, which will automatically be decompressed.'
            }
        },

        // contains all available dataset extensions/types
        list_extensions: [],

        // contains all available genomes
        list_genomes: [],

        initialize: function( options ) {
            var self = this;
            this.options = Utils.merge( options, this.options );

            // create view for upload/progress button
            this.ui_button = new UploadButton.View({
                onclick     : function(e) {
                    e.preventDefault();
                    self.show()
                },
                onunload    : function() {
                    var percentage = self.ui_button.model.get('percentage', 0);
                    if (percentage > 0 && percentage < 100) {
                        return 'Several uploads are queued.';
                    }
                }
            });

            // set element to button view
            this.setElement( this.ui_button.$el );

            // load extensions
            var self = this;
            Utils.get({
                url     : Galaxy.root + 'api/datatypes?extension_only=False',
                success : function( datatypes ) {
                    for ( key in datatypes ) {
                        self.list_extensions.push({
                            id              : datatypes[ key ].extension,
                            text            : datatypes[ key ].extension,
                            description     : datatypes[ key ].description,
                            description_url : datatypes[ key ].description_url,
                            composite_files : datatypes[ key ].composite_files
                        });
                    }
                    self.list_extensions.sort( function( a, b ) {
                        var a_text = a.text && a.text.toLowerCase();
                        var b_text = b.text && b.text.toLowerCase();
                        return a_text > b_text ? 1 : a_text < b_text ? -1 : 0;
                    });
                    if ( !self.options.datatypes_disable_auto ) {
                        self.list_extensions.unshift( self.options.auto );
                    }
                }
            });

            // load genomes
            Utils.get({
                url     : Galaxy.root + 'api/genomes',
                success : function( genomes ) {
                    for ( key in genomes ) {
                        self.list_genomes.push({
                            id      : genomes[ key ][ 1 ],
                            text    : genomes[ key ][ 0 ]
                        });
                    }
                    self.list_genomes.sort( function( a, b ) {
                        if ( a.id == self.options.default_genome ) { return -1; }
                        if ( b.id == self.options.default_genome ) { return 1; }
                        return a.text > b.text ? 1 : a.text < b.text ? -1 : 0;
                    });
                }
            });
        },

        /** Show/hide upload dialog */
        show: function () {
            var self = this;
            if ( !Galaxy.currHistoryPanel || !Galaxy.currHistoryPanel.model ) {
                window.setTimeout(function() { self.show() }, 500)
                return;
            }
            this.current_user = Galaxy.user.id;
            if ( !this.modal ) {
                this.tabs = new Tabs.View();
                this.default_view = new UploadViewDefault( this );
                this.tabs.add({
                    id      : 'regular',
                    title   : 'Regular',
                    $el     : this.default_view.$el
                });
                this.composite_view = new UploadViewComposite( this );
                this.tabs.add({
                    id      : 'composite',
                    title   : 'Composite',
                    $el     : this.composite_view.$el
                });
                this.modal = new Modal.View({
                    title           : 'Download from web or upload from disk',
                    body            : this.tabs.$el,
                    height          : this.options.height,
                    width           : this.options.width,
                    closing_events  : true,
                    title_separator : false
                });
            }
            this.modal.show();
        },

        /** Refresh user and current history */
        currentHistory: function() {
            return this.current_user && Galaxy.currHistoryPanel.model.get( 'id' );
        },

        /** Get ftp configuration */
        currentFtp: function() {
            return this.current_user && this.options.ftp_upload_site;
        },

        /**
          * Package API data from array of models
          * @param{Array} items - Upload items/rows filtered from a collection
        */
        toData: function( items, history_id ) {
            // create dictionary for data submission
            var data = {
                payload: {
                    'tool_id'       : 'upload1',
                    'history_id'    : history_id || this.currentHistory(),
                    'inputs'        : {}
                },
                files: [],
                error_message: null
            }
            // add upload tools input data
            if ( items && items.length > 0 ) {
                var inputs = {};
                inputs[ 'dbkey' ] = items[0].get( 'genome', null );
                inputs[ 'file_type' ] = items[0].get( 'extension', null );
                for ( var index in items ) {
                    var it = items[ index ];
                    it.set( 'status', 'running' );
                    if ( it.get( 'file_size' ) > 0 ) {
                        var prefix = 'files_' + index + '|';
                        inputs[ prefix + 'type' ] = 'upload_dataset';
                        inputs[ prefix + 'space_to_tab' ] = it.get( 'space_to_tab' ) && 'Yes' || null;
                        inputs[ prefix + 'to_posix_lines' ] = it.get( 'to_posix_lines' ) && 'Yes' || null;
                        switch ( it.get( 'file_mode' ) ) {
                            case 'new':
                                inputs[ prefix + 'url_paste' ] = it.get( 'url_paste' );
                                break;
                            case 'ftp':
                                inputs[ prefix + 'ftp_files' ] = it.get( 'file_path' );
                                break;
                            case 'local':
                                data.files.push( { name: prefix + 'file_data', file: it.get( 'file_data' ) } );
                        }
                    } else {
                        data.error_message = 'Upload content incomplete.';
                        it.set( 'status', 'error' );
                        it.set( 'info', data.error_message );
                        break;
                    }
                }
                data.payload.inputs = JSON.stringify( inputs );
            }
            return data;
        }
    });
});
