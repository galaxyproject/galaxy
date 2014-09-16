// dependencies
define(['utils/utils',
        'mvc/upload/upload-model',
        'mvc/upload/upload-settings',
        'mvc/ui/ui-popover',
        'mvc/ui/ui-select'],
       
        function(   Utils,
                    UploadModel,
                    UploadSettings,
                    Popover,
                    Select
                ) {

// item view
return Backbone.View.extend({
    // options
    options: {
        padding : 8
    },
    
    // states
    status_classes : {
        init    : 'upload-icon-button fa fa-trash-o',
        queued  : 'upload-icon fa fa-spinner fa-spin',
        running : 'upload-icon fa fa-spinner fa-spin',
        success : 'upload-icon-button fa fa-check',
        error   : 'upload-icon-button fa fa-exclamation-triangle'
    },
    
    // handle for settings popover
    settings: null,
    
    // genome selector
    select_genome : null,
    
    // extension selector
    select_extension : null,
    
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
        
        // append popup to settings icon
        this.settings = new Popover.View({
            title       : 'Upload configuration',
            container   : it.find('#settings'),
            placement   : 'bottom'
        });

        // select genomes
        this.select_genome = new Select.View({
            css: 'genome',
            onchange : function() {
                self.model.set('genome', self.select_genome.value());
            },
            data: self.app.list_genomes,
            container: it.find('#genome'),
            value: self.model.get('genome')
        });
        
        // initialize genome
        this.model.set('genome', self.select_genome.value());

        // select extension
        this.select_extension = new Select.View({
            css: 'extension',
            onchange : function() {
                self.model.set('extension', self.select_extension.value());
            },
            data: self.app.list_extensions,
            container: it.find('#extension'),
            value: self.model.get('extension')
        });
        
        // initialize extension
        this.model.set('extension', self.select_extension.value());
        
        //
        // ui events
        //
        
        // handle click event
        it.find('#symbol').on('click', function() { self._removeRow(); });
        
        // handle extension info popover
        it.find('#extension-info').on('click' , function(e) { self._showExtensionInfo(); })
                                  .on('mousedown', function(e) { e.preventDefault(); });

        // handle settings popover
        it.find('#settings').on('click' , function(e) { self._showSettings(); })
                            .on('mousedown', function(e) { e.preventDefault(); });

        // handle text editing event
        it.find('#text-content').on('keyup', function(e) {
            self.model.set('url_paste', $(e.target).val());
            self.model.set('file_size', $(e.target).val().length);
        });
        
        // handle space to tabs button
        it.find('#space_to_tabs').on('change', function(e) {
            self.model.set('space_to_tabs', $(e.target).prop('checked'));
        });
        
        //
        // model events
        //
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
        this.model.on('change:file_size', function() {
            self._refreshFileSize();
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
        var file_name   = this.model.get('file_name');
        var file_size   = this.model.get('file_size');
        var file_mode   = this.model.get('file_mode');
        
        // link item
        var it = this.$el;
        
        // update title
        it.find('#title').html(file_name);
    
        // update info
        it.find('#size').html(Utils.bytesToString (file_size));
        
        // remove mode class
        it.find('#mode').removeClass()
                        .addClass('mode');
        
        // activate text field if file is new
        if (file_mode == 'new')
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
            
            // update icon
            it.find('#mode').addClass('fa fa-pencil');
        }
        
        // file from local disk
        if (file_mode == 'local') {
            // update icon
            it.find('#mode').addClass('fa fa-laptop');
        }
        
        // file from ftp
        if (file_mode == 'ftp') {
            // update icon
            it.find('#mode').addClass('fa fa-code-fork');
        }
    },

    // remove
    remove: function() {
        // trigger remove event
        this.select_genome.remove();
        this.select_extension.remove();
        
        // call the base class remove method
        Backbone.View.prototype.remove.apply(this);
    },

    //
    // handle model events
    //
    
    // genome
    _refreshGenome: function() {
        // update genome info on screen
        var genome = this.model.get('genome');
        this.select_genome.value(genome);
    },
        
    // progress
    _refreshInfo: function() {
        // write error message
        var info = this.model.get('info');
        if (info) {
            this.$el.find('#info').html('<strong>Failed: </strong>' + info).show();
        } else {
            this.$el.find('#info').hide();
        }
    },
            
    // progress
    _refreshPercentage : function() {
        var percentage = parseInt(this.model.get('percentage'));
        this.$el.find('.progress-bar').css({ width : percentage + '%' });
        if (percentage != 100)
            this.$el.find('#percentage').html(percentage + '%');
        else
            this.$el.find('#percentage').html('Adding to history...');
    },
    
    // status
    _refreshStatus : function() {
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
            // select fields
            this.select_genome.enable();
            this.select_extension.enable();
       
            // default fields
            it.find('#text-content').attr('disabled', false);
            it.find('#space_to_tabs').attr('disabled', false);
        } else {
            // select fields
            this.select_genome.disable();
            this.select_extension.disable();
       
            // default fields
            it.find('#text-content').attr('disabled', true);
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

    // refresh size
    _refreshFileSize: function() {
        var count = this.model.get('file_size');
        this.$el.find('#size').html(Utils.bytesToString (count));
    },

    //
    // handle ui events
    //
    
    // remove row
    _removeRow: function() {
        // get current status
        var status = this.model.get('status');
        
        // only remove from queue if not in processing line
        if (status == 'init' || status == 'success' || status == 'error') {
            this.app.collection.remove(this.model);
        }
    },
    
    // attach file info popup
    _showExtensionInfo : function() {
        // initialize
        var $el = $(this.el).find('#extension-info');
        var extension = this.model.get('extension');
        var title = this.select_extension.text();
        var description = _.findWhere(this.app.list_extensions, {'id': extension});
        
        // create popup
        if (!this.extension_popup) {
            this.extension_popup = new Popover.View({
                placement: 'bottom',
                container: $el
            });
        }
        
        // show / hide popup
        if (!this.extension_popup.visible) {
            this.extension_popup.title(title);
            this.extension_popup.empty();
            this.extension_popup.append(this._templateDescription(description));
            this.extension_popup.show();
        } else {
            this.extension_popup.hide();
        }
    },

    // attach file info popup
    _showSettings : function() {
        // check if popover is visible
        if (!this.settings.visible) {
            // show popover
            this.settings.empty();
            this.settings.append((new UploadSettings(this)).$el);
            this.settings.show();
        } else {
            // hide popover
            this.settings.hide();
        }
    },
    
    // template
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
    
    // template
    _template: function(options) {
        return  '<tr id="upload-item-' + options.id + '" class="upload-item">' +
                    '<td>' +
                        '<div style="position: relative;">' +
                            '<div id="mode"></div>' +
                            '<div id="title" class="title"></div>' +
                            '<div id="text" class="text">' +
                                '<div class="text-info">You can tell Galaxy to download data from web by entering URL in this box (one per line). You can also directly paste the contents of a file.</div>' +
                                '<textarea id="text-content" class="text-content form-control"></textarea>' +
                            '</div>' +
                        '</div>' +
                    '</td>' +
                    '<td>' +
                        '<div id="size" class="size"></div>' +
                    '</td>' +
                    '<td>' +
                        '<div id="extension" class="extension" style="float: left;"/>&nbsp;&nbsp' +
                        '<div id="extension-info" class="upload-icon-button fa fa-search"/>' +
                    '</td>' +
                    '<td>' +
                        '<div id="genome" class="genome" />' +
                    '</td>' +
                    '<td><div id="settings" class="upload-icon-button fa fa-gear"></div>' +
                    '<td>' +
                        '<div id="info" class="info">' +
                            '<div class="progress">' +
                                '<div class="progress-bar progress-bar-success"></div>' +
                                '<div id="percentage" class="percentage">0%</div>' +
                            '</div>' +
                        '</div>' +
                    '</td>' +
                    '<td>' +
                        '<div id="symbol" class="' + this.status_classes.init + '"></div>' +
                    '</td>' +
                '</tr>';
    }
    
});

});
