// dependencies
define(['utils/utils',
        'mvc/upload/upload-model',
        'mvc/upload/upload-settings',
        'mvc/ui/ui-popover',
        'mvc/ui/ui-select'],

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
        init    : 'upload-icon-button fa fa-trash-o',
        queued  : 'upload-icon fa fa-spinner fa-spin',
        running : 'upload-icon fa fa-spinner fa-spin',
        success : 'upload-icon-button fa fa-check',
        error   : 'upload-icon-button fa fa-exclamation-triangle'
    },

    // source options
    list_sources: [ { id: '', text: 'Choose local file' },
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

        // link item
        var it = this.$el;

        // update title, description etc.
        it.find('#title').html(file_name);
        it.find('#description').html(file_desc);
        it.find('#size').html(Utils.bytesToString (file_size));

        // remove mode class
        it.find('#mode')
            .removeClass();
            //.addClass('mode');

        // activate text field if file is new
        if (file_mode == 'new') {
            // get text component
            var text = it.find('#text');

            // get padding
            var padding = this.options.padding;

            // get dimensions
            var width = it.width() - 2 * padding;
            var height = it.height() - padding;

            // set dimensions
            text.css('width', width + 'px');
            text.css('top', height + 'px');
            it.height(height + text.height() + 2 * padding);

            // show text field
            text.show();
        }

        // file from ftp
        //if (file_mode == 'ftp') {
        it.find('#mode').addClass('fa fa-exclamation text-primary');
        //}
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
            this.$el.find('#info').html('<strong>Failed: </strong>' + info).show();
        } else {
            this.$el.find('#info').hide();
        }
    },

    // progress
    _refreshPercentage : function() {
        var percentage = parseInt(this.model.get('percentage'));
        this.$el.find('.progress-bar').css({ width : percentage + '%' });
        if (percentage != 100)
            this.$el.find('#percentage').html(percentage + '%');
        else
            this.$el.find('#percentage').html('Adding to history...');
    },

    // status
    _refreshStatus : function() {
        // get element
        var it = this.$el;

        // identify new status
        var status = this.model.get('status');
        var status_class = this.status_classes[status];

        // identify symbol and reset classes
        var sy = this.$el.find('#symbol');
        sy.removeClass();

        // set new status class
        sy.addClass(status_class);

        // enable form fields
        if (status == 'init') {
            // select fields
            this.select_source.enable();

            // default fields
            it.find('#text-content').attr('disabled', false);
        } else {
            // select fields
            this.select_source.disable();

            // default fields
            it.find('#text-content').attr('disabled', true);
        }

        // success
        if (status == 'success') {
            it.addClass('success');
            it.find('#percentage').html('100%');
        }

        // error
        if (status == 'error') {
            it.addClass('danger');
            it.find('.progress').remove();
        }
    },

    // refresh size
    _refreshFileSize: function() {
        var count = this.model.get('file_size');
        this.$el.find('#size').html(Utils.bytesToString (count));
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
                        '<div id="mode"/>' +
                    '</td>' +
                    '<td>' +
                        '<div id="source" class="source"/>' +
                    '</td>' +
                    '<td>' +
                        '<div class="name-column">' +
                            '<div id="description" class="title"/>' +
                        '</div>' +
                    '</td>' +
                    '<td>' +
                        '<div class="name-column">' +
                            '<div id="title" class="title"/>' +
                            '<div id="text" class="text">' +
                                '<div class="text-info">You can tell Galaxy to download data from web by entering URL in this box (one per line). You can also directly paste the contents of a file.</div>' +
                                '<textarea id="text-content" class="text-content form-control"></textarea>' +
                            '</div>' +
                        '</div>' +
                    '</td>' +
                    '<td>' +
                        '<div id="size" class="size"/>' +
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
