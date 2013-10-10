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
        'auto'  : 'Auto-detect',
        'bed'   : 'bed',
        'ab1'   : 'ab1'
    },
    
    // states
    state : {
        init : 'fa-icon-trash',
        success : 'fa-icon-ok',
        error : 'fa-icon-warning-sign'
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
        $(this.el).find('tbody:last').append(this.template_row(id, this.select_extension));
        
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
        
        // read in configuration
        var data = {
            source          : "upload",
            space_to_tabs   : it.find('#space_to_tabs').is(':checked'),
            extension       : it.find('#extension').val()
        }
        
        // configure url
        var current_history = Galaxy.currHistoryPanel.model.get('id');
        this.uploadbox.configure({url : galaxy_config.root + "api/histories/" + current_history + "/contents"});
        
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
        it.find('#percentage').html(percentage + '%');
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
        it.addClass('success');
        
        // update icon
        var sy = it.find('#symbol');
        sy.removeClass('fa-icon-spin');
        sy.removeClass('fa-icon-spinner');
        
        // set status
        sy.addClass(this.state.success);
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
        sy.removeClass('fa-icon-spin');
        sy.removeClass('fa-icon-spinner');
        
        // set status
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
                symbol.removeClass(self.state.init);
                symbol.addClass('fa-icon-spinner');
                symbol.addClass('fa-icon-spin');
            }
        });
        
        // update running
        this.counter.running = this.counter.announce;
        this.update_screen();
        
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
                    'Reset'  : function() {self.event_reset()},
                    'Close'  : function() {self.modal.hide()}
                },
                height : '350'
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
            this.modal.enableButton('Reset');
        else
            this.modal.disableButton('Reset');
            
        // update upload button
        if (this.counter.running == 0 && this.counter.announce > 0)
            this.modal.enableButton('Upload');
        else
            this.modal.disableButton('Upload');
        
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
                                '<th>Space&#8594;Tab</th>' +
                                '<th>Progress</th>' +
                                '<th></th>' +
                            '</tr>' +
                        '</thead>' +
                        '<tbody></tbody>' +
                    '</table>' +
                '</div>' +
                '<h6 id="' + idInfo + '" class="upload-info"></h6>';
    },
    
    template_row: function(id, select_extension)
    {
        // construct template
        var tmpl = '<tr id="' + id.substr(1) + '" class="upload-item">' +
                        '<td><div id="title" class="title"></div></td>' +
                        '<td><div id="size" class="size"></div></td>' +
                        '<td>' +
                            '<select id="extension">';

        // add file types to selection
        for (key in select_extension)
            tmpl +=             '<option value="' + key + '">' + select_extension[key] + '</option>';
            
        tmpl +=             '</select>' +
                        '</td>' +
                        '<td><input id="space_to_tabs" type="checkbox"></input></td>' +
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
