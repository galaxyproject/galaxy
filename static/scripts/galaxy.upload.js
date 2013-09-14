/*
    galaxy upload v1.0
*/

// dependencies
define(["galaxy.modal", "galaxy.master", "utils/galaxy.uploadbox", "libs/backbone/backbone-relational"], function(mod_modal, mod_master) {

// galaxy upload
var GalaxyUpload = Backbone.View.extend(
{
    // own modal
    modal   : null,
    
    // button
    button_show : null,
    
    // file counter
    file_counter: 0,
    
    // initialize
    initialize : function()
    {
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
        'mouseover'      : 'event_mouseover',
        'mouseleave'     : 'event_mouseleave'
    },
    
    // mouse over
    event_mouseover : function (e)
    {
        $('#galaxy-upload-box').addClass('highlight');
    },
    
    // mouse left
    event_mouseleave : function (e)
    {
        $('#galaxy-upload-box').removeClass('highlight');
    },

    // start
    event_start : function(index, file, message)
    {
        // make id
        var id = '#galaxy-upload-file-' + index;
        
        // add tag
        $('#galaxy-upload-box').append(this.template_file(id));
        
        // update title
        $('#galaxy-upload-file-' + index).find('.title').html(file.name);
        
        // initialize progress
        this.event_progress(index, file, 0);
        
        // update counter
        this.file_counter++;
        this.refresh();
    },
    
    // progress
    event_progress : function(index, file, message)
    {
        // get progress bar
        var el = $('#galaxy-upload-file-' + index);
        
        // get value
        var percentage = parseInt(message);
        
        // update progress
        el.find('.progress').css({ width : percentage + '%' });
        
        // update info
        el.find('.info').html(percentage + '% of ' + this.size_to_string (file.size));
    },
    
    // end
    event_success : function(index, file, message)
    {
        // update galaxy history
        Galaxy.currHistoryPanel.refresh();
        
        // update counter
        this.file_counter--;
        this.refresh();
    },
    
    // end
    event_error : function(index, file, message)
    {
        // get file box
        var el = $('#galaxy-upload-file-' + index);
        
        // update progress frame
        el.find('.progress-frame').addClass('failed');
        
        // update error message
        el.find('.error').html("<strong>Failed:</strong> " + message);

        // update progress
        this.event_progress(index, file, 0);
        
        // update counter
        this.file_counter--;
        this.refresh();
    },
    
    // show/hide upload frame
    event_show : function (e)
    {
        // prevent default
        e.preventDefault();
        
        // wait for galaxy history panel (workaround due to the use of iframes)
        if (!Galaxy.currHistoryPanel)
        {
            var self = this;
            window.setTimeout(function() { self.event_show(e) }, 200)
            return;
        }
        
        // create modal
        if (!this.modal)
        {
            // make modal
            var self = this;
            this.modal = new mod_modal.GalaxyModal(
            {
                title   : 'Upload files from your local drive',
                body    : this.template(),
                buttons : {
                    'Close' : function() {self.modal.hide()}
                }
            });
        
            // get current history
            var current_history = Galaxy.currHistoryPanel.model.get('id');
        
            // file upload
            var self = this;
            $('#galaxy-upload-box').uploadbox(
            {
                url             : galaxy_config.root + "api/histories/" + current_history + "/contents",
                dragover        : self.event_mouseover,
                dragleave       : self.event_mouseleave,
                start           : function(index, file, message) { self.event_start(index, file, message) },
                success         : function(index, file, message) { self.event_success(index, file, message) },
                progress        : function(index, file, message) { self.event_progress(index, file, message) },
                error           : function(index, file, message) { self.event_error(index, file, message) },
                data            : {source : "upload"}
            });
            
            // set element
            this.setElement('#galaxy-upload-box');
        }
        
        // show modal
        this.modal.show();
    },

    // update counter
    refresh: function ()
    {
        if (this.file_counter > 0)
            this.button_show.number(this.file_counter);
        else
            this.button_show.number('');
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

    // load html template
    template: function()
    {
        return  '<form id="galaxy-upload-box" class="galaxy-upload-box"></form>';
    },
    
    // load html template
    template_file: function(id)
    {
        return  '<div id="' + id.substr(1) + '" class="file corner-soft shadow">' +
                    '<div class="title"></div>' +
                    '<div class="error"></div>' +
                    '<div class="progress-frame corner-soft">' +
                        '<div class="progress"></div>' +
                    '</div>' +
                    '<div class="info"></div>' +
                '</div>';
    }
});

// return
return {
    GalaxyUpload: GalaxyUpload
};

});
