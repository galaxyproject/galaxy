// dependencies
define(['utils/utils'], function(Utils) {

// item view
return Backbone.View.extend({
    // options
    options: {
        class_add       : 'upload-icon-button fa fa-square-o',
        class_remove    : 'upload-icon-button fa fa-check-square-o'
    },
    
    // render
    initialize: function(app) {
        // link app
        this.app = app;
        
        // link this
        var self = this;
        
        // set template
        this.setElement(this._template());
        
        // load extension
        Utils.get(galaxy_config.root + 'api/ftp_files', function(ftp_files) { self._fill(ftp_files); });
    },
    
    // events
    events: {
        'mousedown' : function(e) { e.preventDefault(); }
    },
    
    // fill table
    _fill: function(ftp_files) {
        if (ftp_files.length > 0) {
            // add table
            this.$el.find('#upload-ftp-content').html($(this._templateTable()));
            
            // add files to table
            var size = 0;
            for (key in ftp_files) {
                this.add(ftp_files[key]);
                size += ftp_files[key].size;
            }
            
            // update stats
            this.$el.find('#upload-ftp-number').html(ftp_files.length + ' files');
            this.$el.find('#upload-ftp-disk').html(Utils.bytesToString (size, true));
        } else {
            // add info
            this.$el.find('#upload-ftp-content').html($(this._templateInfo()));
        }
        
        // hide spinner
        this.$el.find('#upload-ftp-wait').hide();
    },
    
    // add
    add: function(ftp_file) {
        // create new item
        var $it = $(this._templateRow(ftp_file));
        
        // append to table
        $(this.el).find('tbody').append($it);
        
        // find model and set initial 'add' icon class
        var icon_class = '';
        if (this._find(ftp_file)) {
            icon_class = this.options.class_remove;
        } else {
            icon_class = this.options.class_add;
        }
        $it.find('#upload-ftp-add').addClass(icon_class);

        // click to add ftp files
        var self = this;
        $it.find('#upload-ftp-add').on('click', function() {
            // find model
            var model_index = self._find(ftp_file);
            
            // update icon
            $(this).removeClass();
                
            // add model
            if (!model_index) {
                // add to uploadbox
                self.app.uploadbox.add([{
                    mode        : 'ftp',
                    name        : ftp_file.path,
                    size        : ftp_file.size,
                    path        : ftp_file.path
                }]);
                
                // add new icon class
                $(this).addClass(self.options.class_remove);
            } else {
                // remove
                self.app.collection.remove(model_index);
                
                // add new icon class
                $(this).addClass(self.options.class_add);
            }
        });
    },
    
    // get model index
    _find: function(ftp_file) {
        // check if exists already
        var filtered = this.app.collection.where({file_path : ftp_file.path});
        var model_index = null;
        for (var key in filtered) {
            var item = filtered[key];
            if (item.get('status') == 'init' && item.get('file_mode') == 'ftp') {
                model_index = item.get('id');
            }
        }
        return model_index;
    },
    
    // template row
    _templateRow: function(options) {
        return  '<tr>' +
                    '<td><div id="upload-ftp-add"/></td>' +
                    '<td style="width: 200px"><p style="width: inherit; word-wrap: break-word;">' + options.path + '</p></td>' +
                    '<td style="white-space: nowrap;">' + Utils.bytesToString(options.size) + '</td>' +
                    '<td style="white-space: nowrap;">' + options.ctime + '</td>' +
                '</tr>';
    },
    
    // load table template
    _templateTable: function() {
        return  '<span style="whitespace: nowrap; float: left;">Available files: </span>' +
                '<span style="whitespace: nowrap; float: right;">' +
                    '<span class="upload-icon fa fa-file-text-o"/>' +
                    '<span id="upload-ftp-number"/>&nbsp;&nbsp;' +
                    '<span class="upload-icon fa fa-hdd-o"/>' +
                    '<span id="upload-ftp-disk"/>' +
                '</span>' +
                '<table class="grid" style="float: left;">' +
                    '<thead>' +
                        '<tr>' +
                            '<th></th>' +
                            '<th>Name</th>' +
                            '<th>Size</th>' +
                            '<th>Created</th>' +
                        '</tr>' +
                    '</thead>' +
                    '<tbody></tbody>' +
                '</table>';
    },
    
    // load table template
    _templateInfo: function() {
        return  '<div class="upload-ftp-warning warningmessage">' +
                    'Your FTP directory does not contain any files.' +
                '</div>';
    },
    
    // load html template
    _template: function() {
        return  '<div class="upload-ftp">' +
                    '<div id="upload-ftp-wait" class="upload-ftp-wait fa fa-spinner fa-spin"/>' +
                    '<div class="upload-ftp-help">This Galaxy server allows you to upload files via FTP. To upload some files, log in to the FTP server at <strong>' + this.app.options.ftp_upload_site + '</strong> using your Galaxy credentials (email address and password).</div>' +
                    '<div id="upload-ftp-content"></div>' +
                '<div>';
    }
    
});

});
