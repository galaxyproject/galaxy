/** Renders contents of the default upload viewer */
define(['utils/utils',
        'mvc/upload/upload-model',
        'mvc/upload/composite/composite-row',
        'mvc/ui/ui-popover',
        'mvc/ui/ui-select',
        'mvc/ui/ui-misc'],

        function(   Utils,
                    UploadModel,
                    UploadItem,
                    Popover,
                    Select,
                    Ui
                ) {

return Backbone.View.extend({
    // extension selector
    select_extension : null,

    // genome selector
    select_genome: null,

    // collection
    collection : new UploadModel.Collection(),

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
        this.btnStart = new Ui.Button({ title: 'Start', onclick: function() { self._eventStart(); } });
        this.btnClose = new Ui.Button({ title: 'Close', onclick: function() { self.app.modal.hide(); } });

        // append buttons to dom
        var buttons = [ this.btnStart, this.btnClose ];
        for (var i in buttons) {
            this.$('#upload-buttons').prepend(buttons[i].$el);
        }

        // select extension
        this.select_extension = new Select.View({
            css         : 'footer-selection',
            container   : this.$('#footer-extension'),
            data        : _.filter(this.list_extensions, function(ext) { return ext.composite_files }),
            onchange    : function(extension) {
                // reset current collection
                self.collection.reset();

                // add new models
                var details = _.findWhere(self.list_extensions, { id: extension });
                if (details && details.composite_files) {
                    self.collection.add(details.composite_files);
                }
            }
        });

        // handle extension info popover
        this.$('#footer-extension-info').on('click', function(e) {
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
            value       : this.options.default_genome
        });

        // listener for collection triggers on change in composite datatype
        this.collection.on('add', function (item) {
            self._eventAnnounce(item);
        });

        this.collection.on('reset', function() {
            //self._eventReset();
        });

        // trigger initial onchange event
        this.select_extension.options.onchange(this.select_extension.value());

        // enable/disable buttons, update messages
        this._updateScreen();
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

    // builds the basic ui with placeholder rows for each composite data type file
    _eventAnnounce: function(item) {
        // create view/model
        console.log(item);
        var upload_item = new UploadItem(this, {
            id          : this.collection.size(),
            file_name   : item.get('description') || item.get('name') || 'Unavailable',
            //file_size   : file.size,
            //file_mode   : file.mode,
            //file_path   : file.path
        });

        // add upload item element to table
        this.$('#upload-table > tbody:first').append(upload_item.$el);

        // render
        upload_item.render();

        // table visibility
        if (this.collection.size() > 0) {
            this.$('#upload-table').show();
        } else {
            this.$('#upload-table').hide();
        }
    },

    // the uploadbox plugin is initializing the upload for this file
    _eventInitialize : function(index, file, message) {
        return;//
        // get element
        var it = this.collection.get(index);

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
        if (!url_paste && !(file.size > 0))
            return null;

        // configure uploadbox
        this.uploadbox.configure({url : this.app.options.nginx_upload_path});

        // local files
        if (file_mode == 'local') {
            this.uploadbox.configure({paramname : 'files_0|file_data'});
        } else {
            this.uploadbox.configure({paramname : null});
        }

        // configure tool
        tool_input = {};

        // new files
        if (file_mode == 'new') {
            tool_input['files_0|url_paste'] = url_paste;
        }

        // files from ftp
        if (file_mode == 'ftp') {
            tool_input['files_0|ftp_files'] = file_path;
        }

        // add common configuration
        tool_input['dbkey'] = genome;
        tool_input['file_type'] = extension;
        tool_input['files_0|type'] = 'upload_dataset';
        tool_input['files_0|space_to_tab'] = space_to_tabs && 'Yes' || null;
        tool_input['files_0|to_posix_lines'] = to_posix_lines && 'Yes' || null;

        // setup data
        data = {};
        data['history_id'] = this.app.current_history;
        data['tool_id'] = 'upload1';
        data['inputs'] = JSON.stringify(tool_input);

        // return additional data to be send with file
        return data;
    },

    // progress
    _eventProgress : function(index, file, percentage) {
        // set progress for row
        var it = this.collection.get(index);
        it.set('percentage', percentage);

        // update ui button
        this.ui_button.set('percentage', this._uploadPercentage(percentage, file.size));
    },

    // success
    _eventSuccess : function(index, file, message) {
        // update status
        var it = this.collection.get(index);
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
    _eventError : function(index, file, message) {
        // get element
        var it = this.collection.get(index);

        // update status
        it.set('percentage', 100);
        it.set('status', 'error');
        it.set('info', message);

        // update ui button
        this.ui_button.set('percentage', this._uploadPercentage(100, file.size));
        this.ui_button.set('status', 'danger');

        // update completed
        this.upload_completed += file.size * 100;

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
    showExtensionInfo : function(options) {
        // initialize
        var self = this;
        var $el = options.$el;
        var extension = options.extension;
        var title = options.title;
        var description = _.findWhere(this.list_extensions, {'id': extension});

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

    // start upload process
    _eventStart : function() {
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
        this._updateScreen();

        // initiate upload procedure in plugin
        this.uploadbox.start();
    },

    // remove all
    _eventReset : function() {
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
        //if (this.active) {
        var message = 'Please select a composite datatype and specify its components.';
        /*} else {
                message = 'Unfortunately, your browser does not support multiple file uploads or drag&drop.<br>Some supported browsers are: Firefox 4+, Chrome 7+, IE 10+, Opera 12+ or Safari 6+.'
        } else {
            if (this.counter.running == 0)
                message = 'You added ' + this.counter.announce + ' file(s) to the queue. Add more files or click \'Start\' to proceed.';
            else
                message = 'Please wait...' + this.counter.announce + ' out of ' + this.counter.running + ' remaining.';
        }*/

        // set html content
        this.$('#upload-info').html(message);

        /*/ update upload button
        if (this.counter.running == 0 && this.counter.announce > 0) {
            this.btnStart.enable();
        } else {
            this.btnStart.disable();
        }*/

        // table visibility
        if (this.collection.size() > 0) {
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
        return  '<div class="upload-view-composite">' +
                    '<div class="upload-top">' +
                        '<h6 id="upload-info" class="upload-info"></h6>' +
                    '</div>' +
                    '<div id="upload-footer" class="upload-footer">' +
                        '<span class="footer-title">Composite Type:</span>' +
                        '<span id="footer-extension"/>' +
                        '<span id="footer-extension-info" class="upload-icon-button fa fa-search"/> ' +
                        '<span class="footer-title">Genome/Build:</span>' +
                        '<span id="footer-genome"/>' +
                    '</div>' +
                    '<div id="upload-box" class="upload-box">' +
                        '<table id="upload-table" class="table table-striped" style="display: none;">' +
                            '<thead>' +
                                '<tr>' +
                                    '<th>Source</th>' +
                                    '<th>Description</th>' +
                                    '<th>Size</th>' +
                                    '<th>Settings</th>' +
                                    '<th>Status</th>' +
                                '</tr>' +
                            '</thead>' +
                            '<tbody></tbody>' +
                        '</table>' +
                    '</div>' +
                    '<div id="upload-buttons" class="upload-buttons"/>' +
                '</div>';
    }
});

});
