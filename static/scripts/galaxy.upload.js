/*
    galaxy upload
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
    
    // upload mod
    uploadbox: null,
    
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
        // hide info
        this.uploadbox.info().hide();
        
        // make id
        var id = '#upload-' + index;
        
        // add upload item
        $(this.el).append(this.template_file(id));
        
        // scroll to bottom
        $(this.el).scrollTop($(this.el).prop('scrollHeight'));
        
        // access upload item
        var it = this.get_upload_item(index);
        
        // fade in
        it.fadeIn();
        
        // update title
        it.find('.title').html(file.name);
        
        // configure select field
        it.find('#extension').select2(
        {
            placeholder: 'Auto-detect',
            width: 'copy',
            ajax: {
                url: "http://www.weighttraining.com/sm/search",
                dataType: 'jsonp',
                quietMillis: 100,
                data: function(term, page)
                {
                    return {
                        types: ["exercise"],
                        limit: -1,
                        term: term
                    };
                },
                results: function(data, page)
                {
                    return { results: data.results.exercise }
                }
            },
            formatResult: function(exercise)
            {
                return "<div class='select2-user-result'>" + exercise.term + "</div>";
            },
            formatSelection: function(exercise)
            {
                return exercise.term;
            },
            initSelection : function (element, callback)
            {
                var elementText = $(element).attr('data-init-text');
                callback({"term":elementText});
            }
        });
        
        // add functionality to remove button
        var self = this;
        it.find('.remove').on('click', function() { self.event_remove (index) });
    
        // initialize progress
        this.event_progress(index, file, 0);
        
        // update button status
        this.modal.enable('Upload');
        this.modal.enable('Reset');
    },
    
    // start
    event_initialize : function(index, file, message)
    {
        // update on screen counter
        this.button_show.number(message);
    
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
    
    // end
    event_success : function(index, file, message)
    {        
        // get element
        var it = this.get_upload_item(index);
        
        // update progress frame
        it.addClass('panel-success');
        it.removeClass('panel-default');
        
        // update galaxy history
        Galaxy.currHistoryPanel.refresh();
        
        // make sure progress is shown correctly
        this.event_progress(index, file, 100);
        
        // update on screen counter
        this.button_show.number('');
    },
    
    // end
    event_error : function(index, file, message)
    {
        // get element
        var it = this.get_upload_item(index);
        
        // update progress frame
        it.addClass('panel-danger');
        it.removeClass('panel-default');
        
        // remove progress bar
        it.find('.progress').remove();
        
        // write error message
        it.find('.error').html('<strong>Failed:</strong> ' + message);
        
        // make sure progress is shown correctly
        this.event_progress(index, file, 0);
        
        // update on screen counter
        this.button_show.number('');
    },
    
    // start upload process
    event_upload : function()
    {
        // hide configuration
        $(this.el).find('.panel-body').hide();
        
        // switch icon
        $(this.el).find('.remove').each(function()
        {
            $(this).removeClass('fa-icon-trash');
            $(this).addClass('fa-icon-caret-down');
        });
        
        // update button status
        this.modal.disable('Upload');
        
        // configure url
        var current_history = Galaxy.currHistoryPanel.model.get('id');
        this.uploadbox.configure({url : galaxy_config.root + "api/histories/" + current_history + "/contents"});
        
        // initiate upload procedure in plugin
        this.uploadbox.upload();
    },
    
    // remove all
    event_reset : function()
    {
        // remove from screen
        var panels = $(this.el).find('.panel');
        var self = this;
        panels.fadeOut({complete: function()
        {
            // remove panels
            panels.remove();
                    
            // show on screen info
            self.uploadbox.info().fadeIn();
        }});
        
        // update button status
        this.modal.disable('Upload');
        this.modal.disable('Reset');
        
        // remove from queue
        this.uploadbox.reset();
    },
    
    // remove item from upload list
    event_remove : function(index)
    {
        // remove
        var self = this;
        var it = this.get_upload_item(index);
        
        // fade out and update button status
        it.fadeOut({complete: function()
        {
            // remove from screen
            it.remove();
        
            // remove from queue
            self.uploadbox.remove(index);
        
            // update reset button
            if ($(self.el).find('.panel').length > 0)
                self.modal.enable('Reset');
            else {
                // disable reset button
                self.modal.disable('Reset');
                
                // show on screen info
                self.uploadbox.info().fadeIn();
            }
            
            // update upload button
            if (self.uploadbox.length() > 0)
                self.modal.enable('Upload');
            else
                self.modal.disable('Upload');
        }});
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
                }
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
            });
            
            // update button status
            this.modal.disable('Upload');
            this.modal.disable('Reset');
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

    // load html template
    template: function(id)
    {
        return  '<div id="' + id + '" class="upload-box"></div>';
    },
    
    // load html template
    template_file: function(id)
    {
        return  '<div id="' + id.substr(1) + '" class="panel panel-default">' +
                    '<div class="panel-heading">' +
                        '<h5 class="title"></h5>' +
                        '<h5 class="info"></h5>' +
                        '<div class="remove fa-icon-trash"></div>' +
                    '</div>' +
                    '<div class="panel-body">' +
                        '<div class="menu">' +
                            //'<input id="extension" type="hidden" width="10px"/>&nbsp;' +
                            '<span><input id="space_to_tabs" type="checkbox">Convert spaces to tabs</input></span>' +
                        '</div>' +
                    '</div>' +
                    '<div class="panel-footer">' +
                        '<div class="progress">' +
                            '<div class="progress-bar progress-bar-success"></div>' +
                        '</div>' +
                        '<h6 class="error"></h6>' +
                    '</div>' +
                '</div>';
    }
});

// return
return {
    GalaxyUpload: GalaxyUpload
};

});
