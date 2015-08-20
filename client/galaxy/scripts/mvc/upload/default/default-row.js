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

// row view
return Backbone.View.extend({
    // states
    status_classes : {
        init    : 'upload-icon-button fa fa-trash-o',
        queued  : 'upload-icon fa fa-spinner fa-spin',
        running : 'upload-icon fa fa-spinner fa-spin',
        success : 'upload-icon-button fa fa-check',
        error   : 'upload-icon-button fa fa-exclamation-triangle'
    },

    // handle for settings popover
    settings: null,

    // genome selector
    select_genome : null,

    // extension selector
    select_extension : null,

    // render
    initialize: function(app, options) {
        // link app
        this.app = app;

        // link this
        var self = this;

        // create model
        this.model = options.model;

        // add upload row
        this.setElement(this._template(options.model));

        // append popup to settings icon
        this.settings = new Popover.View({
            title       : 'Upload configuration',
            container   : this.$('#settings'),
            placement   : 'bottom'
        });

        // initialize default genome through default select field
        var default_genome = this.app.select_genome.value();
        
        // select genomes
        this.select_genome = new Select.View({
            css: 'upload-genome',
            onchange : function(genome) {
                self.model.set('genome', genome);
                self.app.updateGenome(genome, true);
            },
            data: self.app.list_genomes,
            container: this.$('#genome'),
            value: default_genome
        });

        // initialize genome
        this.model.set('genome', default_genome);

        // initialize default extension through default select field
        var default_extension = this.app.select_extension.value();
        
        // select extension
        this.select_extension = new Select.View({
            css: 'upload-extension',
            onchange : function(extension) {
                self.model.set('extension', extension);
                self.app.updateExtension(extension, true);
            },
            data: self.app.list_extensions,
            container: this.$('#extension'),
            value: default_extension
        });

        // initialize extension
        this.model.set('extension', default_extension);
        
        //
        // ui events
        //

        // handle click event
        this.$('#symbol').on('click', function() { self._removeRow(); });

        // handle extension info popover
        this.$('#extension-info').on('click' , function(e) {
            self.app.showExtensionInfo({
                $el         : $(e.target),
                title       : self.select_extension.text(),
                extension   : self.select_extension.value()
            });
        }).on('mousedown', function(e) { e.preventDefault(); });

        // handle settings popover
        this.$('#settings').on('click' , function(e) { self._showSettings(); })
                            .on('mousedown', function(e) { e.preventDefault(); });

        // handle text editing event
        this.$('#text-content').on('keyup', function(e) {
            self.model.set('url_paste', $(e.target).val());
            self.model.set('file_size', $(e.target).val().length);
        });

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
        this.model.on('change:genome', function() {
            self._refreshGenome();
        });
        this.model.on('change:extension', function() {
            self._refreshExtension();
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
        var file_size   = this.model.get('file_size');
        var file_mode   = this.model.get('file_mode');

        // update title
        this.$('#title').html(file_name);

        // update info
        this.$('#size').html(Utils.bytesToString (file_size));

        // remove mode class
        this.$('#mode')
            .removeClass()
            .addClass('upload-mode')
            .addClass('text-primary');

        // activate text field if file is new
        if (file_mode == 'new') {
            this.$('#text').css({
                'width' : this.$el.width() - 16 + 'px',
                'top'   : this.$el.height() - 8 + 'px'
            }).show();
            this.$el.height(this.$el.height() - 8 + this.$('#text').height() + 16);
            this.$('#mode').addClass('fa fa-edit');
        }

        // file from local disk
        if (file_mode == 'local') {
            this.$('#mode').addClass('fa fa-laptop');
        }

        // file from ftp
        if (file_mode == 'ftp') {
            this.$('#mode').addClass('fa fa-folder-open-o');
        }
    },

    // remove
    remove: function() {
        // trigger remove event
        this.select_genome.remove();
        this.select_extension.remove();

        // call the base class remove method
        Backbone.View.prototype.remove.apply(this);
    },

    //
    // handle model events
    //

    // update extension
    _refreshExtension: function() {
        this.select_extension.value(this.model.get('extension'));
    },
    
    // update genome
    _refreshGenome: function() {
        this.select_genome.value(this.model.get('genome'));
    },

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
        if (percentage != 100)
            this.$('#percentage').html(percentage + '%');
        else
            this.$('#percentage').html('Adding to history...');
    },

    // status
    _refreshStatus : function() {
        // identify new status
        var status = this.model.get('status');

        // identify symbol and reset classes
        this.$('#symbol').removeClass().addClass(this.status_classes[status]);

        // enable/disable model flag
        this.model.set('enabled', status == 'init');

        // enable/disable row fields
        var enabled = this.model.get('enabled');
        this.$('#text-content').attr('disabled', !enabled);
        if (enabled) {
            this.select_genome.enable();
            this.select_extension.enable();
        } else {
            this.select_genome.disable();
            this.select_extension.disable();
        }

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

    // refresh size
    _refreshFileSize: function() {
        var count = this.model.get('file_size');
        this.$('#size').html(Utils.bytesToString (count));
    },

    //
    // handle ui events
    //

    // remove row
    _removeRow: function() {
        // get current status
        var status = this.model.get('status');

        // only remove from queue if not in processing line
        if (status == 'init' || status == 'success' || status == 'error') {
            this.app.collection.remove(this.model);
        }
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
        return  '<tr id="upload-row-' + options.id + '" class="upload-row">' +
                    '<td>' +
                        '<div class="upload-text-column">' +
                            '<div id="mode"/>' +
                            '<div id="title" class="upload-title"/>' +
                            '<div id="text" class="text">' +
                                '<div class="text-info">You can tell Galaxy to download data from web by entering URL in this box (one per line). You can also directly paste the contents of a file.</div>' +
                                '<textarea id="text-content" class="text-content form-control"/>' +
                            '</div>' +
                        '</div>' +
                    '</td>' +
                    '<td>' +
                        '<div id="size" class="upload-size"/>' +
                    '</td>' +
                    '<td>' +
                        '<div id="extension" class="upload-extension" style="float: left;"/>&nbsp;&nbsp' +
                        '<div id="extension-info" class="upload-icon-button fa fa-search"/>' +
                    '</td>' +
                    '<td>' +
                        '<div id="genome" class="upload-genome"/>' +
                    '</td>' +
                    '<td><div id="settings" class="upload-icon-button fa fa-gear"/></td>' +
                    '<td>' +
                        '<div id="info" class="upload-info">' +
                            '<div class="progress">' +
                                '<div class="progress-bar progress-bar-success"/>' +
                                '<div id="percentage" class="percentage">0%</div>' +
                            '</div>' +
                        '</div>' +
                    '</td>' +
                    '<td>' +
                        '<div id="symbol" class="' + this.status_classes.init + '"/>' +
                    '</td>' +
                '</tr>';
    }

});

});
