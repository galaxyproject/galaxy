// dependencies
define(['utils/utils'], function(Utils) {

// item view
return Backbone.View.extend({
    // options
    options: {
        class_add       : 'upload-icon-button fa fa-square-o',
        class_remove    : 'upload-icon-button fa fa-check-square-o',
        class_partial   : 'upload-icon-button fa fa-minus-square-o'
    },

    // render
    initialize: function(app) {
        // link app
        this.app = app;

        // link this
        var self = this;

        // set template
        this.setElement(this._template());

        // list of rows
        this.rows = [];

        // load extension
        Utils.get({
            url     : galaxy_config.root + 'api/ftp_files',
            success : function(ftp_files) { self._fill(ftp_files); },
            error   : function() { self._fill(); }
        });
    },

    // events
    events: {
        'mousedown' : function(e) { e.preventDefault(); }
    },

    // fill table
    _fill: function(ftp_files) {
        if (ftp_files && ftp_files.length > 0) {
            // add table
            this.$el.find('#upload-ftp-content').html($(this._templateTable()));

            // add files to table
            var size = 0;
            for (key in ftp_files) {
                this.rows.push(this._add(ftp_files[key]));
                size += ftp_files[key].size;
            }

            // update stats
            this.$el.find('#upload-ftp-number').html(ftp_files.length + ' files');
            this.$el.find('#upload-ftp-disk').html(Utils.bytesToString (size, true));

            // add event handler to select/unselect all
            this.$select_all = $('#upload-selectall');
            this.$select_all.addClass(this.options.class_add);
            var self = this;
            this.$select_all.on('click', function() {
                var add = self.$select_all.hasClass(self.options.class_add);
                for (key in ftp_files) {
                    var ftp_file = ftp_files[key];
                    var model_index = self._find(ftp_file);
                    if(!model_index && add || model_index && !add) {
                        self.rows[key].trigger('click');
                    }
                }
            });

            // refresh
            self._refresh();
        } else {
            // add info
            this.$el.find('#upload-ftp-content').html($(this._templateInfo()));
        }

        // hide spinner
        this.$el.find('#upload-ftp-wait').hide();
    },

    // add
    _add: function(ftp_file) {
        // link this
        var self = this;

        // create new item
        var $it = $(this._templateRow(ftp_file));

        // identify icon
        var $icon = $it.find('.icon');

        // append to table
        $(this.el).find('tbody').append($it);

        // find model and set initial 'add' icon class
        var icon_class = '';
        if (this._find(ftp_file)) {
            icon_class = this.options.class_remove;
        } else {
            icon_class = this.options.class_add;
        }

        // add icon class
        $icon.addClass(icon_class);

        // click to add ftp files
        $it.on('click', function() {
            // find model
            var model_index = self._find(ftp_file);

            // update icon
            $icon.removeClass();

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
                $icon.addClass(self.options.class_remove);
            } else {
                // remove
                self.app.collection.remove(model_index);

                // add new icon class
                $icon.addClass(self.options.class_add);
            }

            // update select all checkbox
            self._refresh();
        });

        // return dom handler
        return $it;
    },

    // refresh
    _refresh: function() {
        var filtered = this.app.collection.where({file_mode : 'ftp'});
        this.$select_all.removeClass();
        if (filtered.length == 0) {
            this.$select_all.addClass(this.options.class_add);
        } else {
            if (filtered.length == this.rows.length) {
                this.$select_all.addClass(this.options.class_remove);
            } else {
                this.$select_all.addClass(this.options.class_partial);
            }
        }
    },

    // get model index
    _find: function(ftp_file) {
        var item = this.app.collection.findWhere({
            file_path   : ftp_file.path,
            status      : 'init',
            file_mode   : 'ftp'
        });
        if (item) {
            return item.get('id');
        }
        return null;
    },

    // template row
    _templateRow: function(options) {
        return  '<tr class="upload-ftp-row">' +
                    '<td><div class="icon"/></td>' +
                    '<td class="label"><p>' + options.path + '</p></td>' +
                    '<td class="nonlabel">' + Utils.bytesToString(options.size) + '</td>' +
                    '<td class="nonlabel">' + options.ctime + '</td>' +
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
                            '<th><div id="upload-selectall"></th>' +
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
