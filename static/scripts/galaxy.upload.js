/*
    galaxy upload
*/

// dependencies
define(["galaxy.modal", "galaxy.master", "utils/galaxy.utils", "utils/galaxy.uploadbox", "libs/backbone/backbone-relational"], function(mod_modal, mod_master, mod_util) {

// galaxy upload
var GalaxyUpload = Backbone.View.extend(
{
    // own modal
    modal : null,
    
    // button
    button_show : null,
    
    // upload mod
    uploadbox: null,
    
    // extension types
    select_extension : {
        'auto'  : 'Auto-detect'
    },
    
    // genomes
    select_genome : {
        '?'     : 'Unspecified'
    },
    
    // states
    state : {
        init    : 'fa-icon-trash',
        queued  : 'fa-icon-spinner fa-icon-spin',
        running : '__running__',
        success : 'fa-icon-ok',
        error   : 'fa-icon-warning-sign'
    },
    
    // counter
    counter : {
        // stats
        announce    : 0,
        success     : 0,
        error       : 0,
        running     : 0,
        
        // reset stats
        reset : function()
        {
            this.announce = this.success = this.error = this.running = 0;
        }
    },
    
    // initialize
    initialize : function()
    {
        // wait for galaxy history panel (workaround due to the use of iframes)
        if (!Galaxy.currHistoryPanel)
        {
            var self = this;
            window.setTimeout(function() { self.initialize() }, 500)
            return;
        }
        
        // check if logged in
        if (!Galaxy.currUser.get('id'))
            return;
            
        // add activate icon
        var self = this;
        this.button_show = new mod_master.GalaxyMasterIcon (
        {
            icon        : 'fa-icon-upload',
            tooltip     : 'Upload Files',
            on_click    : function(e) { self.event_show(e) },
            on_unload   : function() {
                if (self.counter.running > 0)
                    return "Currently uploads are running.";
            },
            with_number : true
        });
        
        // add to master
        Galaxy.master.prepend(this.button_show);
        
        // load extension
        var self = this;
        mod_util.jsonFromUrl(galaxy_config.root + "api/datatypes",
            function(datatypes) {
                for (key in datatypes)
                    self.select_extension[datatypes[key]] = datatypes[key];
            });
            
        // load genomes
        mod_util.jsonFromUrl(galaxy_config.root + "api/genomes",
            function(genomes) {
                for (key in genomes)
                    self.select_genome[genomes[key][1]] = genomes[key][0];
            });
    },
    
    // mouse over
    event_dragover : function (e)
    {
    },
    
    // mouse left
    event_dragleave : function (e)
    {
    },
    
    // start
    event_announce : function(index, file, message)
    {
        // make id
        var id = '#upload-' + index;

        // add upload item
        $(this.el).find('tbody:last').append(this.template_row(id));
        
        // scroll to bottom
        //$(this.el).scrollTop($(this.el).prop('scrollHeight'));
        
        // access upload item
        var it = this.get_upload_item(index);
        
        // fade in
        it.fadeIn();
        
        // update title
        it.find('#title').html(file.name);
    
        // update info
        it.find('#size').html(this.size_to_string (file.size));
        
        // add functionality to remove button
        var self = this;
        it.find('#symbol').on('click', function() { self.event_remove (index) });
        
        // initialize progress
        this.event_progress(index, file, 0);
        
        // update counter
        this.counter.announce++;
        
        // update screen
        this.update_screen();
    },
    
    // start
    event_initialize : function(index, file, message)
    {
        // update on screen counter
        this.button_show.number(this.counter.announce);
    
        // get element
        var it = this.get_upload_item(index);

        // update status
        var sy = it.find('#symbol');
        sy.addClass(this.state.running);
      
        // get configuration
        var current_history = Galaxy.currHistoryPanel.model.get('id');
        var file_type = it.find('#extension').val();
        var genome = it.find('#genome').val();
        var space_to_tabs = it.find('#space_to_tabs').is(':checked');
        
        // configure uploadbox
        this.uploadbox.configure({url : galaxy_config.root + "api/tools/", paramname : "files_0|file_data"});
        
        // configure tool
        tool_input = {};
        tool_input['dbkey'] = genome;
        tool_input['file_type'] = file_type;
        tool_input['files_0|NAME'] = file.name;
        tool_input['files_0|type'] = 'upload_dataset';
        tool_input['space_to_tabs'] = space_to_tabs;
        
        // setup data
        data = {};
        data['history_id'] = current_history;
        data['tool_id'] = 'upload1';
        data['inputs'] = JSON.stringify(tool_input);
                
        // return additional data to be send with file
        return data;
    },
    
    // progress
    event_progress : function(index, file, message)
    {
        // get element
        var it = this.get_upload_item(index);
        
        // get value
        var percentage = parseInt(message);
        
        // update progress
        it.find('.progress-bar').css({ width : percentage + '%' });
        
        // update value
        if (percentage != 100)
            it.find('#percentage').html(percentage + '%');
        else
            it.find('#percentage').html('Adding to history...');
    },
    
    // success
    event_success : function(index, file, message)
    {
        // make sure progress is shown correctly
        this.event_progress(index, file, 100);
        
        // update on screen counter
        this.button_show.number('');
        
        // update counter
        this.counter.announce--;
        this.counter.success++;
        
        // update on screen info
        this.update_screen();
        
        // get element
        var it = this.get_upload_item(index);
        
        // update progress frame
        it.addClass('success');
        
        // update text
        it.find('#percentage').html('100%');
        
        // update icon
        var sy = it.find('#symbol');
        sy.removeClass(this.state.running);
        sy.removeClass(this.state.queued);
        sy.addClass(this.state.success);
        
        // update galaxy history
        Galaxy.currHistoryPanel.refresh();
    },
    
    // error
    event_error : function(index, file, message)
    {
        // make sure progress is shown correctly
        this.event_progress(index, file, 0);
        
        // update on screen counter
        this.button_show.number('');
        
        // update counter
        this.counter.announce--;
        this.counter.error++;
        
        // update on screen info
        this.update_screen();
        
        // get element
        var it = this.get_upload_item(index);
        
        // update progress frame
        it.addClass('danger');
        
        // remove progress bar
        it.find('.progress').remove();
        
        // write error message
        it.find('#info').html('<strong>Failed: </strong>' + message).show();
        
        // update icon
        var sy = it.find('#symbol');
        sy.removeClass(this.state.running);
        sy.removeClass(this.state.queued);
        sy.addClass(this.state.error);
    },
    
    // start upload process
    event_upload : function()
    {
        // check
        if (this.counter.announce == 0 || this.counter.running > 0)
            return;
            
        // switch icons for new uploads
        var items = $(this.el).find('.upload-item');
        var self = this;
        items.each(function()
        {
            var symbol = $(this).find('#symbol');
            if(symbol.hasClass(self.state.init))
            {
                // set status
                symbol.removeClass(self.state.init);
                symbol.addClass(self.state.queued);
            
                // disable options
                $(this).find('#genome').attr('disabled', true);
                $(this).find('#extension').attr('disabled', true);
                $(this).find('#space_to_tabs').attr('disabled', true);
            }
        });
        
        // update running
        this.counter.running = this.counter.announce;
        this.update_screen();
        
        // initiate upload procedure in plugin
        this.uploadbox.upload();
    },
    
    // pause upload process
    event_pause : function()
    {
        // check
        if (this.counter.running == 0)
            return;
                            
        // request pause
        this.uploadbox.pause();
        
        // set html content
        $('#upload-info').html('Queueing will pause after completing the current file...');
    },
    
    // queue is done
    event_complete: function()
    {
        // update running
        this.counter.running = 0;
        this.update_screen();
        
        // switch icons for new uploads
        var items = $(this.el).find('.upload-item');
        var self = this;
        items.each(function()
        {
            var symbol = $(this).find('#symbol');
            if(symbol.hasClass(self.state.queued) && !symbol.hasClass(self.state.running))
            {
                // update status
                symbol.removeClass(self.state.queued);
                symbol.addClass(self.state.init);
                
                // disable options
                $(this).find('#genome').attr('disabled', false);
                $(this).find('#extension').attr('disabled', false);
                $(this).find('#space_to_tabs').attr('disabled', false);
            }
        });
    },
    
    // remove all
    event_reset : function()
    {
        // make sure queue is not running
        if (this.counter.running == 0)
        {
            // remove from screen
            var items = $(this.el).find('.upload-item');
            $(this.el).find('table').fadeOut({ complete : function() { items.remove(); }});
            
            // reset counter
            this.counter.reset();
        
            // show on screen info
            this.update_screen();
            
            // remove from queue
            this.uploadbox.reset();
        }
    },
    
    // remove item from upload list
    event_remove : function(index)
    {
        // get item
        var it = this.get_upload_item(index);
        var sy = it.find('#symbol');
                
        // only remove from queue if not in processing line
        if (sy.hasClass(this.state.init) || sy.hasClass(this.state.success) || sy.hasClass(this.state.error))
        {
            // reduce counter
            if (it.hasClass('success'))
                this.counter.success--;
            else if (it.hasClass('danger'))
                this.counter.error--;
            else
                this.counter.announce--;
            
            // show on screen info
            this.update_screen();
                
            // remove from queue
            this.uploadbox.remove(index);
            
            // remove element
            it.remove();
        }
    },
    
    // show/hide upload frame
    event_show : function (e)
    {
        // prevent default
        e.preventDefault();
        
        // create modal
        if (!this.modal)
        {
            // make modal
            var self = this;
            this.modal = new mod_modal.GalaxyModal(
            {
                title   : 'Upload files from your local drive',
                body    : this.template('upload-box', 'upload-info'),
                buttons : {
                    'Select' : function() {self.uploadbox.select()},
                    'Upload' : function() {self.event_upload()},
                    'Pause'  : function() {self.event_pause()},
                    'Reset'  : function() {self.event_reset()},
                    'Close'  : function() {self.modal.hide()}
                },
                height      : '350',
                width       : '850'
            });
        
            // set element
            this.setElement('#upload-box');
            
            // file upload
            var self = this;
            this.uploadbox = this.$el.uploadbox(
            {
                dragover        : function() { self.event_dragover() },
                dragleave       : function() { self.event_dragleave() },
                announce        : function(index, file, message) { self.event_announce(index, file, message) },
                initialize      : function(index, file, message) { return self.event_initialize(index, file, message) },
                success         : function(index, file, message) { self.event_success(index, file, message) },
                progress        : function(index, file, message) { self.event_progress(index, file, message) },
                error           : function(index, file, message) { self.event_error(index, file, message) },
                complete        : function() { self.event_complete() },
            });
            
            // setup info
            this.update_screen();
        }
        
        // show modal
        this.modal.show();
    },

    // get upload item
    get_upload_item: function(index)
    {
        // get element
        return $(this.el).find('#upload-' + index);
    },

    // to string
    size_to_string : function (size)
    {
        // identify unit
        var unit = "";
        if (size >= 100000000000)   { size = size / 100000000000; unit = "TB"; } else
        if (size >= 100000000)      { size = size / 100000000; unit = "GB"; } else
        if (size >= 100000)         { size = size / 100000; unit = "MB"; } else
        if (size >= 100)            { size = size / 100; unit = "KB"; } else
                                    { size = size * 10; unit = "b"; }
        // return formatted string
        return "<strong>" + (Math.round(size) / 10) + "</strong> " + unit;
    },

    // set screen
    update_screen: function ()
    {
        /*
            update on screen info
        */
        
        // check default message
        if(this.counter.announce == 0)
        {
            if (this.uploadbox.compatible)
                message = 'Drag&drop files into this box or click \'Select\' to select files!';
            else
                message = 'Unfortunately, your browser does not support multiple file uploads or drag&drop.<br>Please upgrade to i.e. Firefox 4+, Chrome 7+, IE 10+, Opera 12+ or Safari 6+.'
        } else {
            if (this.counter.running == 0)
                message = 'You added ' + this.counter.announce + ' file(s) to the queue. Add more files or click \'Upload\' to proceed.';
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
            this.modal.enableButton('Upload');
        else
            this.modal.disableButton('Upload');

        // pause upload button
        if (this.counter.running > 0)
            this.modal.enableButton('Pause');
        else
            this.modal.disableButton('Pause');
        
        // select upload button
        if (this.counter.running == 0)
            this.modal.enableButton('Select');
        else
            this.modal.disableButton('Select');
            
        // table visibility
        if (this.counter.announce + this.counter.success + this.counter.error > 0)
            $(this.el).find('table').show();
        else
            $(this.el).find('table').hide();
    },

    // load html template
    template: function(id, idInfo)
    {
        return  '<div id="' + id + '" class="upload-box">' +
                    '<table class="table table-striped" style="display: none;">' +
                        '<thead>' +
                            '<tr>' +
                                '<th>Name</th>' +
                                '<th>Size</th>' +
                                '<th>Type</th>' +
                                '<th>Genome</th>' +
                                '<th>Space&#8594;Tab</th>' +
                                '<th>Status</th>' +
                                '<th></th>' +
                            '</tr>' +
                        '</thead>' +
                        '<tbody></tbody>' +
                    '</table>' +
                '</div>' +
                '<h6 id="' + idInfo + '" class="upload-info"></h6>';
    },
    
    template_row: function(id)
    {
        // construct template
        var tmpl = '<tr id="' + id.substr(1) + '" class="upload-item">' +
                        '<td><div id="title" class="title"></div></td>' +
                        '<td><div id="size" class="size"></div></td>';

        // add file type selectore
        tmpl +=         '<td>' +
                            '<select id="extension" class="extension">';
        for (key in this.select_extension)
            tmpl +=             '<option value="' + key + '">' + this.select_extension[key] + '</option>';
        tmpl +=             '</select>' +
                        '</td>';                        

        // add genome selector
        tmpl +=         '<td>' +
                            '<select id="genome" class="genome">';
        for (key in this.select_genome)
            tmpl +=             '<option value="' + key + '">' + this.select_genome[key] + '</option>';
        tmpl +=             '</select>' +
                        '</td>';
        
        // add next row
        tmpl +=         '<td><input id="space_to_tabs" type="checkbox"></input></td>' +
                        '<td>' +
                            '<div id="info" class="info">' +
                                '<div class="progress">' +
                                    '<div class="progress-bar progress-bar-success"></div>' +
                                    '<div id="percentage" class="percentage">0%</div>' +
                                '</div>' +
                            '</div>' +
                        '</td>' +
                        '<td><div id="symbol" class="symbol ' + this.state.init + '"></div></td>' +
                    '</tr>';
        
        // return html string
        return tmpl;
    }
});

// return
return {
    GalaxyUpload: GalaxyUpload
};

});
