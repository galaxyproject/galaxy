// dependencies
define(['utils/utils',
        'mvc/upload/upload-model',
        'mvc/upload/upload-settings',
        'mvc/ui/ui-popover',
        'mvc/ui/ui-select',
        'utils/uploadbox'],

        function(   Utils,
                    UploadModel,
                    UploadSettings,
                    Popover,
                    Select
                ) {

// item view
return Backbone.View.extend({
    // options
    options: {
        padding : 8
    },

    // states
    status_classes : {
        init    : 'status fa fa-exclamation text-primary',
        ready   : 'status fa fa-check text-success',
        running : 'status fa fa-spinner fa-spin',
        success : 'status fa fa-check',
        error   : 'status fa fa-exclamation-triangle'
    },

    // source options
    list_sources: [ { id: '', text: 'Select a source...' },
                    { id: 'local', text: 'Choose local file' },
                    { id: 'ftp', text: 'Choose FTP file' },
                    { id: 'url', text: 'Paste/fetch data' } ],

    // source selector
    select_source : null,

    // initialize
    initialize: function(app, options) {
        // link app
        this.app = app;

        // link this
        var self = this;

        // create model
        this.model = new UploadModel.Model(options);

        // add upload item
        this.setElement(this._template(options));

        // link item
        var it = this.$el;

        // build upload functions
        var uploadinput = it.uploadinput({
            onchange: function(files) {
                if (files && files.length > 0) {
                    self.model.set('file_name', files[0].name);
                    self.model.set('file_size', files[0].size);
                }
            }
        });

        // append popup to settings icon
        this.settings = new Popover.View({
            title       : 'Upload configuration',
            container   : it.find('#settings'),
            placement   : 'bottom'
        });

        // initialize source selection field
        this.select_source = new Select.View({
            css: 'source',
            onchange : function(source) {
                if (source == 'local') {
                    uploadinput.dialog();
                }
                //self.model.set('genome', genome);
                //self.app.updateGenome(genome, true);
            },
            data: self.list_sources,
            container: it.find('#source'),
            placeholder: 'Select a source...'
        });

        //
        // ui events
        //

        // handle text editing event
        it.find('#text-content').on('keyup', function(e) {
            self.model.set('url_paste', $(e.target).val());
            self.model.set('file_size', $(e.target).val().length);
        });

        // handle settings popover
        it.find('#settings').on('click' , function(e) { self._showSettings(); })
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
        // read model
        var file_name   = this.model.get('file_name');
        var file_desc   = this.model.get('file_desc');
        var file_size   = this.model.get('file_size');
        var file_mode   = this.model.get('file_mode');

        // update title, description etc.
        this.$('#file_name').html(file_name);
        this.$('#file_desc').html(file_desc);
        this.$('#file_size').html(Utils.bytesToString (file_size));

        // remove mode class
        this.$('#status')
            .removeClass()
            .addClass('status');

        // activate text field if file is new
        if (file_mode == 'new') {
            // get text component
            var text = this.$('#text');

            // get padding
            var padding = this.options.padding;

            // get dimensions
            var width = this.$el.width() - 2 * padding;
            var height = this.$el.height() - padding;

            // set dimensions
            text.css('width', width + 'px');
            text.css('top', height + 'px');
            this.$el.height(height + text.height() + 2 * padding);

            // show text field
            text.show();
        }

        // file from ftp
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

    // progress
    _refreshInfo: function() {
        // write error message
        var info = this.model.get('info');
        if (info) {
            this.$('#info').html('<strong>Failed: </strong>' + info).show();
        } else {
            this.$('#info').hide();
        }
    },

    // progress
    _refreshPercentage : function() {
        var percentage = parseInt(this.model.get('percentage'));
        this.$('.progress-bar').css({ width : percentage + '%' });
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

        // enable/disable row fields
        this.$('#text-content').attr('disabled', status != 'init');

        // success
        if (status == 'success') {
            this.$el.addClass('success');
            this.$('#percentage').html('100%');
        }

        // error
        if (status == 'error') {
            this.$el.addClass('danger');
            this.$('.progress').remove();
        }
    },

    // refresh file name
    _refreshFileName: function() {
        this.$('#file_name').html(this.model.get('file_name'));
    },

    // refresh size
    _refreshFileSize: function() {
        var file_size = this.model.get('file_size');
        this.$('#file_size').html(Utils.bytesToString (file_size));
        this.model.set('status', (file_size > 0 && 'ready') || 'init');
    },

    // attach file info popup
    _showSettings : function() {
        // check if popover is visible
        if (!this.settings.visible) {
            // show popover
            this.settings.empty();
            this.settings.append((new UploadSettings(this)).$el);
            this.settings.show();
        } else {
            // hide popover
            this.settings.hide();
        }
    },

    // template
    _template: function(options) {
        return  '<tr id="upload-item-' + options.id + '" class="upload-item">' +
                    '<td>' +
                        '<div id="status"/>' +
                    '</td>' +
                    '<td>' +
                        '<div id="source" class="source"/>' +
                    '</td>' +
                    '<td>' +
                        '<div id="file_desc" class="title"/>' +
                    '</td>' +
                    '<td>' +
                        '<div class="title-column">' +
                            '<div id="file_name" class="title"/>' +
                            '<div id="text" class="text">' +
                                '<div class="text-info">You can tell Galaxy to download data from web by entering URL in this box (one per line). You can also directly paste the contents of a file.</div>' +
                                '<textarea id="text-content" class="text-content form-control"></textarea>' +
                            '</div>' +
                        '</div>' +
                    '</td>' +
                    '<td>' +
                        '<div id="file_size" class="size"/>' +
                    '</td>' +
                    '<td><div id="settings" class="upload-icon-button fa fa-gear"/></td>' +
                    '<td>' +
                        '<div id="info" class="info">' +
                            '<div class="progress">' +
                                '<div class="progress-bar progress-bar-success"></div>' +
                                '<div id="percentage" class="percentage">0%</div>' +
                            '</div>' +
                        '</div>' +
                    '</td>' +
                '</tr>';
    }

});

});
