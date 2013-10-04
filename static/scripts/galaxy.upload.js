/*
    galaxy upload
*/

// dependencies
define(["galaxy.modal", "galaxy.master", "utils/galaxy.uploadbox", "libs/backbone/backbone-relational"], function(mod_modal, mod_master) {

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
        ''      : 'Auto-detect',
        'bed'   : 'bed',
        'ab1'   : 'ab1'
    },
    
    // states
    state : {
        init  : 'fa-icon-trash',
        done  : 'fa-icon-caret-down'
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
        
        // add activate icon
        var self = this;
        this.button_show = new mod_master.GalaxyMasterIcon (
        {
            icon        : 'fa-icon-upload',
            tooltip     : 'Upload Files',
            on_click    : function(e) { self.event_show(e) },
            with_number : true
        });
        
        // add to master
        Galaxy.master.prepend(this.button_show);
    },
    
    // events
    events :
    {
        'mouseover'         : 'event_mouseover',
        'mouseleave'        : 'event_mouseleave'
    },
    
    // mouse over
    event_mouseover : function (e)
    {
    },
    
    // mouse left
    event_mouseleave : function (e)
    {
    },
    
    // start
    event_announce : function(index, file, message)
    {
        // make id
        var id = '#upload-' + index;

        // add upload item
        $(this.el).append(this.template_file(id, this.select_extension));
        
        // scroll to bottom
        //$(this.el).scrollTop($(this.el).prop('scrollHeight'));
        
        // access upload item
        var it = this.get_upload_item(index);
        
        // fade in
        it.fadeIn();
        
        // update title
        it.find('.title').html(file.name);
        
        // configure select field
        //it.find('#extension').select2();
        
        // add functionality to remove button
        var self = this;
        it.find('.symbol').on('click', function() { self.event_remove (index) });
    
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
        
        // read in configuration
        var data = {
            source          : "upload",
            space_to_tabs   : it.find('#space_to_tabs').is(':checked'),
            extension       : it.find('#extension').val()
        }
        
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
        
        // update info
        it.find('.info').html(percentage + '% of ' + this.size_to_string (file.size));
    },
    
    // success
    event_success : function(index, file, message)
    {                
        // update galaxy history
        Galaxy.currHistoryPanel.refresh();
        
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
        it.addClass('panel-success');
        it.removeClass('panel-default');
        
        // update icon
        var sy = it.find('.symbol');
        sy.removeClass('fa-icon-spin');
        sy.removeClass('fa-icon-spinner');
        
        // set status
        sy.addClass(this.state.done);
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
        it.addClass('panel-danger');
        it.removeClass('panel-default');
        
        // remove progress bar
        it.find('.progress').remove();
        
        // write error message
        it.find('.error').html('<strong>Failed:</strong> ' + message);
        
        // update icon
        var sy = it.find('.symbol');
        sy.removeClass('fa-icon-spin');
        sy.removeClass('fa-icon-spinner');
        
        // set status
        sy.addClass(this.state.done);
    },
    
    // start upload process
    event_upload : function()
    {
        // check
        if (this.counter.announce == 0 || this.counter.running > 0)
            return;
            
        // switch icons for new uploads
        var self = this;
        $(this.el).find('.symbol').each(function()
        {
            if($(this).hasClass(self.state.init))
            {
                $(this).removeClass(self.state.init);
                $(this).addClass('fa-icon-spinner');
                $(this).addClass('fa-icon-spin');
            }
        });
        
        // hide configuration
        $(this.el).find('.panel-body').hide();
        
        // update running
        this.counter.running = this.counter.announce;
        this.update_screen();
                
        // configure url
        var current_history = Galaxy.currHistoryPanel.model.get('id');
        this.uploadbox.configure({url : galaxy_config.root + "api/histories/" + current_history + "/contents"});
        
        // initiate upload procedure in plugin
        this.uploadbox.upload();
    },
    
    // queue is done
    event_complete: function()
    {
        // update running
        this.counter.running = 0;
        this.update_screen();
    },
    
    // remove all
    event_reset : function()
    {
        // make sure queue is not running
        if (this.counter.running == 0)
        {
            // remove from screen
            var panels = $(this.el).find('.panel');
            panels.fadeOut({complete: function() { panels.remove(); }});
        
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
        var sy = it.find('.symbol');
                
        // only remove from queue if not in processing line
        if (sy.hasClass(this.state.init) || sy.hasClass(this.state.done))
        {
            // reduce counter
            if (it.hasClass('panel-default'))
                this.counter.announce--;
            else if (it.hasClass('panel-success'))
                this.counter.success--;
            else if (it.hasClass('panel-danger'))
                this.counter.error--;
            
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
                body    : this.template('upload-box'),
                buttons : {
                    'Select' : function() {self.uploadbox.select()},
                    'Upload' : function() {self.event_upload()},
                    'Reset'  : function() {self.event_reset()},
                    'Close'  : function() {self.modal.hide()}
                },
                height : '250px'
            });
        
            // set element
            this.setElement('#upload-box');
            
            // file upload
            var self = this;
            this.uploadbox = this.$el.uploadbox(
            {
                dragover        : self.event_mouseover,
                dragleave       : self.event_mouseleave,
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
            this.modal.enable('Reset');
        else
            this.modal.disable('Reset');
            
        // update upload button
        if (this.counter.running == 0 && this.counter.announce > 0)
            this.modal.enable('Upload');
        else
            this.modal.disable('Upload');
        
        // select upload button
        if (this.counter.running == 0)
            this.modal.enable('Select');
        else
            this.modal.disable('Select');
    },

    // load html template
    template: function(id)
    {
        return  '<div id="' + id + '" class="upload-box"></div><h6 id="upload-info" class="upload-info"></h6>';
    },
    
    // load html template
    template_file: function(id, select_extension)
    {
        // start template
        var tmpl =  '<div id="' + id.substr(1) + '" class="panel panel-default">' +
                        '<div class="panel-heading">' +
                            '<h5 class="title"></h5>' +
                            '<h5 class="info"></h5>' +
                            '<div class="symbol ' + this.state.init + '"></div>' +
                        '</div>' +
                        '<div class="panel-body">' +
                            '<div class="menu">' +
                                'Select file type: ' +
                                '<select id="extension">';
        
        // add file types to selection
        for (key in select_extension)
            tmpl +=                 '<option value="' + key + '">' + select_extension[key] + '</option>';

        // continue template
        tmpl +=                 '</select>,&nbsp;' +
                                '<span>Convert space to tabs: <input id="space_to_tabs" type="checkbox"></input></span>' +
                            '</div>' +
                        '</div>' +
                        '<div class="panel-footer">' +
                            '<div class="progress">' +
                                '<div class="progress-bar progress-bar-success"></div>' +
                            '</div>' +
                            '<h6 class="error"></h6>' +
                        '</div>' +
                    '</div>';
        
        // return html string
        return tmpl;
    }
});

// return
return {
    GalaxyUpload: GalaxyUpload
};

});
