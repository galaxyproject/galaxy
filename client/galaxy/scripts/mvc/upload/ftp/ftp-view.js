/** Renders contents of the collection uploader */
define([ 'utils/utils', 'mvc/ui/ui-select',  'mvc/ui/ui-misc', 'mvc/upload/upload-model', 'mvc/upload/upload-ftp', 'mvc/upload/upload-extension', 'utils/uploadbox' ],
function( Utils, Select, Ui, UploadModel, UploadFtp, UploadExtension ) {
    return Backbone.View.extend({

        // contains upload row models
        collection : new UploadModel.Collection(),

        initialize : function( app ) {
            var self = this;
            this.app                = app;
            this.options            = app.options;
            this.list_extensions    = app.list_extensions;
            this.list_genomes       = app.list_genomes;
            this.ftp_upload_site    = app.currentFtp();
            this.setElement( this._template() );

            // build ftp list view
            this.ftp_list = new UploadFtp({
                css             : 'upload-ftp-full',
                collection      : this.collection,
                ftp_upload_site : this.ftp_upload_site,
                onadd           : function( ftp_file ) {
                    self.collection.add({
                        id        : Utils.uid(),
                        file_mode : 'ftp',
                        file_name : ftp_file.path,
                        file_size : ftp_file.size,
                        file_path : ftp_file.path,
                        enabled   : true
                    });
                },
                onremove: function( model_index ) {
                    self.collection.remove( model_index );
                }
            });
            this.$( '.upload-box' ).append( this.ftp_list.$el );

            // append buttons to dom
            this.btnStart = new Ui.Button( { id: 'btn-start', title: 'Start', onclick: function() { self._eventStart() } } );
            this.btnClose = new Ui.Button( { id: 'btn-close', title: 'Close',               onclick: function() { self.app.modal.hide() } } );
            _.each( [ this.btnStart, this.btnClose ], function( button ) {
                self.$( '.upload-buttons' ).prepend( button.$el );
            });

            // select extension
            this.select_extension = new Select.View({
                css         : 'upload-footer-selection',
                container   : this.$( '.upload-footer-extension' ),
                data        : _.filter( this.list_extensions, function( ext ) { return !ext.composite_files } ),
                value       : this.options.default_extension,
                onchange    : function( extension ) { self.model.set( 'extension', extension ) }
            });

            // genome extension
            this.select_genome = new Select.View({
                css         : 'upload-footer-selection',
                container   : this.$( '.upload-footer-genome' ),
                data        : this.list_genomes,
                value       : this.options.default_genome,
                onchange    : function( genome ) { self.model.set( 'genome', genome ) }
            });

            // handle extension info popover
            this.$( '.upload-footer-extension-info' ).on( 'click', function( e ) {
                new UploadExtension({
                    $el         : $( e.target ),
                    title       : self.select_extension.text(),
                    extension   : self.select_extension.value(),
                    list        : self.list_extensions,
                    placement   : 'top'
                });
            }).on( 'mousedown', function( e ) { e.preventDefault() } );
        },

        /** Start upload process */
        _eventStart: function() {
            alert( 'Submit all ftp files' );
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

        /** Template */
        _template: function() {
            return  '<div class="upload-view-default">' +
                        '<div class="upload-top">' +
                            '<h6 class="upload-top-info"/>' +
                        '</div>' +
                        '<div class="upload-box upload-box-solid"/>' +
                        '<div class="upload-footer">' +
                            '<span class="upload-footer-title">Type (for all):</span>' +
                            '<span class="upload-footer-extension"/>' +
                            '<span class="upload-footer-extension-info upload-icon-button fa fa-search"/> ' +
                            '<span class="upload-footer-title">Genome (for all):</span>' +
                            '<span class="upload-footer-genome"/>' +
                        '</div>' +
                        '<div class="upload-buttons"/>' +
                    '</div>';
        }
    });
});
