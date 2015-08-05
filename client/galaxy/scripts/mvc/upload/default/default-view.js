/** Renders contents of the default upload viewer */
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
                    UploadItem,
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

    // current upload size
    upload_size: 0,

    // collection
    collection : new UploadModel.Collection(),

    // ftp file viewer
    ftp : null,

    // counter
    counter : {
        // stats
        announce    : 0,
        success     : 0,
        error       : 0,
        running     : 0,

        // reset stats
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

        // link this
        var self = this;

        // set element
        this.setElement(this._template());

        // create button section
        this.btnLocal    = new Ui.Button({ title: 'Choose local file',   onclick: function() { self.uploadbox.select(); } });
        this.btnFtp      = new Ui.Button({ title: 'Choose FTP file',     onclick: function() { self._eventFtp(); } });
        this.btnCreate   = new Ui.Button({ title: 'Paste/Fetch data',    onclick: function() { self._eventCreate(); } });
        this.btnStart    = new Ui.Button({ title: 'Start',               onclick: function() { self._eventStart(); } });
        this.btnStop     = new Ui.Button({ title: 'Pause',               onclick: function() { self._eventStop(); } });
        this.btnReset    = new Ui.Button({ title: 'Reset',               onclick: function() { self._eventReset(); } });
        this.btnClose    = new Ui.Button({ title: 'Close',               onclick: function() { self.app.modal.hide(); } });

        // append buttons to dom
        var buttons = [ this.btnLocal, this.btnFtp, this.btnCreate, this.btnStart, this.btnStop, this.btnReset, this.btnClose ];
        for (var i in buttons) {
            this.$('#upload-buttons').prepend(buttons[i].$el);
        }

        // file upload
        var self = this;
        this.uploadbox = this.$('#upload-box').uploadbox({
            url             : this.app.options.nginx_upload_path,
            announce        : function(d) { self._eventAnnounce(d) },
            initialize      : function(d) { return self._eventInitialize(d) },
            progress        : function(d, percentage) { self._eventProgress(d, percentage) },
            success         : function(d, message) { self._eventSuccess(d, message) },
            error           : function(d, message) { self._eventError(d, message) },
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

        // setup info
        this._updateScreen();

        // events
        this.collection.on('remove', function(item) {
            self._eventRemove(item);
        });
    },

    //
    // events triggered by collection
    //

    // remove item from upload list
    _eventRemove : function(item) {
        // update status
        var status = item.get('status');

        // reduce counter
        if (status == 'success') {
            this.counter.success--;
        } else if (status == 'error') {
            this.counter.error--;
        } else {
            this.counter.announce--;
        }

        // show on screen info
        this._updateScreen();

        // remove from queue
        this.uploadbox.remove(item.id);
    },

    //
    // events triggered by the upload box plugin
    //

    // a new file has been dropped/selected through the uploadbox plugin
    _eventAnnounce: function(d) {
        // update counter
        this.counter.announce++;

        // update screen
        this._updateScreen();

        // create view/model
        var upload_item = new UploadItem(this, {
            id          : d.index,
            file_name   : d.file.name,
            file_size   : d.file.size,
            file_mode   : d.file.mode || 'local',
            file_path   : d.file.path
        });

        // add to collection
        this.collection.add(upload_item.model);

        // add upload item element to table
        this.$('#upload-table > tbody:first').append(upload_item.$el);

        // render
        upload_item.render();
    },

    // the uploadbox plugin is initializing the upload for this file
    _eventInitialize: function(d) {
        // get element
        var it = this.collection.get(d.index);

        // update status
        it.set('status', 'running');

        // get configuration
        var file_name       = it.get('file_name');
        var file_path       = it.get('file_path');
        var file_mode       = it.get('file_mode');
        var extension       = it.get('extension');
        var genome          = it.get('genome');
        var url_paste       = it.get('url_paste');
        var space_to_tab    = it.get('space_to_tab');
        var to_posix_lines  = it.get('to_posix_lines');

        // validate
        if (!url_paste && !(d.file.size > 0)) {
            return { error: 'No upload content available.' };
        }

        // configure tool input
        inputs = {};
        inputs['dbkey'] = genome;
        inputs['file_type'] = extension;
        inputs['files_0|type'] = 'upload_dataset';
        inputs['files_0|space_to_tab'] = space_to_tab && 'Yes' || null;
        inputs['files_0|to_posix_lines'] = to_posix_lines && 'Yes' || null;

        // modes without upload data
        if (file_mode == 'new') {
            inputs['files_0|url_paste'] = url_paste;
        }
        if (file_mode == 'ftp') {
            inputs['files_0|ftp_files'] = file_path;
        }

        // setup/return submission data
        var data = {
            payload: {
                'tool_id'       : 'upload1',
                'history_id'    : this.app.current_history,
                'inputs'        : JSON.stringify(inputs),
            }
        }
        if (file_mode == 'local') {
            data['files'] = [{ name: 'files_0|file_data', file: d.file }];
        }
        return data;
    },

    // progress
    _eventProgress: function(d, percentage) {
        // set progress for row
        var it = this.collection.get(d.index);
        it.set('percentage', percentage);

        // update ui button
        this.ui_button.set('percentage', this._uploadPercentage(percentage, d.file.size));
    },

    // success
    _eventSuccess: function(d, message) {
        // update status
        var it = this.collection.get(d.index);
        it.set('percentage', 100);
        it.set('status', 'success');

        // file size
        var file_size = it.get('file_size');

        // update ui button
        this.ui_button.set('percentage', this._uploadPercentage(100, file_size));

        // update completed
        this.upload_completed += file_size * 100;

        // update counter
        this.counter.announce--;
        this.counter.success++;

        // update on screen info
        this._updateScreen();

        // update galaxy history
        Galaxy.currHistoryPanel.refreshContents();
    },

    // error
    _eventError: function(d, message) {
        // get element
        var it = this.collection.get(d.index);

        // update status
        it.set('percentage', 100);
        it.set('status', 'error');
        it.set('info', message);

        // update ui button
        this.ui_button.set('percentage', this._uploadPercentage(100, d.file.size));
        this.ui_button.set('status', 'danger');

        // update completed
        this.upload_completed += d.file.size * 100;

        // update counter
        this.counter.announce--;
        this.counter.error++;

        // update on screen info
        this._updateScreen();
    },

    // queue is done
    _eventComplete: function() {
        // reset queued upload to initial status
        this.collection.each(function(item) {
            if(item.get('status') == 'queued') {
                item.set('status', 'init');
            }
        });

        // update running
        this.counter.running = 0;
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

    _eventFtp: function() {
        // check if popover is visible
        if (!this.ftp.visible) {
            // show popover
            this.ftp.empty();
            this.ftp.append((new UploadFtp(this)).$el);
            this.ftp.show();
        } else {
            // hide popover
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
        this.collection.each(function(item) {
            if(item.get('status') == 'init') {
                item.set('status', 'queued');
                self.upload_size += item.get('file_size');
            }
        });

        // reset progress
        this.ui_button.set('percentage', 0);
        this.ui_button.set('status', 'success');

        // update running
        this.counter.running = this.counter.announce;
        this._updateScreen();

        // initiate upload procedure in plugin
        this.uploadbox.start();
    },

    // pause upload process
    _eventStop: function() {
        // check
        if (this.counter.running == 0) {
            return;
        }

        // show upload has paused
        this.ui_button.set('status', 'info');

        // request pause
        this.uploadbox.stop();

        // set html content
        $('#upload-info').html('Queue will pause after completing the current file...');
    },

    // remove all
    _eventReset: function() {
        // make sure queue is not running
        if (this.counter.running == 0){
            // reset collection
            this.collection.reset();

            // reset counter
            this.counter.reset();

            // show on screen info
            this._updateScreen();

            // remove from queue
            this.uploadbox.reset();

            // reset value for universal type drop-down
            this.select_extension.value(this.options.default_extension);
            this.select_genome.value(this.options.default_genome);

            // reset button
            this.ui_button.set('percentage', 0);
        }
    },

    // update extension for all models
    updateExtension: function(extension, defaults_only) {
        var self = this;
        this.collection.each(function(item) {
            if (item.get('status') == 'init' && (item.get('extension') == self.options.default_extension || !defaults_only)) {
                item.set('extension', extension);
            }
        });
    },

    // update genome for all models
    updateGenome: function(genome, defaults_only) {
        var self = this;
        this.collection.each(function(item) {
            if (item.get('status') == 'init' && (item.get('genome') == self.options.default_genome || !defaults_only)) {
                item.set('genome', genome);
            }
        });
    },

    // set screen
    _updateScreen: function () {
        /*
            update on screen info
        */

        // check default message
        if(this.counter.announce == 0){
            if (this.uploadbox.compatible())
                message = 'You can Drag & Drop files into this box.';
            else
                message = 'Unfortunately, your browser does not support multiple file uploads or drag&drop.<br>Some supported browsers are: Firefox 4+, Chrome 7+, IE 10+, Opera 12+ or Safari 6+.'
        } else {
            if (this.counter.running == 0)
                message = 'You added ' + this.counter.announce + ' file(s) to the queue. Add more files or click \'Start\' to proceed.';
            else
                message = 'Please wait...' + this.counter.announce + ' out of ' + this.counter.running + ' remaining.';
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
        } else {
            this.btnStart.disable();
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
        if (this.app.current_user && this.options.ftp_upload_dir && this.options.ftp_upload_site) {
            this.btnFtp.$el.show();
        } else {
            this.btnFtp.$el.hide();
        }

        // table visibility
        if (this.counter.announce + this.counter.success + this.counter.error > 0) {
            this.$('#upload-table').show();
        } else {
            this.$('#upload-table').hide();
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
