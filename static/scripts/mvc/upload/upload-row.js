// dependencies
define(['mvc/upload/upload-model', 'mvc/upload/upload-extensions'], function(UploadModel, UploadExtensions) {

// item view
return Backbone.View.extend({
    // options
    options: {
        padding : 8,
        timeout : 2000
    },
    
    // states
    status_classes : {
        init    : 'symbol fa fa-trash-o',
        queued  : 'symbol fa fa-spinner fa-spin',
        running : 'symbol fa fa-spinner fa-spin',
        success : 'symbol fa fa-check',
        error   : 'symbol fa fa-exclamation-triangle'
    },
    
    // render
    initialize: function(app, options) {
        // link app
        this.app = app;
        
        // link this
        var self = this;
        
        // create model
        this.model = new UploadModel.Model(options);
        
        // add upload item
        this.setElement(this._template(options));

        // link item
        var it = this.$el;
        
        // handle click event
        it.find('#symbol').on('click', function() {
            // get current status
            var status = self.model.get('status');
            
            // only remove from queue if not in processing line
            if (status == 'init' || status == 'success' || status == 'error')
            {
                // remove from collection
                self.app.collection.remove(self.model);
            }
        });
        
        // handle mouse over
        it.find('#extension_info').on('mouseover' , function() { self._showExtensionInfo(); })
                                  .on('mouseleave', function() { self._hideExtensionInfo(); });

        // handle text editing event
        it.find('#text-content').on('keyup', function() {
            // get properties
            var $el     = it.find('#text-content');
            var value   = $el.val();
            var count   = value.length;
            
            // update size string
            it.find('#size').html(self._formatSize (count));
            
            // update url paste content
            self.model.set('url_paste', value);
            self.model.set('file_size', count);
        });
        
        // handle genome selection
        it.find('#genome').on('change', function(e) {
            self.model.set('genome', $(e.target).val());
        });
        
        // handle extension selection
        it.find('#extension').on('change', function(e) {
            self.model.set('extension', $(e.target).val());
            self.$el.find('#extension_info').popover('destroy');
        });
        
        // handle space to tabs button
        it.find('#space_to_tabs').on('change', function(e) {
            self.model.set('space_to_tabs', $(e.target).prop('checked'));
        });
        
        // events
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
        var file_name = this.model.get('file_name');
        var file_size = this.model.get('file_size');
        
        // link item
        var it = this.$el;
        
        // update title
        it.find('#title').html(file_name);
    
        // update info
        it.find('#size').html(this._formatSize (file_size));
        
        // activate text field if file content is zero
        if (file_size == -1)
        {
            // get text component
            var text = it.find('#text');
            
            // get padding
            var padding = this.options.padding;
            
            // get dimensions
            var width = it.width() - 2 * padding;
            var height = it.height() - padding;
            
            // set dimensions
            text.css('width', width + 'px');
            text.css('top', height + 'px');
            it.height(height + text.height() + 2 * padding);
            
            // show text field
            text.show();
        }
    },

    // genome
    _refreshGenome: function()
    {
        // update genome info on screen
        var genome = this.model.get('genome');
        this.$el.find('#genome').val(genome);
    },
        
    // progress
    _refreshInfo: function()
    {
        // write error message
        var info = this.model.get('info');
        if (info) {
            this.$el.find('#info').html('<strong>Failed: </strong>' + info).show();
        } else {
            this.$el.find('#info').hide();
        }
    },
            
    // progress
    _refreshPercentage : function()
    {
        var percentage = parseInt(this.model.get('percentage'));
        this.$el.find('.progress-bar').css({ width : percentage + '%' });
        if (percentage != 100)
            this.$el.find('#percentage').html(percentage + '%');
        else
            this.$el.find('#percentage').html('Adding to history...');
    },
    
    // status
    _refreshStatus : function()
    {
        // get element
        var it = this.$el;
        
        // identify new status
        var status = this.model.get('status');
        var status_class = this.status_classes[status];
        
        // identify symbol and reset classes
        var sy = this.$el.find('#symbol');
        sy.removeClass();
        
        // set new status class
        sy.addClass(status_class);
        
        // enable form fields
        if (status == 'init') {
            it.find('#text-content').attr('disabled', false);
            it.find('#genome').attr('disabled', false);
            it.find('#extension').attr('disabled', false);
            it.find('#space_to_tabs').attr('disabled', false);
        } else {
            it.find('#text-content').attr('disabled', true);
            it.find('#genome').attr('disabled', true);
            it.find('#extension').attr('disabled', true);
            it.find('#space_to_tabs').attr('disabled', true);
        }
        
        // success
        if (status == 'success') {
            it.addClass('success');
            it.find('#percentage').html('100%');
        }
        
        // error
        if (status == 'error') {
            it.addClass('danger');
            it.find('.progress').remove();
        }
    },

    // to string
    _formatSize : function (size)
    {
        // identify unit
        var unit = "";
        if (size >= 100000000000)   { size = size / 100000000000; unit = 'TB'; } else
        if (size >= 100000000)      { size = size / 100000000; unit = 'GB'; } else
        if (size >= 100000)         { size = size / 100000; unit = 'MB'; } else
        if (size >= 100)            { size = size / 100; unit = 'KB'; } else
        if (size >  0)              { size = size * 10; unit = 'b'; } else
            return '<strong>-</strong>';
                                    
        // return formatted string
        return '<strong>' + (Math.round(size) / 10) + '</strong> ' + unit;
    },
    
    // attach file info popup
    _showExtensionInfo : function()
    {
        // initialize
        var self = this;
        var $el = $(this.el).find('#extension_info');
        var extension = this.model.get('extension');
        var title = $(this.el).find('#extension').find('option:selected').text();
        
        // create popup
        $el.popover({
            html: true,
            title: title,
            content: UploadExtensions(extension),
            placement: 'bottom',
            container: self.$el.parent()
        });
        
        // show popup
        $el.popover('show');
        
        // clear previous timers
        clearTimeout(this.popover_timeout);
    },

    // attach file info popup
    _hideExtensionInfo : function()
    {
        // remove popup
        var self = this
        this.popover_timeout = setTimeout(function() {
            self.$el.find('#extension_info').popover('destroy');
        }, this.options.timeout);
    },
    
    // template
    _template: function(options)
    {
        // link this
        var self = this;
        
        // construct template
        var tmpl = '<tr id="upload-item-' + options.id + '" class="upload-item">' +
                        '<td>' +
                            '<div style="position: relative;">' +
                                '<div id="title" class="title"></div>' +
                                '<div id="text" class="text">' +
                                    '<div class="text-info">You can tell Galaxy to download data from web by entering URL in this box (one per line). You can also directly paste the contents of a file.</div>' +
                                    '<textarea id="text-content" class="text-content form-control"></textarea>' +
                                '</div>' +
                            '</div>' +
                        '</td>' +
                        '<td><div id="size" class="size"></div></td>';

        // add file type selectore
        tmpl +=         '<td>' +
                            '<select id="extension" class="extension">';
        for (key in self.app.select_extension)
            tmpl +=             '<option value="' + self.app.select_extension[key][1] + '">' + self.app.select_extension[key][0] + '</option>';
        tmpl +=             '</select>' +
                            '&nbsp;<i id="extension_info" class="fa fa-search" style="cursor: pointer;"/>' +
                        '</td>';                        

        // add genome selector
        tmpl +=         '<td>' +
                            '<select id="genome" class="genome">';
        for (key in self.app.select_genome)
            tmpl +=             '<option value="' + self.app.select_genome[key][1] + '">' + self.app.select_genome[key][0] + '</option>';
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
                        '<td><div id="symbol" class="' + this.status_classes.init + '"></div></td>' +
                    '</tr>';
        
        // return html string
        return tmpl;
    }
    
});

});
