// dependencies
define(["galaxy.modal",
        "utils/utils",
        "mvc/upload/upload-button",
        "mvc/upload/upload-model",
        "mvc/upload/upload-row",
        "mvc/upload/upload-ftp",
        "mvc/ui.popover",
        "mvc/ui",
        "utils/uploadbox"],
       
        function(   Modal,
                    Utils,
                    UploadButton,
                    UploadModel,
                    UploadItem,
                    UploadFtp,
                    Popover
                ) {

// galaxy upload
return Backbone.View.extend(
{
    // options
    options : {
        nginx_upload_path : ''
    },
    
    // own modal
    modal : null,
    
    // button
    ui_button : null,
    
    // jquery uploadbox plugin
    uploadbox: null,
    
    // current history
    current_history: null,
    
    // current upload size
    upload_size: 0,
    
    // extension types
    select_extension :[['Auto-detect', 'auto']],
    
    // genomes
    select_genome : [['Unspecified (?)', '?']],
    
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
    initialize : function(options) {
        // link this
        var self = this;
            
        // wait for galaxy history panel (workaround due to the use of iframes)
        if (!Galaxy.currHistoryPanel || !Galaxy.currHistoryPanel.model) {
            window.setTimeout(function() { self.initialize() }, 500)
            return;
        }
        
        // check if logged in
        if (!Galaxy.currUser.get('id')) {
            return;
        }
            
        // create model
        this.ui_button = new UploadButton.Model({
            icon        : 'fa-upload',
            tooltip     : 'Download from URL or upload files from disk',
            label       : 'Load Data',
            onclick     : function(e) {
                if (e) {
                    self._eventShow(e)
                }
            },
            onunload    : function() {
                if (self.counter.running > 0) {
                    return "Several uploads are still processing.";
                }
            }
        });
        
        // define location
        $('#left .unified-panel-header-inner').append((new UploadButton.View(this.ui_button)).$el);
        
        // load extension
        var self = this;
        Utils.jsonFromUrl(galaxy_config.root + "api/datatypes?upload_only=True",
            function(datatypes) {
                for (key in datatypes)
                    self.select_extension.push([datatypes[key], datatypes[key]]);
            });
            
        // load genomes
        Utils.jsonFromUrl(galaxy_config.root + "api/genomes",
            function(genomes) {
                // backup default
                var def = self.select_genome[0];
                
                // fill array
                self.select_genome = [];
                for (key in genomes)
                    if (genomes[key].length > 1)
                        if (genomes[key][1] !== def[1])
                            self.select_genome.push(genomes[key]);
                
                // sort
                self.select_genome.sort(function(a, b) {
                    return a[0] > b[0] ? 1 : a[0] < b[0] ? -1 : 0;
                });

                // insert default back to array
                self.select_genome.unshift(def);
            });
        
        // read in options
        if (options) {
            this.options = _.defaults(options, this.options);
        }
        
        // events
        this.collection.on('remove', function(item) {
            self._eventRemove(item);
        });
        this.collection.on('change:genome', function(item) {
            var genome = item.get('genome');
            self.collection.each(function(item) {
                if (item.get('status') == 'init' && item.get('genome') == '?') {
                    item.set('genome', genome);
                }
            });
        });
    },
    
    //
    // event triggered by upload button
    //
    
    // show/hide upload frame
    _eventShow : function (e) {
        // prevent default
        e.preventDefault();
        
        // create modal
        if (!this.modal) {
            // make modal
            var self = this;
            this.modal = new Modal.GalaxyModal({
                title   : 'Download data directly from web or upload files from your disk',
                body    : this._template('upload-box', 'upload-info'),
                buttons : {
                    'Choose local file' : function() {self.uploadbox.select()},
                    'Choose FTP file'   : function() {self._eventFtp()},
                    'Create new file'   : function() {self._eventCreate()},
                    'Start'             : function() {self._eventStart()},
                    'Pause'             : function() {self._eventStop()},
                    'Reset'             : function() {self._eventReset()},
                    'Close'             : function() {self.modal.hide()},
                },
                height              : '400',
                width               : '900',
                closing_events      : true
            });
        
            // set element
            this.setElement('#upload-box');
            
            // file upload
            var self = this;
            this.uploadbox = this.$el.uploadbox({
                announce        : function(index, file, message) { self._eventAnnounce(index, file, message) },
                initialize      : function(index, file, message) { return self._eventInitialize(index, file, message) },
                progress        : function(index, file, message) { self._eventProgress(index, file, message) },
                success         : function(index, file, message) { self._eventSuccess(index, file, message) },
                error           : function(index, file, message) { self._eventError(index, file, message) },
                complete        : function() { self._eventComplete() }
            });
            
            // setup info
            this._updateScreen();
            
            // add ftp file viewer
            if (this.options.ftp_upload_dir && this.options.ftp_upload_site) {
                var button = this.modal.getButton('Choose FTP file');
                this.ftp = new Popover.View({
                    title       : 'FTP files',
                    container   : button
                });
            } else {
                this.modal.hideButton('Choose FTP file');
            }
        }
        
        // show modal
        this.modal.show();
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
    _eventAnnounce : function(index, file, message) {
        // update counter
        this.counter.announce++;
        
        // update screen
        this._updateScreen();
        
        // create view/model
        var upload_item = new UploadItem(this, {
            id          : index,
            file_name   : file.name,
            file_size   : file.size,
            file_mode   : file.mode,
            file_path   : file.path
        });
        
        // add to collection
        this.collection.add(upload_item.model);
        
        // add upload item element to table
        $(this.el).find('tbody:first').append(upload_item.$el);
        
        // render
        upload_item.render();
    },
    
    // the uploadbox plugin is initializing the upload for this file
    _eventInitialize : function(index, file, message) {
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
        var space_to_tabs   = it.get('space_to_tabs');
        var to_posix_lines  = it.get('to_posix_lines');
        
        // validate
        if (!url_paste && !(file.size > 0))
            return null;
            
        // configure uploadbox
        this.uploadbox.configure({url : this.options.nginx_upload_path});
        
        // configure tool
        tool_input = {};
        
        // local files
        if (file_mode == 'local') {
            this.uploadbox.configure({paramname : 'files_0|file_data'});
        } else {
            this.uploadbox.configure({paramname : null});
        }
        
        // new files
        if (file_mode == 'new') {
            tool_input['files_0|url_paste'] = url_paste;
        }
        
        // files from ftp
        if (file_mode == 'ftp') {
            // add to tool configuration
            tool_input['files_0|ftp_files'] = file_path;
        }
        
        // add common configuration
        tool_input['dbkey'] = genome;
        tool_input['file_type'] = extension;
        tool_input['files_0|type'] = 'upload_dataset';
        tool_input['space_to_tabs'] = space_to_tabs;
        tool_input['to_posix_lines'] = to_posix_lines;
        
        // setup data
        data = {};
        data['history_id'] = this.current_history;
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
        this.ui_button.set('percentage', this._upload_percentage(percentage, file.size));
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
        this.ui_button.set('percentage', this._upload_percentage(100, file_size));
        
        // update completed
        this.upload_completed += file_size * 100;
        
        // update counter
        this.counter.announce--;
        this.counter.success++;
        
        // update on screen info
        this._updateScreen();
        
        // update galaxy history
        Galaxy.currHistoryPanel.refreshHdas();
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
        this.ui_button.set('percentage', this._upload_percentage(100, file.size));
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
    _eventCreate : function ()
    {
        this.uploadbox.add([{
            name    : 'New File',
            size    : 0,
            mode    : 'new'
        }]);
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
        
        // backup current history
        this.current_history = Galaxy.currHistoryPanel.model.get('id');
        
        // update running
        this.counter.running = this.counter.announce;
        this._updateScreen();
        
        // initiate upload procedure in plugin
        this.uploadbox.start();
    },
    
    // pause upload process
    _eventStop : function() {
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
    _eventReset : function() {
        // make sure queue is not running
        if (this.counter.running == 0)
        {
            // reset collection
            this.collection.reset();
            
            // reset counter
            this.counter.reset();
        
            // show on screen info
            this._updateScreen();
            
            // remove from queue
            this.uploadbox.reset();
            
            // reset button
            this.ui_button.set('percentage', 0);
        }
    },
    
    // set screen
    _updateScreen: function () {
        /*
            update on screen info
        */
        
        // check default message
        if(this.counter.announce == 0)
        {
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
        $('#upload-info').html(message);
        
        /*
            update button status
        */
        
        // update reset button
        if (this.counter.running == 0 && this.counter.announce + this.counter.success + this.counter.error > 0)
            this.modal.enableButton('Reset');
        else
            this.modal.disableButton('Reset');
            
        // update upload button
        if (this.counter.running == 0 && this.counter.announce > 0)
            this.modal.enableButton('Start');
        else
            this.modal.disableButton('Start');

        // pause upload button
        if (this.counter.running > 0)
            this.modal.enableButton('Pause');
        else
            this.modal.disableButton('Pause');
        
        // select upload button
        if (this.counter.running == 0)
        {
            this.modal.enableButton('Choose local file');
            this.modal.enableButton('Choose FTP file');
            this.modal.enableButton('Create new file');
        } else {
            this.modal.disableButton('Choose local file');
            this.modal.disableButton('Choose FTP file');
            this.modal.disableButton('Create new file');
        }
        
        // table visibility
        if (this.counter.announce + this.counter.success + this.counter.error > 0)
            $(this.el).find('#upload-table').show();
        else
            $(this.el).find('#upload-table').hide();
    },

    // calculate percentage of all queued uploads
    _upload_percentage: function(percentage, size) {
        return (this.upload_completed + (percentage * size)) / this.upload_size;
    },

    // load html template
    _template: function(id, idInfo) {
        return  '<div id="' + id + '" class="upload-box">' +
                    '<table id="upload-table" class="table table-striped" style="display: none;">' +
                        '<thead>' +
                            '<tr>' +
                                '<th>Name</th>' +
                                '<th>Size</th>' +
                                '<th>Type</th>' +
                                '<th>Genome</th>' +
                                '<th>Settings</th>' +
                                '<th>Status</th>' +
                                '<th></th>' +
                            '</tr>' +
                        '</thead>' +
                        '<tbody></tbody>' +
                    '</table>' +
                '</div>' +
                '<h6 id="' + idInfo + '" class="upload-info"></h6>';
    }
});

});
