/** Renders contents of the default uploader */
define(['utils/utils',
        'mvc/upload/upload-model',
        'mvc/upload/default/default-row',
        'mvc/upload/upload-ftp',
        'mvc/ui/ui-popover',
        'mvc/ui/ui-select',
        'mvc/ui/ui-misc',
        'utils/uploadbox'],

        function(   Utils,
                    UploadModel,
                    UploadRow,
                    UploadFtp,
                    Popover,
                    Select,
                    Ui
                ) {

return Backbone.View.extend({
    // extension selector
    select_extension : null,

    // genome selector
    select_genome: null,

    // jquery uploadbox plugin
    uploadbox: null,

    // current upload size in bytes
    upload_size: 0,

    // contains upload row models
    collection : new UploadModel.Collection(),

    // ftp file viewer
    ftp : null,

    // keeps track of the current uploader state
    counter : {
        announce    : 0,
        success     : 0,
        error       : 0,
        running     : 0,
        reset : function() {
            this.announce = this.success = this.error = this.running = 0;
        }
    },

    // initialize
    initialize : function(app) {
        // link app
        this.app                = app;
        this.options            = app.options;
        this.list_extensions    = app.list_extensions;
        this.list_genomes       = app.list_genomes;
        this.ui_button          = app.ui_button;
        this.ftp_upload_site    = app.currentFtp();

        // link this
        var self = this;

        // set element
        this.setElement(this._template());

        // create button section
        this.btnLocal    = new Ui.Button({ id: 'btn-local', title: 'Choose local file',   onclick: function() { self.uploadbox.select(); }, icon: 'fa fa-laptop' });
        this.btnFtp      = new Ui.Button({ id: 'btn-ftp',   title: 'Choose FTP file',     onclick: function() { self._eventFtp(); }, icon: 'fa fa-folder-open-o' });
        this.btnCreate   = new Ui.Button({ id: 'btn-new',   title: 'Paste/Fetch data',    onclick: function() { self._eventCreate(); }, icon: 'fa fa-edit' });
        this.btnStart    = new Ui.Button({ id: 'btn-start', title: 'Start',               onclick: function() { self._eventStart(); } });
        this.btnStop     = new Ui.Button({ id: 'btn-stop',  title: 'Pause',               onclick: function() { self._eventStop(); } });
        this.btnReset    = new Ui.Button({ id: 'btn-reset', title: 'Reset',               onclick: function() { self._eventReset(); } });
        this.btnClose    = new Ui.Button({ id: 'btn-close', title: 'Close',               onclick: function() { self.app.modal.hide(); } });

        // append buttons to dom
        var buttons = [ this.btnLocal, this.btnFtp, this.btnCreate, this.btnStop, this.btnReset, this.btnStart, this.btnClose ];
        for (var i in buttons) {
            this.$('#upload-buttons').prepend(buttons[i].$el);
        }

        // file upload
        var self = this;
        this.uploadbox = this.$('#upload-box').uploadbox({
            url             : this.app.options.nginx_upload_path,
            announce        : function(index, file) { self._eventAnnounce(index, file) },
            initialize      : function(index) { return self.app.toData([ self.collection.get(index) ], self.history_id) },
            progress        : function(index, percentage) { self._eventProgress(index, percentage) },
            success         : function(index, message) { self._eventSuccess(index, message) },
            error           : function(index, message) { self._eventError(index, message) },
            complete        : function() { self._eventComplete() },
            ondragover      : function() { self.$('.upload-box').addClass('highlight'); },
            ondragleave     : function() { self.$('.upload-box').removeClass('highlight'); }
        });

        // add ftp file viewer
        this.ftp = new Popover.View({
            title       : 'FTP files',
            container   : this.btnFtp.$el
        });

        // select extension
        this.select_extension = new Select.View({
            css         : 'footer-selection',
            container   : this.$('#footer-extension'),
            data        : _.filter(this.list_extensions, function(ext) { return !ext.composite_files }),
            value       : this.options.default_extension,
            onchange    : function(extension) {
                self.updateExtension(extension);
            }
        });

        // handle extension info popover
        self.$('#footer-extension-info').on('click', function(e) {
            self.showExtensionInfo({
                $el         : $(e.target),
                title       : self.select_extension.text(),
                extension   : self.select_extension.value(),
                placement   : 'top'
            });
        }).on('mousedown', function(e) { e.preventDefault(); });

        // genome extension
        this.select_genome = new Select.View({
            css         : 'footer-selection',
            container   : this.$('#footer-genome'),
            data        : this.list_genomes,
            value       : this.options.default_genome,
            onchange    : function(genome) {
                self.updateGenome(genome);
            }
        });

        // events
        this.collection.on('remove', function(model) {
            self._eventRemove(model);
        });

        // setup info
        this._updateScreen();
    },

    //
    // events triggered by the upload box plugin
    //

    // a new file has been dropped/selected through the uploadbox plugin
    _eventAnnounce: function(index, file) {
        // update counter
        this.counter.announce++;

        // create if model has not been created yet
        var new_model = new UploadModel.Model({
            id          : index,
            file_name   : file.name,
            file_size   : file.size,
            file_mode   : file.mode || 'local',
            file_path   : file.path,
            file_data   : file
        });

        // add model to collection
        this.collection.add(new_model);

        // create view/model
        var upload_row = new UploadRow(this, { model: new_model });

        // add upload row element to table
        this.$('#upload-table > tbody:first').append(upload_row.$el);

        // show on screen info
        this._updateScreen();

        // render
        upload_row.render();
    },

    // progress
    _eventProgress: function(index, percentage) {
        // set progress for row
        var it = this.collection.get(index);
        it.set('percentage', percentage);

        // update ui button
        this.ui_button.set('percentage', this._uploadPercentage(percentage, it.get('file_size')));
    },

    // success
    _eventSuccess: function(index, message) {
        // update status
        var it = this.collection.get(index);
        it.set('percentage', 100);
        it.set('status', 'success');

        // update ui button
        this.ui_button.set('percentage', this._uploadPercentage(100, it.get('file_size')));

        // update completed
        this.upload_completed += it.get('file_size') * 100;

        // update counter
        this.counter.announce--;
        this.counter.success++;

        // update on screen info
        this._updateScreen();

        // update galaxy history
        Galaxy.currHistoryPanel.refreshContents();
    },

    // error
    _eventError: function(index, message) {
        // get element
        var it = this.collection.get(index);

        // update status
        it.set('percentage', 100);
        it.set('status', 'error');
        it.set('info', message);

        // update ui button
        this.ui_button.set('percentage', this._uploadPercentage(100, it.get('file_size')));
        this.ui_button.set('status', 'danger');

        // update completed
        this.upload_completed += it.get('file_size') * 100;

        // update counter
        this.counter.announce--;
        this.counter.error++;

        // update on screen info
        this._updateScreen();
    },

    // queue is done
    _eventComplete: function() {
        // reset queued upload to initial status
        this.collection.each(function(model) {
            if(model.get('status') == 'queued') {
                model.set('status', 'init');
            }
        });

        // update running
        this.counter.running = 0;

        // update on screen info
        this._updateScreen();
    },

    //
    // events triggered by collection
    //

    // remove model from upload list
    _eventRemove: function(model) {
        // update status
        var status = model.get('status');

        // reduce counter
        if (status == 'success') {
            this.counter.success--;
        } else if (status == 'error') {
            this.counter.error--;
        } else {
            this.counter.announce--;
        }

        // remove from queue
        this.uploadbox.remove(model.id);

        // show on screen info
        this._updateScreen();
    },

    //
    // events triggered by this view
    //

    // [public] display extension info popup
    showExtensionInfo: function(options) {
        // initialize
        var self = this;
        var $el = options.$el;
        var extension = options.extension;
        var title = options.title;
        var description = _.findWhere(self.list_extensions, {'id': extension});

        // create popup
        this.extension_popup && this.extension_popup.remove();
        this.extension_popup = new Popover.View({
            placement: options.placement || 'bottom',
            container: $el,
            destroy: true
        });

        // add content and show popup
        this.extension_popup.title(title);
        this.extension_popup.empty();
        this.extension_popup.append(this._templateDescription(description));
        this.extension_popup.show();
    },

    // show/hide ftp popup
    _eventFtp: function() {
        if (!this.ftp.visible) {
            this.ftp.empty();
            var self = this;
            this.ftp.append((new UploadFtp({
                collection      : this.collection,
                ftp_upload_site : this.ftp_upload_site,
                onadd: function(ftp_file) {
                    self.uploadbox.add([{
                        mode: 'ftp',
                        name: ftp_file.path,
                        size: ftp_file.size,
                        path: ftp_file.path
                    }]);
                },
                onremove: function(model_index) {
                    self.collection.remove(model_index);
                }
            })).$el);
            this.ftp.show();
        } else {
            this.ftp.hide();
        }
    },

    // create a new file
    _eventCreate: function (){
        this.uploadbox.add([{
            name    : 'New File',
            size    : 0,
            mode    : 'new'
        }]);
    },

    // start upload process
    _eventStart: function() {
        // check
        if (this.counter.announce == 0 || this.counter.running > 0) {
            return;
        }

        // reset current size
        var self = this;
        this.upload_size = 0;
        this.upload_completed = 0;
        // switch icons for new uploads
        this.collection.each(function(model) {
            if(model.get('status') == 'init') {
                model.set('status', 'queued');
                self.upload_size += model.get('file_size');
            }
        });

        // reset progress
        this.ui_button.set('percentage', 0);
        this.ui_button.set('status', 'success');

        // update running
        this.counter.running = this.counter.announce;

        // set current history id
        this.history_id = this.app.currentHistory();

        // initiate upload procedure in plugin
        this.uploadbox.start();

        // update on screen info
        this._updateScreen();
    },

    // pause upload process
    _eventStop: function() {
        // check
        if (this.counter.running > 0) {
            // show upload has paused
            this.ui_button.set('status', 'info');

            // set html content
            $('#upload-info').html('Queue will pause after completing the current file...');

            // request pause
            this.uploadbox.stop();
        }
    },

    // remove all
    _eventReset: function() {
        // make sure queue is not running
        if (this.counter.running == 0){
            // reset collection
            this.collection.reset();

            // reset counter
            this.counter.reset();

            // remove from queue
            this.uploadbox.reset();

            // reset value for universal type drop-down
            this.select_extension.value(this.options.default_extension);
            this.select_genome.value(this.options.default_genome);

            // reset button
            this.ui_button.set('percentage', 0);

            // show on screen info
            this._updateScreen();
        }
    },

    // update extension for all models
    updateExtension: function(extension, defaults_only) {
        var self = this;
        this.collection.each(function(model) {
            if (model.get('status') == 'init' && (model.get('extension') == self.options.default_extension || !defaults_only)) {
                model.set('extension', extension);
            }
        });
    },

    // update genome for all models
    updateGenome: function(genome, defaults_only) {
        var self = this;
        this.collection.each(function(model) {
            if (model.get('status') == 'init' && (model.get('genome') == self.options.default_genome || !defaults_only)) {
                model.set('genome', genome);
            }
        });
    },

    // set screen
    _updateScreen: function () {
        /*
            update on screen info
        */

        // check default message
        if(this.counter.announce == 0) {
            if (this.uploadbox.compatible()) {
                message = '&nbsp;';
            } else {
                message = 'Browser does not support Drag & Drop. Try Firefox 4+, Chrome 7+, IE 10+, Opera 12+ or Safari 6+.';
            }
        } else {
            if (this.counter.running == 0) {
                message = 'You added ' + this.counter.announce + ' file(s) to the queue. Add more files or click \'Start\' to proceed.';
            } else {
                message = 'Please wait...' + this.counter.announce + ' out of ' + this.counter.running + ' remaining.';
            }
        }

        // set html content
        this.$('#upload-info').html(message);

        /*
            update button status
        */

        // update reset button
        if (this.counter.running == 0 && this.counter.announce + this.counter.success + this.counter.error > 0) {
            this.btnReset.enable();
        } else {
            this.btnReset.disable();
        }

        // update upload button
        if (this.counter.running == 0 && this.counter.announce > 0) {
            this.btnStart.enable();
            this.btnStart.$el.addClass('btn-primary');
        } else {
            this.btnStart.disable();
            this.btnStart.$el.removeClass('btn-primary');
        }

        // pause upload button
        if (this.counter.running > 0) {
            this.btnStop.enable();
        } else {
            this.btnStop.disable();
        }

        // select upload button
        if (this.counter.running == 0) {
            this.btnLocal.enable();
            this.btnFtp.enable();
            this.btnCreate.enable();
        } else {
            this.btnLocal.disable();
            this.btnFtp.disable();
            this.btnCreate.disable();
        }

        // ftp button
        if (this.ftp_upload_site) {
            this.btnFtp.$el.show();
        } else {
            this.btnFtp.$el.hide();
        }

        // table visibility
        if (this.counter.announce + this.counter.success + this.counter.error > 0) {
            this.$('#upload-table').show();
            this.$('.upload-helper').hide();
        } else {
            this.$('#upload-table').hide();
            this.$('.upload-helper').show();
        }
    },

    // calculate percentage of all queued uploads
    _uploadPercentage: function(percentage, size) {
        return (this.upload_completed + (percentage * size)) / this.upload_size;
    },

    // template for extensions description
    _templateDescription: function(options) {
        if (options.description) {
            var tmpl = options.description;
            if (options.description_url) {
                tmpl += '&nbsp;(<a href="' + options.description_url + '" target="_blank">read more</a>)';
            }
            return tmpl;
        } else {
            return 'There is no description available for this file extension.';
        }
    },

    // load html template
    _template: function() {
        return  '<div class="upload-view-default">' +
                    '<div class="upload-top">' +
                        '<h6 id="upload-info" class="upload-info"/>' +
                    '</div>' +
                    '<div id="upload-box" class="upload-box">' +
                        '<div class="upload-helper"><i class="fa fa-files-o"/>Drop files here</div>' +
                        '<table id="upload-table" class="ui-table-striped" style="display: none;">' +
                            '<thead>' +
                                '<tr>' +
                                    '<th>Name</th>' +
                                    '<th>Size</th>' +
                                    '<th>Type</th>' +
                                    '<th>Genome</th>' +
                                    '<th>Settings</th>' +
                                    '<th>Status</th>' +
                                    '<th/>' +
                                '</tr>' +
                            '</thead>' +
                            '<tbody/>' +
                        '</table>' +
                    '</div>' +
                    '<div id="upload-footer" class="upload-footer">' +
                        '<span class="footer-title">Type (set all):</span>' +
                        '<span id="footer-extension"/>' +
                        '<span id="footer-extension-info" class="upload-icon-button fa fa-search"/> ' +
                        '<span class="footer-title">Genome (set all):</span>' +
                        '<span id="footer-genome"/>' +
                    '</div>' +
                    '<div id="upload-buttons" class="upload-buttons"/>' +
                '</div>';
    }
});

});
