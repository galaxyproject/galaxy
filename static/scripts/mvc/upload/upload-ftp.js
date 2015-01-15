// dependencies
define(['utils/utils'], function(Utils) {

// item view
return Backbone.View.extend({
    // options
    options: {
        class_add       : 'upload-icon-button fa fa-square-o',
        class_remove    : 'upload-icon-button fa fa-check-square-o'
    },
    
    // render
    initialize: function(app) {
        // link app
        this.app = app;
        
        // link this
        var self = this;
        
        // set template
        this.setElement(this._template());
        
        // load extension
        Utils.get({
            url     : galaxy_config.root + 'api/ftp_files',
            success : function(ftp_files) { self._fill(ftp_files); },
            error   : function() { self._fill(); }
        });
    },
    
    // events
    events: {
        'mousedown' : function(e) { e.preventDefault(); }
    },
    
    // fill table
    _fill: function(ftp_files) {
        var self = this;
        if (ftp_files && ftp_files.length > 0) {
            // add table
            this.$el.find('#upload-ftp-content').html($(this._templateTable()));
            
            // add files to table
            var size = 0;
            for (key in ftp_files) {
                this.add(ftp_files[key]);
                size += ftp_files[key].size;
            }
            
            // update stats
            this.$el.find('#upload-ftp-number').html(ftp_files.length + ' files');
            this.$el.find('#upload-ftp-disk').html(Utils.bytesToString (size, true));

            var selectAll = this.$el.find('#selectAll');

            // call method to determine and set selectAll status on loading
            this._updateSelectAll(selectAll);

            // selectAll checkbox has been clicked
            selectAll.on('click', function() {
                var checkboxes=$(this).parents().find('tr.upload-ftp-row>td>div');
                var len = checkboxes.length;
                $this = $(this);
                var allChecked = !($this.hasClass('fa-check-square-o'));
               


                // change state of the selectAll checkbox
                // if($this.hasClass('fa-check-square-o')) {
                //     // if checked change to unchecked
                //     $this.removeClass('fa-check-square-o');
                //     $this.addClass('fa-square-o');
                //     allChecked=false;
                // } else {
                //     // if checked or partially checked, change to checked
                //     $this.removeClass('fa-square-o fa-minus-square-o');
                //     $this.addClass('fa-check-square-o');
                //     allChecked=true;
                // }

                // change state of the sub-checkboxes
                for(i = 0; i < len; i++) {
                    if(allChecked) {
                        // all checkboxes should be checked
                        if(checkboxes.eq(i).hasClass('fa-square-o')) {
                            // if they are not checked, check them
                            checkboxes.eq(i).trigger('addToUpBox');
                        }
                    } else {
                        // no checkboxes should be checked
                        if(checkboxes.eq(i).hasClass('fa-check-square-o')) {
                            // if they are checked, uncheck them
                            checkboxes.eq(i).trigger('addToUpBox');
                        }
                    }
                }
                self._updateSelectAll(selectAll);
                return;
            });

        } else {
            // add info
            this.$el.find('#upload-ftp-content').html($(this._templateInfo()));
        }

        // hide spinner
        this.$el.find('#upload-ftp-wait').hide();
    },
    
    // add
    add: function(ftp_file) {
        // link this
        var self = this;
        
        // create new item
        var $it = $(this._templateRow(ftp_file));
        
        // identify icon
        var $icon = $it.find('.icon');
        
        // append to table
        $(this.el).find('tbody').append($it);
        
        // find model and set initial 'add' icon class
        var icon_class = '';
        if (this._find(ftp_file)) {
            icon_class = this.options.class_remove;
        } else {
            icon_class = this.options.class_add;
        }

        // add icon class
        $icon.addClass(icon_class);
        
        $it.on('addToUpBox', function() {
            // find model
            var model_index = self._find(ftp_file);

            // update icon
            $icon.removeClass();

            // add model
            if (!model_index) {
                // add to uploadbox
                self.app.uploadbox.add([{
                    mode        : 'ftp',
                    name        : ftp_file.path,
                    size        : ftp_file.size,
                    path        : ftp_file.path
                }]);

                // add new icon class
                $icon.addClass(self.options.class_remove);
            } else {
                // remove
                self.app.collection.remove(model_index);

                // add new icon class
                $icon.addClass(self.options.class_add);
            }
        });

        // click to add ftp files
        $it.on('click', function() {
            //trigger my new event
            $icon.trigger('addToUpBox');

            // click to add ftp files
            // modify selectAll box based on number of checkboxes checked
            var selectBox=$icon.parents().find('#selectAll');
            // determine and set state of selectAll after sub-checkbox clicked
            self._updateSelectAll(selectBox);
        });
    },

    _updateSelectAll: function(selectBox) {
        // array of all checkboxes
        var checkboxes=selectBox.parents().find('tr.upload-ftp-row>td>div');
        // array of only checked checkboxes
        var checkedCheckboxes=selectBox.parents().find('tr.upload-ftp-row>td>div.fa-check-square-o');
        var lenAll = checkboxes.length;
        var lenChecked = checkedCheckboxes.length;

        // determine which state the selectAll checkbox needs to be and setting it
        if(lenChecked > 0 && lenChecked !== lenAll) {
            // indeterminate state
            selectBox.removeClass('fa-square-o fa-check-square-o');
            selectBox.addClass('fa-minus-square-o');
        } else if(lenChecked === lenAll) {
            // checked state
            selectBox.removeClass('fa-square-o fa-minus-square-o');
            selectBox.addClass('fa-check-square-o');
        } else if(lenChecked === 0) {
            // unchecked state
            selectBox.removeClass('fa-check-square-o fa-minus-square-o');
            selectBox.addClass('fa-square-o');
        }
    },



    // get model index
    _find: function(ftp_file) {
        // check if exists already
        var filtered = this.app.collection.where({file_path : ftp_file.path});
        var model_index = null;
        for (var key in filtered) {
            var item = filtered[key];
            if (item.get('status') == 'init' && item.get('file_mode') == 'ftp') {
                model_index = item.get('id');
            }
        }
        return model_index;
    },
    
    // template row
    _templateRow: function(options) {
        return  '<tr class="upload-ftp-row" style="cursor: pointer;">' +
                    '<td><div class="icon"/></td>' +
                    '<td style="width: 200px"><p style="width: inherit; word-wrap: break-word;">' + options.path + '</p></td>' +
                    '<td style="white-space: nowrap;">' + Utils.bytesToString(options.size) + '</td>' +
                    '<td style="white-space: nowrap;">' + options.ctime + '</td>' +
                '</tr>';
    },
    
    // load table template
    _templateTable: function() {
        return  '<span style="whitespace: nowrap; float: left;">Available files: </span>' +
                '<span style="whitespace: nowrap; float: right;">' +
                    '<span class="upload-icon fa fa-file-text-o"/>' +
                    '<span id="upload-ftp-number"/>&nbsp;&nbsp;' +
                    '<span class="upload-icon fa fa-hdd-o"/>' +
                    '<span id="upload-ftp-disk"/>' +
                '</span>' +
                '<table class="grid" style="float: left;">' +
                    '<thead>' +
                        '<tr>' +
                            '<th><div id="selectAll" class="upload-icon-button fa fa-square-o" ></th>' +
                            '<th>Name</th>' +
                            '<th>Size</th>' +
                            '<th>Created</th>' +
                        '</tr>' +
                    '</thead>' +
                    '<tbody></tbody>' +
                '</table>';
    },
    
    // load table template
    _templateInfo: function() {
        return  '<div class="upload-ftp-warning warningmessage">' +
                    'Your FTP directory does not contain any files.' +
                '</div>';
    },
    
    // load html template
    _template: function() {
        return  '<div class="upload-ftp">' +
                    '<div id="upload-ftp-wait" class="upload-ftp-wait fa fa-spinner fa-spin"/>' +
                    '<div class="upload-ftp-help">This Galaxy server allows you to upload files via FTP. To upload some files, log in to the FTP server at <strong>' + this.app.options.ftp_upload_site + '</strong> using your Galaxy credentials (email address and password).</div>' +
                    '<div id="upload-ftp-content"></div>' +
                '<div>';
    }
    
});

});
