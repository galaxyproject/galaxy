// dependencies
define(['utils/utils',
        'mvc/upload/upload-settings',
        'mvc/upload/upload-ftp',
        'mvc/ui/ui-popover',
        'mvc/ui/ui-misc',
        'mvc/ui/ui-select',
        'utils/uploadbox'],

        function(   Utils,
                    UploadSettings,
                    UploadFtp,
                    Popover,
                    Ui,
                    Select
                ) {

// renders the composite upload row view
return Backbone.View.extend({
    // states
    status_classes : {
        init    : 'upload-mode fa fa-exclamation text-primary',
        ready   : 'upload-mode fa fa-check text-success',
        running : 'upload-mode fa fa-spinner fa-spin',
        success : 'upload-mode fa fa-check',
        error   : 'upload-mode fa fa-exclamation-triangle'
    },

    // initialize
    initialize: function(app, options) {
        // link app
        this.app = app;

        // link this
        var self = this;

        // create model
        this.model = options.model;

        // add upload row
        this.setElement(this._template(options.model));

        // build upload functions
        this.uploadinput = this.$el.uploadinput({
            ondragover: function() {
                if (self.model.get('enabled')) {
                    self.$el.addClass('warning');
                }
            },
            ondragleave: function() {
                self.$el.removeClass('warning');
            },
            onchange: function(files) {
                if (self.model.get('status') != 'running' && files && files.length > 0) {
                    self.model.reset({
                        'file_data': files[0],
                        'file_name': files[0].name,
                        'file_size': files[0].size,
                        'file_mode': files[0].mode || 'local'
                    });
                    self._refreshReady();
                }
            }
        });

        // source selection popup
        this.button_menu = new Ui.ButtonMenu({
            icon        : 'fa-caret-down',
            title       : 'Select',
            pull        : 'left'
        });
        this.$('#source').append(this.button_menu.$el);
        this.button_menu.addMenu({
            icon        : 'fa-laptop',
            title       : 'Choose local file',
            onclick     : function() {
                self.uploadinput.dialog();
            }
        });
        if (this.app.ftp_upload_site) {
            this.button_menu.addMenu({
                icon        : 'fa-folder-open-o',
                title       : 'Choose FTP file',
                onclick     : function() {
                    self._showFtp();
                }
            });
        }
        this.button_menu.addMenu({
            icon        : 'fa-edit',
            title       : 'Paste/Fetch data',
            onclick     : function() {
                self.model.reset({
                    'file_mode': 'new',
                    'file_name': 'New File'
                });
            }
        });

        // add ftp file viewer
        this.ftp = new Popover.View({
            title       : 'Choose FTP file:',
            container   : this.$('#source').find('.ui-button-menu'),
            placement   : 'right'
        });

        // append popup to settings icon
        this.settings = new Popover.View({
            title       : 'Upload configuration',
            container   : this.$('#settings'),
            placement   : 'bottom'
        });

        //
        // ui events
        //

        // handle text editing event
        this.$('#text-content').on('keyup', function(e) {
            self.model.set('url_paste', $(e.target).val());
            self.model.set('file_size', $(e.target).val().length);
            self._refreshReady();
        });

        // handle settings popover
        this.$('#settings').on('click' , function(e) { self._showSettings(); })
                           .on('mousedown', function(e) { e.preventDefault(); });

        //
        // model events
        //
        this.model.on('change:percentage', function() {
            self._refreshPercentage();
        });
        this.model.on('change:status', function() {
            self._refreshStatus();
        });
        this.model.on('change:info', function() {
            self._refreshInfo();
        });
        this.model.on('change:file_name', function() {
            self._refreshFileName();
        });
        this.model.on('change:file_mode', function() {
            self._refreshMode();
        });
        this.model.on('change:file_size', function() {
            self._refreshFileSize();
        });
        this.model.on('remove', function() {
            self.remove();
        });
        this.app.collection.on('reset', function() {
            self.remove();
        });
    },

    // render
    render: function() {
        this.$('#file_name').html(this.model.get('file_name') || '-');
        this.$('#file_desc').html(this.model.get('file_desc') || 'Unavailable');
        this.$('#file_size').html(Utils.bytesToString (this.model.get('file_size')));
        this.$('#status').removeClass().addClass(this.status_classes.init);
    },

    // remove
    remove: function() {
        // call the base class remove method
        Backbone.View.prototype.remove.apply(this);
    },

    //
    // handle model events
    //

    // refresh ready or not states
    _refreshReady: function() {
        this.app.collection.each(function(model) {
            model.set('status', (model.get('file_size') > 0) && 'ready' || 'init');
        });
    },

    // refresh mode and e.g. show/hide textarea field
    _refreshMode: function() {
        var file_mode = this.model.get('file_mode');
        if (file_mode == 'new') {
            this.height = this.$el.height();
            this.$('#text').css({
                'width' : this.$el.width() - 16 + 'px',
                'top'   : this.$el.height() - 8 + 'px'
            }).show();
            this.$el.height(this.$el.height() - 8 + this.$('#text').height() + 16);
            this.$('#text-content').val('').trigger('keyup');
        } else {
            this.$el.height(this.height);
            this.$('#text').hide();
        }
    },

    // information
    _refreshInfo: function() {
        var info = this.model.get('info');
        if (info) {
            this.$('#info-text').html('<strong>Failed: </strong>' + info).show();
        } else {
            this.$('#info-text').hide();
        }
    },

    // percentage
    _refreshPercentage : function() {
        var percentage = parseInt(this.model.get('percentage'));
        if (percentage != 0) {
            this.$('.progress-bar').css({ width : percentage + '%' });
        } else {
            this.$('.progress-bar').addClass('no-transition');
            this.$('.progress-bar').css({ width : '0%' });
            this.$('.progress-bar')[0].offsetHeight;
            this.$('.progress-bar').removeClass('no-transition');
        }
        if (percentage != 100) {
            this.$('#percentage').html(percentage + '%');
        } else {
            this.$('#percentage').html('Adding to history...');
        }
    },

    // status
    _refreshStatus : function() {
        // identify new status
        var status = this.model.get('status');

        // identify symbol and reset classes
        this.$('#status').removeClass().addClass(this.status_classes[status]);

        // enable/disable model flag
        this.model.set('enabled', status != 'running');

        // enable/disable row fields
        this.$('#text-content').attr('disabled', !this.model.get('enabled'));

        // remove status classes
        this.$el.removeClass('success danger warning');

        // set status classes
        if (status == 'running' || status == 'ready') {
            this.model.set('percentage', 0);
        }
        if (status == 'running') {
            this.$('#source').find('.button').addClass('disabled');
        } else {
            this.$('#source').find('.button').removeClass('disabled');
        }
        if (status == 'success') {
            this.$el.addClass('success');
            this.model.set('percentage', 100);
            this.$('#percentage').html('100%');
        }
        if (status == 'error') {
            this.$el.addClass('danger');
            this.model.set('percentage', 0);
            this.$('#info-progress').hide();
            this.$('#info-text').show();
        } else {
            this.$('#info-progress').show();
            this.$('#info-text').hide();
        }
    },

    // file name
    _refreshFileName: function() {
        this.$('#file_name').html(this.model.get('file_name') || '-');
    },

    // file size
    _refreshFileSize: function() {
        this.$('#file_size').html(Utils.bytesToString (this.model.get('file_size')));
    },

    // show/hide ftp popup
    _showFtp: function() {
        if (!this.ftp.visible) {
            this.ftp.empty();
            var self = this;
            this.ftp.append((new UploadFtp({
                ftp_upload_site: this.app.ftp_upload_site,
                onchange: function(ftp_file) {
                    self.ftp.hide();
                    if (self.model.get('status') != 'running' && ftp_file) {
                        self.model.reset({
                            'file_mode': 'ftp',
                            'file_name': ftp_file.path,
                            'file_size': ftp_file.size,
                            'file_path': ftp_file.path
                        });
                        self._refreshReady();
                    }
                }
            })).$el);
            this.ftp.show();
        } else {
            this.ftp.hide();
        }
    },

    // show/hide settings popup
    _showSettings : function() {
        if (!this.settings.visible) {
            this.settings.empty();
            this.settings.append((new UploadSettings(this)).$el);
            this.settings.show();
        } else {
            this.settings.hide();
        }
    },

    // template
    _template: function(options) {
        return  '<tr id="upload-row-' + options.id + '" class="upload-row">' +
                    '<td>' +
                        '<div id="source"/>' +
                        '<div class="upload-text-column">' +
                            '<div id="text" class="text">' +
                                '<div class="text-info">You can tell Galaxy to download data from web by entering URL in this box (one per line). You can also directly paste the contents of a file.</div>' +
                                '<textarea id="text-content" class="text-content form-control"/>' +
                            '</div>' +
                        '</div>' +
                    '</td>' +
                    '<td>' +
                        '<div id="status"/>' +
                    '</td>' +
                    '<td>' +
                        '<div id="file_desc" class="upload-title"/>' +
                    '</td>' +
                    '<td>' +
                        '<div id="file_name" class="upload-title"/>' +
                    '</td>' +
                    '<td>' +
                        '<div id="file_size" class="upload-size"/>' +
                    '</td>' +
                    '<td><div id="settings" class="upload-icon-button fa fa-gear"/></td>' +
                    '<td>' +
                        '<div id="info" class="upload-info">' +
                            '<div id="info-text"/>' +
                            '<div id="info-progress" class="progress">' +
                                '<div class="progress-bar progress-bar-success"/>' +
                                '<div id="percentage" class="percentage">0%</div>' +
                            '</div>' +
                        '</div>' +
                    '</td>' +
                '</tr>';
    }
});
});
