/*
    galaxy upload lib v1.0 - uses FileReader, FormData and XMLHttpRequest
*/
;(function($)
{
    // add event properties
    jQuery.event.props.push("dataTransfer");

    // default options
    var default_opts =
    {
        url             : '',
        paramname       : 'content',
        maxfilesize     : 2048,
        data            : {},
        dragover        : function() {},
        dragleave       : function() {},
        initialize      : function() {},
        start           : function() {},
        progress        : function() {},
        success         : function() {},
        error           : function(index, file, message) { alert(message); },
        error_browser   : "Your browser does not support drag-and-drop file uploads.",
        error_filesize  : "This file is too large. Please use an FTP client to upload it.",
        error_default   : "The upload failed. Please make sure the file is available and accessible.",
        text_default    : "Drag&drop files here or click to browse your local drive.",
        text_degrade    : "Click here to browse your local drive. <br><br>Unfortunately, your browser does not support multiple file uploads or drag&drop.<br>Please upgrade to i.e. Firefox 4+, Chrome 7+, IE 10+, Opera 12+ or Safari 6+."
    }

    // global file queue
    var queue = [];
  
    // global counter for file being currently processed
    var queue_index = -1;
  
    // global queue status
    var queue_status = false;
  
    // attach to element
    $.fn.uploadbox = function(options)
    {
        // parse options
        var opts = $.extend({}, default_opts, options);
  
        // compatibility
        var mode = window.File && window.FileReader && window.FormData && window.XMLHttpRequest;
  
        // append upload button
        this.append('<input id="uploadbox_input" type="file" style="display: none" multiple>');
        this.append('<div id="uploadbox_info"></div>');
  
        // set info text
        if (mode)
            this.find('#uploadbox_info').html(opts.text_default);
        else
            this.find('#uploadbox_info').html(opts.text_degrade);
  
        // attach events
        this.on('drop', drop);
        this.on('dragover',  dragover);
        this.on('dragleave', dragleave);
  
        // attach click event
        this.on('click', function(e)
        {
            e.stopPropagation();
            $('#uploadbox_input').trigger(e);
        });
  
        // attach change event
        $('#uploadbox_input').change(function(e)
        {
            var files = e.target.files;
            upload(files);
        });

        // drop event
        function drop(e)
        {
            // check if its a file transfer
            if(!e.dataTransfer)
                return;
            
            // get files from event
            var files = e.dataTransfer.files;
  
            // start upload
            upload(files);
      
            // prevent default
            e.preventDefault();
            
            // return
            return false;
        }

        // drag over
        function dragover(e)
        {
            e.preventDefault();
            opts.dragover.call(this, e);
        }

        // drag leave
        function dragleave(e)
        {
            e.stopPropagation();
            opts.dragleave.call(this, e);
        }

        // progress
        function progress(e)
        {
            // get percentage
            if (e.lengthComputable)
                opts.progress(this.index, this.file, Math.round((e.loaded * 100) / e.total));
        }

        // respond to an upload request
        function upload(files)
        {
            // get current queue size
            var queue_sofar = queue.length;
  
            // add new files to queue
            for (var index = 0; index < files.length; index++)
                queue.push(files[index]);
  
            // tell client about new uploads
            for (var index = queue_sofar; index < queue.length; index++)
                opts.start(index, queue[index], "");
  
            // initiate processing loop if process loop is not running already
            if (!queue_status)
                process();
        }

        // process an upload, recursive
        function process()
        {
            // check if for files
            if (queue_index + 1 == queue.length)
            {
                queue_status = false;
                return;
            }
  
            // set status
            queue_status = true;
  
            // identify current index
            var index = ++queue_index;
  
            // add file to queue
            try
            {
                // load file read
                var reader = new FileReader();
  
                // identify maximum file size
                var file = queue[index];
                var filesize = file.size;
                var maxfilesize = 1048576 * opts.maxfilesize;
                    
                // set index
                reader.index = index;
                if (filesize < maxfilesize)
                {
                    // link loadend is always called at the end
                    reader.onloadend = function(e)
                    {
                        send(index, file)
                    };

                    // link error
                    reader.onerror = function(e)
                    {
                        opts.error(index, file, opts.error_default);
                        queue_status = false;
                    };

                    // read data
                    reader.readAsDataURL(file);
                } else {
                    // skip file
                    opts.error(index, file, opts.error_filesize);
  
                    // restart process
                    process();
                }
            } catch (err)
            {
                // parse error
                opts.error(index, file, err);
            }
        }
  
        // send file
        function send (index, file)
        {
            // construct form data
            var formData = new FormData();
            for (var key in opts.data)
                formData.append(key, opts.data[key]);
            formData.append(opts.paramname, file, file.name);
  
            // prepare request
            var xhr = new XMLHttpRequest();
  
            // prepare upload progress
            xhr.upload.index = index;
            xhr.upload.file = file;
            xhr.upload.addEventListener('progress', progress, false);

            // open request
            xhr.open('POST', opts.url, true);
            xhr.setRequestHeader('Accept', 'application/json');
            xhr.setRequestHeader('Cache-Control', 'no-cache');
            xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
            xhr.send(formData);
  
            // onloadend
            xhr.onloadend = function()
            {
                // retrieve response
                var response = null;
                if (xhr.responseText)
                {
                    try
                    {
                        response = jQuery.parseJSON(xhr.responseText);
                    } catch (e) {
                        response = xhr.responseText;
                    }
                }
  
                // pass any error to the error option
                if (xhr.status < 200 || xhr.status > 299)
                {
                    // request error
                    opts.error(index, file, xhr.statusText + " (Server Code " + xhr.status + ")");
  
                    // reset status
                    queue_status = false;
                } else {
                    // parse response
                    opts.success(index, file, response);

                    // upload next file
                    process();
                }
            }
        }
  
        // return
        return this;
    }
})(jQuery);