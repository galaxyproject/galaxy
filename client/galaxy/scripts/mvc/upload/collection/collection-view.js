/** Renders contents of the collection uploader */
define([ 'utils/utils', 'mvc/upload/upload-model', 'mvc/upload/collection/collection-row', 'mvc/upload/upload-ftp', 'mvc/ui/ui-popover', 'mvc/ui/ui-select',  'mvc/ui/ui-misc', 'mvc/collection/list-collection-creator', 'utils/uploadbox' ],
function( Utils, UploadModel, UploadRow, UploadFtp, Popover, Select, Ui, LIST_COLLECTION_CREATOR ) {
    return Backbone.View.extend({
        // current upload size in bytes
        upload_size: 0,

        // contains upload row models
        collection : new UploadModel.Collection(),

        // keeps track of the current uploader state
        counter : {
            announce    : 0,
            success     : 0,
            error       : 0,
            running     : 0,
            reset : function() { this.announce = this.success = this.error = this.running = 0 }
        },

        initialize : function( app ) {
            var self = this;
            this.app                = app;
            this.options            = app.options;
            this.list_extensions    = app.list_extensions;
            this.list_genomes       = app.list_genomes;
            this.ui_button          = app.ui_button;
            this.ftp_upload_site    = app.currentFtp();
            this.setElement( this._template() );

            // append buttons to dom
            this.btnLocal    = new Ui.Button( { id: 'btn-local', title: 'Choose local files',  onclick: function() { self.uploadbox.select() }, icon: 'fa fa-laptop' } );
            this.btnFtp      = new Ui.Button( { id: 'btn-ftp',   title: 'Choose FTP files',    onclick: function() { self._eventFtp() }, icon: 'fa fa-folder-open-o' } );
            this.btnCreate   = new Ui.Button( { id: 'btn-new',   title: 'Paste/Fetch data',    onclick: function() { self._eventCreate() }, icon: 'fa fa-edit' } );
            this.btnStart    = new Ui.Button( { id: 'btn-start', title: 'Start',               onclick: function() { self._eventStart() } } );
            this.btnBuild    = new Ui.Button( { id: 'btn-build', title: 'Build',               onclick: function() { self._eventBuild() } } );
            this.btnStop     = new Ui.Button( { id: 'btn-stop',  title: 'Pause',               onclick: function() { self._eventStop() } } );
            this.btnReset    = new Ui.Button( { id: 'btn-reset', title: 'Reset',               onclick: function() { self._eventReset() } } );
            this.btnClose    = new Ui.Button( { id: 'btn-close', title: 'Close',               onclick: function() { self.app.modal.hide() } } );
            _.each( [ this.btnLocal, this.btnFtp, this.btnCreate, this.btnStop, this.btnReset, this.btnStart, this.btnBuild, this.btnClose ], function( button ) {
                self.$( '.upload-buttons' ).prepend( button.$el );
            });

            // file upload
            this.uploadbox = this.$( '.upload-box' ).uploadbox({
                url             : this.app.options.nginx_upload_path,
                announce        : function( index, file )       { self._eventAnnounce( index, file ) },
                initialize      : function( index )             { return self.app.toData( [ self.collection.get( index ) ], self.history_id ) },
                progress        : function( index, percentage ) { self._eventProgress( index, percentage ) },
                success         : function( index, message )    { self._eventSuccess( index, message ) },
                error           : function( index, message )    { self._eventError( index, message ) },
                complete        : function()                    { self._eventComplete() },
                ondragover      : function()                    { self.$( '.upload-box' ).addClass( 'highlight' ) },
                ondragleave     : function()                    { self.$( '.upload-box' ).removeClass( 'highlight' ) }
            });

            console.log(this.list_extensions);

            // add ftp file viewer
            this.ftp = new Popover.View( { title: 'FTP files', container: this.btnFtp.$el } );

            // select extension
            this.select_extension = new Select.View({
                css         : 'upload-footer-selection-compressed',
                container   : this.$( '.upload-footer-extension' ),
                data        : _.filter( this.list_extensions, function( ext ) { return !ext.composite_files } ),
                value       : this.options.default_extension,
                onchange    : function( extension ) { self.updateExtension( extension ) }
            });

            this.collectionType = "list";
            this.select_collection = new Select.View({
                css         : 'upload-footer-selection-compressed',
                container   : this.$( '.upload-footer-collection-type' ),
                data        : [{"id": "list", "text": "List"}, {"id": "paired", "text": "Paired"}, {"id": "list:paired", "text": "List of Pairs"}],
                value       : "list",
                onchange    : function( collectionType ) { self.updateCollectionType( collectionType ) }
            })

            // handle extension info popover
            this.$( '.upload-footer-extension-info' ).on( 'click', function( e ) {
                self.showExtensionInfo({
                    $el         : $( e.target ),
                    title       : self.select_extension.text(),
                    extension   : self.select_extension.value(),
                    placement   : 'top'
                });
            }).on( 'mousedown', function( e ) { e.preventDefault() } );

            // genome extension
            this.select_genome = new Select.View({
                css         : 'upload-footer-selection',
                container   : this.$( '.upload-footer-genome' ),
                data        : this.list_genomes,
                value       : this.options.default_genome,
                onchange    : function( genome ) { self.updateGenome(genome) }
            });

            // events
            this.collection.on( 'remove', function( model ) { self._eventRemove( model ) } );
            this._updateScreen();
        },

        /** A new file has been dropped/selected through the uploadbox plugin */
        _eventAnnounce: function( index, file ) {
            this.counter.announce++;
            var new_model = new UploadModel.Model({
                id          : index,
                file_name   : file.name,
                file_size   : file.size,
                file_mode   : file.mode || 'local',
                file_path   : file.path,
                file_data   : file,
                extension   : this.select_extension.value(),
                genome      : this.select_genome.value()
            });
            this.collection.add( new_model );
            var upload_row = new UploadRow( this, { model: new_model } );
            this.$( '.upload-table > tbody:first' ).append( upload_row.$el );
            this._updateScreen();
            upload_row.render();
        },

        /** Progress */
        _eventProgress: function( index, percentage ) {
            var it = this.collection.get( index );
            it.set( 'percentage', percentage );
            this.ui_button.model.set( 'percentage', this._uploadPercentage( percentage, it.get( 'file_size' ) ) );
        },

        /** Success */
        _eventSuccess: function( index, message ) {
            // var hdaId = message["outputs"][0]["id"];
            var hid = message["outputs"][0]["hid"];
            console.log(message["outputs"][0]);       
            var it = this.collection.get( index );
            it.set( { 'percentage': 100, 'status': 'success', 'hid': hid } );
            this.ui_button.model.set( 'percentage', this._uploadPercentage( 100, it.get( 'file_size' ) ) );
            this.upload_completed += it.get( 'file_size' ) * 100;
            this.counter.announce--;
            this.counter.success++;
            this._updateScreen();
            Galaxy.currHistoryPanel.refreshContents();
        },

        /** Error */
        _eventError: function( index, message ) {
            var it = this.collection.get( index );
            it.set( { 'percentage': 100, 'status': 'error', 'info': message } );
            this.ui_button.model.set( { 'percentage': this._uploadPercentage( 100, it.get( 'file_size' ) ), 'status': 'danger' } );
            this.upload_completed += it.get( 'file_size' ) * 100;
            this.counter.announce--;
            this.counter.error++;
            this._updateScreen();
        },

        /** Queue is done */
        _eventComplete: function() {
            this.collection.each( function( model ) { model.get( 'status' ) == 'queued' && model.set( 'status', 'init' ) } );
            this.counter.running = 0;
            this._updateScreen();
        },

        _eventBuild: function() {
            var models = this.collection.map( function( upload ) { return Galaxy.currHistoryPanel.collection.getByHid( upload.get( 'hid' ) ) } );
            var selection = new Galaxy.currHistoryPanel.collection.constructor( models );
            // I'm building the selection wrong because I need to set this historyId directly.
            selection.historyId = Galaxy.currHistoryPanel.collection.historyId;
            Galaxy.currHistoryPanel.buildCollection( this.collectionType, selection, true );
            this.counter.running = 0;
            this._updateScreen();
            this._eventReset();
            this.app.modal.hide();
        },

        /** Remove model from upload list */
        _eventRemove: function( model ) {
            var status = model.get( 'status' );
            if ( status == 'success' ) {
                this.counter.success--;
            } else if ( status == 'error' ) {
                this.counter.error--;
            } else {
                this.counter.announce--;
            }
            this.uploadbox.remove( model.id );
            this._updateScreen();
        },

        //
        // events triggered by this view
        //

        /** [public] display extension info popup */
        showExtensionInfo: function( options ) {
            var self = this;
            var $el = options.$el;
            var extension = options.extension;
            var title = options.title;
            var description = _.findWhere( self.list_extensions, { 'id': extension } );
            this.extension_popup && this.extension_popup.remove();
            this.extension_popup = new Popover.View({ placement: options.placement || 'bottom', container: $el } );
            this.extension_popup.title( title );
            this.extension_popup.empty();
            this.extension_popup.append( this._templateDescription( description ) );
            this.extension_popup.show();
        },

        /** Show/hide ftp popup */
        _eventFtp: function() {
            if ( !this.ftp.visible ) {
                this.ftp.empty();
                var self = this;
                this.ftp.append( ( new UploadFtp({
                    collection      : this.collection,
                    ftp_upload_site : this.ftp_upload_site,
                    onadd           : function( ftp_file ) {
                        self.uploadbox.add([{
                            mode: 'ftp',
                            name: ftp_file.path,
                            size: ftp_file.size,
                            path: ftp_file.path
                        }]);
                    },
                    onremove: function( model_index ) {
                        self.collection.remove( model_index );
                    }
                } ) ).$el );
                this.ftp.show();
            } else {
                this.ftp.hide();
            }
        },

        /** Create a new file */
        _eventCreate: function (){
            this.uploadbox.add( [ { name: 'New File', size: 0, mode: 'new' } ] );
        },

        /** Start upload process */
        _eventStart: function() {
            if ( this.counter.announce == 0 || this.counter.running > 0 ) {
                return;
            }
            var self = this;
            this.upload_size = 0;
            this.upload_completed = 0;
            this.collection.each( function( model ) {
                if( model.get( 'status' ) == 'init' ) {
                    model.set( 'status', 'queued' );
                    self.upload_size += model.get( 'file_size' );
                }
            });
            this.ui_button.model.set( { 'percentage': 0, 'status': 'success' } );
            this.counter.running = this.counter.announce;
            this.history_id = this.app.currentHistory();
            this.uploadbox.start();
            this._updateScreen();
        },

        /** Pause upload process */
        _eventStop: function() {
            if ( this.counter.running > 0 ) {
                this.ui_button.model.set( 'status', 'info' );
                $( '.upload-top-info' ).html( 'Queue will pause after completing the current file...' );
                this.uploadbox.stop();
            }
        },

        /** Remove all */
        _eventReset: function() {
            if ( this.counter.running == 0 ){
                this.collection.reset();
                this.counter.reset();
                this.uploadbox.reset();
                this.select_extension.value( this.options.default_extension );
                this.select_genome.value( this.options.default_genome );
                this.ui_button.model.set( 'percentage', 0 );
                this._updateScreen();
            }
        },

        /** Update extension for all models */
        updateExtension: function( extension, defaults_only ) {
            var self = this;
            this.collection.each( function( model ) {
                if ( model.get( 'status' ) == 'init' && ( model.get( 'extension' ) == self.options.default_extension || !defaults_only ) ) {
                    model.set( 'extension', extension );
                }
            });
        },

        /** Update collection type */
        updateCollectionType: function( collectionType ) {
            var self = this;
            this.collectionType = collectionType;
        },

        /** Update genome for all models */
        updateGenome: function( genome, defaults_only ) {
            var self = this;
            this.collection.each( function( model ) {
                if ( model.get( 'status' ) == 'init' && ( model.get( 'genome' ) == self.options.default_genome || !defaults_only ) ) {
                    model.set( 'genome', genome );
                }
            });
        },

        /** Set screen */
        _updateScreen: function () {
            var message = '';
            if( this.counter.announce == 0 ) {
                if (this.uploadbox.compatible()) {
                    message = '&nbsp;';
                } else {
                    message = 'Browser does not support Drag & Drop. Try Firefox 4+, Chrome 7+, IE 10+, Opera 12+ or Safari 6+.';
                }
            } else {
                if ( this.counter.running == 0 ) {
                    message = 'You added ' + this.counter.announce + ' file(s) to the queue. Add more files or click \'Start\' to proceed.';
                } else {
                    message = 'Please wait...' + this.counter.announce + ' out of ' + this.counter.running + ' remaining.';
                }
            }
            this.$( '.upload-top-info' ).html( message );
            var enable_reset = this.counter.running == 0 && this.counter.announce + this.counter.success + this.counter.error > 0;
            var enable_start = this.counter.running == 0 && this.counter.announce > 0;
            var enable_build = this.counter.running == 0 && this.counter.announce == 0 && this.counter.success > 0 && this.counter.error == 0
            var enable_sources = this.counter.running == 0;
            var show_table = this.counter.announce + this.counter.success + this.counter.error > 0;
            this.btnReset[ enable_reset ? 'enable' : 'disable' ]();
            this.btnStart[ enable_start ? 'enable' : 'disable' ]();
            this.btnStart.$el[ enable_start ? 'addClass' : 'removeClass' ]( 'btn-primary' );
            this.btnBuild[ enable_build ? 'enable' : 'disable' ]();
            this.btnBuild.$el[ enable_build ? 'addClass' : 'removeClass' ]( 'btn-primary' );
            this.btnStop[ this.counter.running > 0 ? 'enable' : 'disable' ]();
            this.btnLocal[ enable_sources ? 'enable' : 'disable' ]();
            this.btnFtp[ enable_sources ? 'enable' : 'disable' ]();
            this.btnCreate[ enable_sources ? 'enable' : 'disable' ]();
            this.btnFtp.$el[ this.ftp_upload_site ? 'show' : 'hide' ]();
            this.$( '.upload-table' )[ show_table ? 'show' : 'hide' ]();
            this.$( '.upload-helper' )[ show_table ? 'hide' : 'show' ]();
        },

        /** Calculate percentage of all queued uploads */
        _uploadPercentage: function( percentage, size ) {
            return ( this.upload_completed + ( percentage * size ) ) / this.upload_size;
        },

        /** Template for extensions description */
        _templateDescription: function( options ) {
            if ( options.description ) {
                var tmpl = options.description;
                if ( options.description_url ) {
                    tmpl += '&nbsp;(<a href="' + options.description_url + '" target="_blank">read more</a>)';
                }
                return tmpl;
            } else {
                return 'There is no description available for this file extension.';
            }
        },

        /** Template */
        _template: function() {
            return  '<div class="upload-view-default">' +
                        '<div class="upload-top">' +
                            '<h6 class="upload-top-info"/>' +
                        '</div>' +
                        '<div class="upload-box">' +
                            '<div class="upload-helper"><i class="fa fa-files-o"/>Drop files here</div>' +
                            '<table class="upload-table ui-table-striped" style="display: none;">' +
                                '<thead>' +
                                    '<tr>' +
                                        '<th>Name</th>' +
                                        '<th>Size</th>' +
                                        '<th>Status</th>' +
                                        '<th/>' +
                                    '</tr>' +
                                '</thead>' +
                                '<tbody/>' +
                            '</table>' +
                        '</div>' +
                        '<div class="upload-footer">' +
                            '<span class="upload-footer-title-compressed">Collection Type:</span>' +
                            '<span class="upload-footer-collection-type"/>' +
                            '<span class="upload-footer-title-compressed">File Type:</span>' +
                            '<span class="upload-footer-extension"/>' +
                            '<span class="upload-footer-extension-info upload-icon-button fa fa-search"/> ' +
                            '<span class="upload-footer-title-compressed">Genome (set all):</span>' +
                            '<span class="upload-footer-genome"/>' +
                        '</div>' +
                        '<div class="upload-buttons"/>' +
                    '</div>';
        }
    });
});
