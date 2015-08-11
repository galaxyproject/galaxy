/** This renders the content of the ftp popup **/
define(['utils/utils'], function(Utils) {
return Backbone.View.extend({
    // render
    initialize: function(options) {
        // link options
        this.options = Utils.merge(options, {
            class_add       : 'upload-icon-button fa fa-square-o',
            class_remove    : 'upload-icon-button fa fa-check-square-o',
            class_partial   : 'upload-icon-button fa fa-minus-square-o',
            collection      : null,
            onchange        : function() {},
            onadd           : function() {},
            onremove        : function() {}
        });

        // link this
        var self = this;

        // link app
        this.collection = this.options.collection;

        // set template
        this.setElement(this._template());

        // list of rows
        this.rows = [];

        // load extension
        Utils.get({
            url     : galaxy_config.root + 'api/remote_files',
            success : function(ftp_files) { self._fill(ftp_files); },
            error   : function() { self._fill(); }
        });
    },

    // events
    events: {
        'mousedown': function(e) { e.preventDefault(); }
    },

    // fill table
    _fill: function(ftp_files) {
        if (ftp_files && ftp_files.length > 0) {
            // add table
            this.$el.find('#upload-ftp-content').html($(this._templateTable()));

            // add files to table
            var size = 0;
            for (index in ftp_files) {
                this.rows.push(this._add(ftp_files[index]));
                size += ftp_files[index].size;
            }

            // update stats
            this.$el.find('#upload-ftp-number').html(ftp_files.length + ' files');
            this.$el.find('#upload-ftp-disk').html(Utils.bytesToString (size, true));

            // add event handler to select/unselect all
            if (this.collection) {
                var self = this;
                this.$('._has_collection').show();
                this.$select_all = $('#upload-selectall');
                this.$select_all.addClass(this.options.class_add);
                this.$select_all.on('click', function() {
                    var add = self.$select_all.hasClass(self.options.class_add);
                    for (index in ftp_files) {
                        var ftp_file = ftp_files[index];
                        var model_index = self._find(ftp_file);
                        if(!model_index && add || model_index && !add) {
                            self.rows[index].trigger('click');
                        }
                    }
                });
                this._refresh();
            }
        } else {
            this.$el.find('#upload-ftp-content').html($(this._templateInfo()));
        }
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

        // collection mode with add/remove triggers
        if (this.collection) {
            // find model and set initial 'add' icon class
            var icon_class = '';
            if (this._find(ftp_file)) {
                icon_class = this.options.class_remove;
            } else {
                icon_class = this.options.class_add;
            }
            $icon.addClass(icon_class);

            // click triggers add/remove events
            $it.on('click', function() {
                var model_index = self._find(ftp_file);
                $icon.removeClass();
                if (!model_index) {
                    self.options.onadd(ftp_file);
                    $icon.addClass(self.options.class_remove);
                } else {
                    self.options.onremove(model_index);
                    $icon.addClass(self.options.class_add);
                }
                self._refresh();
            });
        } else {
            // click triggers only change
            $it.on('click', function() {
                self.options.onchange(ftp_file);
            });
        }

        // return dom handler
        return $it;
    },

    // refresh
    _refresh: function() {
        var filtered = this.collection.where({file_mode: 'ftp', enabled: true});
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
        var item = this.collection.findWhere({
            file_path   : ftp_file.path,
            file_mode   : 'ftp',
            enabled     : true
        });
        return item && item.get('id');
    },

    // template row
    _templateRow: function(options) {
        return  '<tr class="upload-ftp-row">' +
                    '<td class="_has_collection" style="display: none;"><div class="icon"/></td>' +
                    '<td class="ftp-name">' + options.path + '</td>' +
                    '<td class="ftp-size">' + Utils.bytesToString(options.size) + '</td>' +
                    '<td class="ftp-time">' + options.ctime + '</td>' +
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
                            '<th class="_has_collection" style="display: none;"><div id="upload-selectall"></th>' +
                            '<th>Name</th>' +
                            '<th>Size</th>' +
                            '<th>Created</th>' +
                        '</tr>' +
                    '</thead>' +
                    '<tbody/>' +
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
                    '<div class="upload-ftp-help">This Galaxy server allows you to upload files via FTP. To upload some files, log in to the FTP server at <strong>' + this.options.ftp_upload_site + '</strong> using your Galaxy credentials (email address and password).</div>' +
                    '<div id="upload-ftp-content"/>' +
                '<div>';
    }
});

});
