// dependencies
define(['utils/utils',
        'mvc/upload/upload-settings',
        'mvc/ui/ui-popover',
        'mvc/ui/ui-misc',
        'mvc/ui/ui-select',
        'utils/uploadbox'],

        function(   Utils,
                    UploadSettings,
                    Popover,
                    Ui,
                    Select
                ) {

// renders the composite upload row view
return Backbone.View.extend({
    // states
    status_classes : {
        init    : 'status fa fa-exclamation text-primary',
        ready   : 'status fa fa-check text-success',
        running : 'status fa fa-spinner fa-spin',
        success : 'status fa fa-check',
        error   : 'status fa fa-exclamation-triangle'
    },

    // initialize
    initialize: function(app, options) {
        // link app
        this.app = app;

        // link this
        var self = this;

        // create model
        this.model = options.model;

        // add upload item
        this.setElement(this._template(options.model));

        // build upload functions
        this.uploadinput = this.$el.uploadinput({
            ondragover: function() {
                if (self.model.get('status') != 'running') {
                    self.$el.addClass('warning');
                }
            },
            ondragleave: function() {
                self.$el.removeClass('warning');
            },
            onchange: function(files) {
                if (self.model.get('status') != 'running' && files && files.length > 0) {
                    self.model.set('file_data', files[0]);
                    self.model.set('file_name', files[0].name);
                    self.model.set('file_size', files[0].size);
                    self.model.set('file_mode', files[0].mode || 'local');
                }
            }
        });

        // append popup to settings icon
        this.settings = new Popover.View({
            title       : 'Upload configuration',
            container   : this.$('#settings'),
            placement   : 'bottom'
        });

        // source selection popup
        this.button_menu = new Ui.ButtonMenu({
            icon        : 'fa-caret-down',
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

        //
        // ui events
        //

        // handle text editing event
        this.$('#text-content').on('keyup', function(e) {
            self.model.set('url_paste', $(e.target).val());
            self.model.set('file_size', $(e.target).val().length);
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
        this.$('#file_name').html(this.model.get('file_name'));
        this.$('#file_desc').html(this.model.get('file_desc'));
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

    // mode
    _refreshMode: function() {
        // activate text field if file is new
        var file_mode = this.model.get('file_mode');
        if (file_mode == 'new') {
            this.$('#text').css({
                'width' : this.$el.width() - 2 * 8 + 'px',
                'top'   : this.$el.height() - 8 + 'px'
            }).show();
            this.$el.height(this.$el.height() - 8 + this.$('#text').height() + 2 * 8);
        } else {
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
        this.model.set('enabled', status == 'init' || status == 'ready');

        // enable/disable row fields
        this.$('#text-content').attr('disabled', !this.model.get('enabled'));

        // remove status classes
        this.$el.removeClass('success danger');

        // set status classes
        if (status == 'running' || status == 'ready') {
            this.$el.addClass('success');
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
        this.$('#file_name').html(this.model.get('file_name'));
    },

    // file size
    _refreshFileSize: function() {
        var file_size = this.model.get('file_size');
        this.$('#file_size').html(Utils.bytesToString (file_size));
        this.model.set('status', (file_size > 0 && 'ready') || 'init');
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
        return  '<tr id="upload-item-' + options.id + '" class="upload-item">' +
                    '<td>' +
                        '<div id="source"/>' +
                    '</td>' +
                    '<td>' +
                        '<div id="status"/>' +
                    '</td>' +
                    '<td>' +
                        '<div id="file_desc" class="title"/>' +
                    '</td>' +
                    '<td>' +
                        '<div class="title-column">' +
                            '<div id="file_name" class="title"/>' +
                            '<div id="text" class="text">' +
                                '<div class="text-info">You can tell Galaxy to download data from web by entering URL in this box (one per line). You can also directly paste the contents of a file.</div>' +
                                '<textarea id="text-content" class="text-content form-control"/>' +
                            '</div>' +
                        '</div>' +
                    '</td>' +
                    '<td>' +
                        '<div id="file_size" class="size"/>' +
                    '</td>' +
                    '<td><div id="settings" class="upload-icon-button fa fa-gear"/></td>' +
                    '<td>' +
                        '<div id="info" class="info">' +
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
