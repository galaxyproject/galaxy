/** Upload app containing the upload progress button and main modal **/
define(['utils/utils',
        'mvc/ui/ui-modal',
        'mvc/ui/ui-tabs',
        'mvc/upload/upload-button',
        'mvc/upload/upload-view-default'],
        function(   Utils,
                    Modal,
                    Tabs,
                    UploadButton,
                    UploadViewDefault ) {
return Backbone.View.extend({
    // default options
    options : {
        nginx_upload_path   : '',
        ftp_upload_site     : 'n/a',
        default_genome      : '?',
        default_extension   : 'auto',
        height              : 480,
        width               : 900,
        auto                : {
            id          : 'auto',
            text        : 'Auto-detect',
            description : 'This system will try to detect the file type automatically. If your file is not detected properly as one of the known formats, it most likely means that it has some format problems (e.g., different number of columns on different rows). You can still coerce the system to set your data to the format you think it should be.  You can also upload compressed files, which will automatically be decompressed.'
        }
    },

    // upload modal container
    modal: null,

    // progress button in panel
    ui_button: null,

    // current history identifier
    current_history: null,

    // contains all available dataset extensions/types
    list_extensions: [],

    // contains all available genomes
    list_genomes: [],

    // initialize
    initialize: function(options) {
        // link this
        var self = this;

        // merge parsed options
        this.options = Utils.merge(options, this.options);

        // create model for upload/progress button
        this.ui_button = new UploadButton.Model();

        // create view for upload/progress button
        this.ui_button_view = new UploadButton.View({
            model       : this.ui_button,
            onclick     : function(e) {
                e.preventDefault();
                self.show()
            },
            onunload    : function() {
                //if (self.counter.running > 0) {
                //    return 'Several uploads are still processing.';
                //}
            }
        });

        // append button to container
        $('.with-upload-button').append(this.ui_button_view.$el);

        // load extensions
        var self = this;
        Utils.get({
            url     : galaxy_config.root + 'api/datatypes?extension_only=False',
            success : function(datatypes) {
                for (key in datatypes) {
                    self.list_extensions.push({
                        id              : datatypes[key].extension,
                        text            : datatypes[key].extension,
                        description     : datatypes[key].description,
                        description_url : datatypes[key].description_url
                    });
                }

                // sort
                self.list_extensions.sort(function(a, b) {
                    return a.text > b.text ? 1 : a.text < b.text ? -1 : 0;
                });

                // add auto field
                if (!self.options.datatypes_disable_auto) {
                    self.list_extensions.unshift(self.options.auto);
                }
            }
        });

        // load genomes
        Utils.get({
            url     : galaxy_config.root + 'api/genomes',
            success : function(genomes) {
                for (key in genomes) {
                    self.list_genomes.push({
                        id      : genomes[key][1],
                        text    : genomes[key][0]
                    });
                }

                // sort
                self.list_genomes.sort(function(a, b) {
                    if (a.id == self.options.default_genome) { return -1; }
                    if (b.id == self.options.default_genome) { return 1; }
                    return a.text > b.text ? 1 : a.text < b.text ? -1 : 0;
                });
            }
        });
    },

    //
    // event triggered by upload button
    //

    // show/hide upload frame
    show: function () {
        // wait for galaxy history panel
        var self = this;
        if (!Galaxy.currHistoryPanel || !Galaxy.currHistoryPanel.model) {
            window.setTimeout(function() { self.show() }, 500)
            return;
        }

        // refresh
        this.refresh();

        // create modal
        if (!this.modal) {
            // build tabs
            this.tabs = new Tabs.View();

            // add tab
            this.default_view = new UploadViewDefault(this);
            this.tabs.add({
                id      : 'default',
                title   : 'Default',
                $el     : this.default_view.$el
            });

            // make modal
            this.modal = new Modal.View({
                title           : 'Download data directly from web or upload files from your disk',
                body            : this.tabs.$el,
                height          : this.options.height,
                width           : this.options.width,
                closing_events  : true
            });
        }

        // show modal
        this.modal.show();
    },

    // update user and current history
    refresh: function() {
        this.current_user = Galaxy.currUser.get('id');
        this.current_history = null;
        if (this.current_user) {
            this.current_history = Galaxy.currHistoryPanel.model.get('id');
        }
    }
});

});
