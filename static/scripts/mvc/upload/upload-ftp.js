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
		// ADD THINGS HERE
		//
			$($('.upload-ftp')[0]).find('#selectAll').on('click', function(){
				var checkboxes=$(this).parent().parent().parent().parent().find('tr.upload-ftp-row>td>div');
				var len = checkboxes.length;
				var allChecked;
 				$this = $(this);
				//
				if($this.hasClass("fa-square-o")){
					$this.removeClass("fa-square-o");
					$this.removeClass("fa-minus-square-o");
					$this.addClass("fa-check-square-o");
					allChecked=true;
				}
				else{
					$this.removeClass("fa-check-square-o");
					$this.removeClass("fa-minus-square-o");
					$this.addClass("fa-square-o");
					allChecked=false;
				}
				//
				for(i = 0; i < len; i++){
					if(allChecked)
					{
					
						checkboxes.eq(i).removeClass("fa-square-o"); 
						checkboxes.eq(i).addClass("fa-check-square-o");
					}
					else{
						checkboxes.eq(i).removeClass("fa-check-square-o"); 
						checkboxes.eq(i).addClass("fa-square-o");
					}
				}
				console.log(checkboxes, allChecked);
				return;
			} );

		

		// END JC ADD


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

        // click to add ftp files
        $it.on('click', function() {
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

				var selectBox=$icon.parent().parent().parent().parent().find('#selectAll');
				var checkboxes=$icon.parent().parent().parent().parent().find('tr.upload-ftp-row>td>div');
				var checkedCheckboxes=$icon.parent().parent().parent().parent().find('tr.upload-ftp-row>td>div.fa-check-square-o');
				var lenAll = checkboxes.length;
				var lenChecked = checkedCheckboxes.length;
//				var checked = 0;
			//	console.log("BeforeLoop " + checked);
			//	for (i = 0; i < len; i++) {
			//		console.log("In loop "+checked, checkboxes.eq(i));
			//		if (checkboxes.eq(i).hasClass("fa-check-square-o")) {
			//		  checked++;
			//			console.log("In if "+checked);
			//		}
			//	}
				if(lenChecked > 0 && lenChecked !== lenAll){
					selectBox.removeClass("fa-square-o");
					selectBox.removeClass("fa-check-square-o");
					selectBox.addClass("fa-minus-square-o");
				}
				else if(lenChecked === lenAll){
					selectBox.removeClass("fa-square-o");
					selectBox.addClass("fa-check-square-o");
					selectBox.removeClass("fa-minus-square-o");
				}
				else if(lenChecked === 0){
					selectBox.addClass("fa-square-o");
					selectBox.removeClass("fa-check-square-o");
					selectBox.removeClass("fa-minus-square-o");
				}
				console.log(checkboxes,lenChecked);

        });

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
                    '<td><div class="icon " /></td>' +
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
//jc added
                            '<th><div id="selectAll" class="upload-icon-button fa fa-square-o" ></th>' +
//end jc added
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
                    '<div id="upload-ftp-content">'
//jc added

//end jc added	
			'</div>' +
                '<div>';
    }
    
});

});
