/** Renders contents of the composite uploader */
define(['utils/utils',
        'mvc/upload/upload-model',
        'mvc/upload/composite/composite-row',
        'mvc/ui/ui-popover',
        'mvc/ui/ui-select',
        'mvc/ui/ui-misc'],

        function(   Utils,
                    UploadModel,
                    UploadRow,
                    Popover,
                    Select,
                    Ui
                ) {

return Backbone.View.extend({
    // extension selector
    select_extension: null,

    // genome selector
    select_genome: null,

    // collection
    collection: new UploadModel.Collection(),

    // initialize
    initialize: function(app) {
        // link app
        this.app                = app;
        this.options            = app.options;
        this.list_extensions    = app.list_extensions;
        this.list_genomes       = app.list_genomes;
        this.ftp_upload_site    = app.currentFtp();

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
                self.collection.reset();
                var details = _.findWhere(self.list_extensions, { id : extension });
                if (details && details.composite_files) {
                    for (var i in details.composite_files) {
                        var item = details.composite_files[i];
                        self.collection.add({
                            id          : self.collection.size(),
                            file_desc   : item['description'] || item['name']
                        });
                    }
                }
            }
        });

        // handle extension info popover
        this.$('#footer-extension-info').on('click', function(e) {
            self._showExtensionInfo({
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
        this.collection.on('add', function (model) {
            self._eventAnnounce(model);
        });
        this.collection.on('change add', function() {
            self._updateScreen();
        }).trigger('change');

        // trigger initial onchange event
        this.select_extension.options.onchange(this.select_extension.value());
    },

    //
    // upload events / process pipeline
    //

    // builds the basic ui with placeholder rows for each composite data type file
    _eventAnnounce: function(model) {
        // create view/model
        var upload_row = new UploadRow(this, { model : model });

        // add upload row element to table
        this.$('#upload-table > tbody:first').append(upload_row.$el);

        // render
        upload_row.render();

        // table visibility
        if (this.collection.length > 0) {
            this.$('#upload-table').show();
        } else {
            this.$('#upload-table').hide();
        }
    },

    // start upload process
    _eventStart: function() {
        var self = this;
        this.collection.each(function(model) {
            model.set('genome', self.select_genome.value());
            model.set('extension', self.select_extension.value());
        });
        $.uploadpost({
            url      : this.app.options.nginx_upload_path,
            data     : this.app.toData(this.collection.filter()),
            success  : function(message) { self._eventSuccess(message); },
            error    : function(message) { self._eventError(message); },
            progress : function(percentage) { self._eventProgress(percentage); }
        });
    },

    // progress
    _eventProgress: function(percentage) {
        this.collection.each(function(it) { it.set('percentage', percentage); });
    },

    // success
    _eventSuccess: function(message) {
        this.collection.each(function(it) {
            it.set('status', 'success');
        });
        Galaxy.currHistoryPanel.refreshContents();
    },

    // error
    _eventError: function(message) {
        this.collection.each(function(it) {
            it.set('status', 'error');
            it.set('info', message);
        });
    },

    // display extension info popup
    _showExtensionInfo: function(options) {
        // initialize
        var self = this;
        var $el = options.$el;
        var extension = options.extension;
        var title = options.title;
        var description = _.findWhere(this.list_extensions, { id : extension });

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

    // set screen
    _updateScreen: function () {
        // show start button if components have been selected
        var model = this.collection.first();
        if (model && model.get('status') == 'running') {
            this.select_genome.disable();
            this.select_extension.disable();
        } else {
            this.select_genome.enable();
            this.select_extension.enable();
        }
        if (this.collection.where({ status : 'ready' }).length == this.collection.length && this.collection.length > 0) {
            this.btnStart.enable();
            this.btnStart.$el.addClass('btn-primary');
        } else {
            this.btnStart.disable();
            this.btnStart.$el.removeClass('btn-primary');
        }

        // table visibility
        if (this.collection.length > 0) {
            this.$('#upload-table').show();
        } else {
            this.$('#upload-table').hide();
        }
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
                    '<div id="upload-footer" class="upload-footer">' +
                        '<span class="footer-title">Composite Type:</span>' +
                        '<span id="footer-extension"/>' +
                        '<span id="footer-extension-info" class="upload-icon-button fa fa-search"/> ' +
                        '<span class="footer-title">Genome/Build:</span>' +
                        '<span id="footer-genome"/>' +
                    '</div>' +
                    '<div id="upload-box" class="upload-box">' +
                        '<table id="upload-table" class="ui-table-striped" style="display: none;">' +
                            '<thead>' +
                                '<tr>' +
                                    '<th/>' +
                                    '<th/>' +
                                    '<th>Description</th>' +
                                    '<th>Name</th>' +
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
