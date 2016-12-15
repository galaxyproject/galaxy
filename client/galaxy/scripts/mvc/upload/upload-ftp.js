/** This renders the content of the ftp popup **/
define( [ 'utils/utils' ], function( Utils ) {
    return Backbone.View.extend({
        initialize: function( options ) {
            var self = this;
            this.options = Utils.merge( options, {
                class_add       : 'upload-icon-button fa fa-square-o',
                class_remove    : 'upload-icon-button fa fa-check-square-o',
                class_partial   : 'upload-icon-button fa fa-minus-square-o',
                collection      : null,
                onchange        : function() {},
                onadd           : function() {},
                onremove        : function() {}
            } );
            this.collection = this.options.collection;
            this.setElement( this._template() );
            this.rows = [];
            Utils.get({
                url     : Galaxy.root + 'api/remote_files',
                success : function( ftp_files ) { self._fill( ftp_files ) },
                error   : function() { self._fill(); }
            });
        },

        /** Fill table with ftp entries */
        _fill: function( ftp_files ) {
            if ( ftp_files && ftp_files.length > 0 ) {
                this.$( '.upload-ftp-content' ).html( $( this._templateTable() ) );
                var size = 0;
                for ( index in ftp_files ) {
                    this.rows.push( this._add( ftp_files[ index ] ) );
                    size += ftp_files[ index ].size;
                }
                this.$( '.upload-ftp-number' ).html( ftp_files.length + ' files' );
                this.$( '.upload-ftp-disk' ).html( Utils.bytesToString ( size, true ) );
                if ( this.collection ) {
                    var self = this;
                    this.$( '._has_collection' ).show();
                    this.$select_all = this.$( '.upload-selectall' ).addClass( this.options.class_add );
                    this.$select_all.on( 'click', function() {
                        var add = self.$select_all.hasClass( self.options.class_add );
                        for ( index in ftp_files ) {
                            var ftp_file = ftp_files[ index ];
                            var model_index = self._find( ftp_file );
                            if( !model_index && add || model_index && !add ) {
                                self.rows[ index ].trigger( 'click' );
                            }
                        }
                    });
                    this._refresh();
                }
            } else {
                this.$( '.upload-ftp-content' ).html( $( this._templateInfo() ) );
            }
            this.$( '.upload-ftp-wait' ).hide();
        },

        /** Add file to table */
        _add: function( ftp_file ) {
            var self = this;
            var $it = $( this._templateRow( ftp_file ) );
            var $icon = $it.find( '.icon' );
            this.$( 'tbody' ).append( $it );
            if ( this.collection ) {
                $icon.addClass( this._find( ftp_file ) ? this.options.class_remove : this.options.class_add );
                $it.on('click', function() {
                    var model_index = self._find( ftp_file );
                    $icon.removeClass();
                    if ( !model_index ) {
                        self.options.onadd( ftp_file );
                        $icon.addClass( self.options.class_remove );
                    } else {
                        self.options.onremove( model_index );
                        $icon.addClass( self.options.class_add );
                    }
                    self._refresh();
                });
            } else {
                $it.on('click', function() { self.options.onchange( ftp_file ) } );
            }
            return $it;
        },

        /** Refresh select all button state */
        _refresh: function() {
            var filtered = this.collection.where( { file_mode: 'ftp', enabled: true } );
            this.$select_all.removeClass();
            if ( filtered.length == 0 ) {
                this.$select_all.addClass( this.options.class_add );
            } else {
                this.$select_all.addClass( filtered.length == this.rows.length ? this.options.class_remove : this.options.class_partial );
            }
        },

        /** Get model index */
        _find: function( ftp_file ) {
            var item = this.collection.findWhere({
                file_path   : ftp_file.path,
                file_mode   : 'ftp',
                enabled     : true
            });
            return item && item.get('id');
        },

        /** Template of row */
        _templateRow: function( options ) {
            return  '<tr class="upload-ftp-row">' +
                        '<td class="_has_collection" style="display: none;"><div class="icon"/></td>' +
                        '<td class="ftp-name">' + options.path + '</td>' +
                        '<td class="ftp-size">' + Utils.bytesToString( options.size ) + '</td>' +
                        '<td class="ftp-time">' + options.ctime + '</td>' +
                    '</tr>';
        },

        /** Template of table */
        _templateTable: function() {
            return  '<span style="whitespace: nowrap; float: left;">Available files: </span>' +
                    '<span style="whitespace: nowrap; float: right;">' +
                        '<span class="upload-icon fa fa-file-text-o"/>' +
                        '<span class="upload-ftp-number"/>&nbsp;&nbsp;' +
                        '<span class="upload-icon fa fa-hdd-o"/>' +
                        '<span class="upload-ftp-disk"/>' +
                    '</span>' +
                    '<table class="grid" style="float: left;">' +
                        '<thead>' +
                            '<tr>' +
                                '<th class="_has_collection" style="display: none;"><div class="upload-selectall"></th>' +
                                '<th>Name</th>' +
                                '<th>Size</th>' +
                                '<th>Created</th>' +
                            '</tr>' +
                        '</thead>' +
                        '<tbody/>' +
                    '</table>';
        },

        /** Template of info message */
        _templateInfo: function() {
            return  '<div class="upload-ftp-warning warningmessage">' +
                        'Your FTP directory does not contain any files.' +
                    '</div>';
        },

        /** Template of main view */
        _template: function() {
            return  '<div class="upload-ftp">' +
                        '<div class="upload-ftp-wait fa fa-spinner fa-spin"/>' +
                        '<div class="upload-ftp-help">This Galaxy server allows you to upload files via FTP. To upload some files, log in to the FTP server at <strong>' + this.options.ftp_upload_site + '</strong> using your Galaxy credentials (email address and password).</div>' +
                        '<div class="upload-ftp-content"/>' +
                    '<div>';
        }
    });
});
