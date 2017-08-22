// Provides support for interacting with the GenomeSpace File Browser popup dialogue
define([], function() {

// tool form templates
return {
    openFileBrowser: function( options ) {
        var GS_UI_URL = window.Galaxy.config.genomespace_ui_url;
        var GS_UPLOAD_URL = GS_UI_URL + 'upload/loadUrlToGenomespace.html?getLocation=true'

        var newWin = window.open(GS_UPLOAD_URL, "GenomeSpace File Browser", "height=360px,width=600px");
         
        successCalBack = options['successCallback'];
        window.addEventListener( "message", function (e) {
             successCalBack(e.data);    
          }, false);
      
        newWin.focus();
       
        if (options['errorCallback'] != null) newWin.setCallbackOnGSUploadError = config['errorCallback'];  
    }

};

});