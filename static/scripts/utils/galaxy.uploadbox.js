/*
    galaxy upload lib - uses FileReader, FormData and XMLHttpRequest
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
        maxfilesize     : 250,
        dragover        : function() {},
        dragleave       : function() {},
        announce        : function() {},
        initialize      : function() {},
        progress        : function() {},
        success         : function() {},
        error           : function(index, file, message) { alert(message); },
        complete        : function() {},
        error_browser   : "Your browser does not support drag-and-drop file uploads.",
        error_filesize  : "This file is too large (>250MB). Please use an FTP client to upload it.",
        error_default   : "Please make sure the file is available."
    }

    // options
    var opts = {};

    // file queue
    var queue = {};
  
    // queue index counter
    var queue_index = 0;
  
    // queue length
    var queue_length = 0;
  
    // indicates if queue is currently running
    var queue_status = false;
  
    // element
    var el = null;
  
    // attach to element
    $.fn.uploadbox = function(options)
    {
        // parse options
        opts = $.extend({}, default_opts, options);
  
        // element
        el = this;
  
        // append upload button
        el.append('<input id="uploadbox_input" type="file" style="display: none" multiple>');
  
        // attach events
        el.on('drop', drop);
        el.on('dragover',  dragover);
        el.on('dragleave', dragleave);
  
        // attach change event
        $('#uploadbox_input').change(function(e)
        {
            // add files to queue
            add(e.target.files);
        });

        // drop event
        function drop(e)
        {
            // check if its a file transfer
            if(!e.dataTransfer)
                return;
            
            // add files to queue
            add(e.dataTransfer.files);
      
            // prevent default
            e.preventDefault();
            
            // return
            return false;
        }

        // drag over
        function dragover(e)
        {
            e.preventDefault();
            opts.dragover.call(e);
        }

        // drag leave
        function dragleave(e)
        {
            e.stopPropagation();
            opts.dragleave.call(e);
        }

        // progress
        function progress(e)
        {
            // get percentage
            if (e.lengthComputable)
                opts.progress(this.index, this.file, Math.round((e.loaded * 100) / e.total));
        }

        // respond to an upload request
        function add(files)
        {
            // only allow adding file if current batch is complete
            if (queue_status)
                return;
  
            // add new files to queue
            for (var i = 0; i < files.length; i++)
            {
                // new identifier
                var index = String(queue_index++);
  
                // add to queue
                queue[index] = files[i];
  
                // increase counter
                queue_length++;
  
                // announce
                opts.announce(index, queue[index], "");
            }
        }

        // remove entry from queue
        function remove(index)
        {
            if (queue[index])
            {
                // remove from queue
                delete queue[index];
  
                // update counter
                queue_length--;
            }
        }
  
        // process an upload, recursive
        function process()
        {
            // validate
            if (queue_length == 0)
            {
                queue_status = false;
                opts.complete();
                return;
            } else
                queue_status = true;
  
            // get an identifier from the queue
            var index = -1;
            for (var key in queue)
            {
                index = key;
                break;
            }
  
            // get current file from queue
            var file = queue[index];
  
            // remove from queue
            remove(index)
  
            // start
            var data = opts.initialize(index, file);
  
            // add file to queue
            try
            {
                // load file read
                var reader = new FileReader();
  
                // identify maximum file size
                var filesize = file.size;
                var maxfilesize = 1048576 * opts.maxfilesize;
    
                // set index
                reader.index = index;
                if (filesize < maxfilesize)
                {
                    // link load
                    reader.onload = function(e)
                    {
                        send(index, file, data)
                    };

                    // link error
                    reader.onerror = function(e)
                    {
                        error(index, file, opts.error_default);
                    };

                    // read data
                    reader.readAsDataURL(file);
                } else {
                    // skip file
                    error(index, file, opts.error_filesize);
                }
            } catch (err)
            {
                // parse error
                error(index, file, err);
            }
        }
  
        // send file
        function send (index, file, data)
        {
            // construct form data
            var formData = new FormData();
            for (var key in data)
                formData.append(key, data[key]);
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
                    // format error
                    var text = xhr.statusText;
                    if (!xhr.statusText)
                        text = opts.error_default;
  
                    // request error
                    error(index, file, text + " (Server Code " + xhr.status + ")");
                } else
                    // parse response
                    success(index, file, response);
            }
        }
  
        // success
        function success (index, file, msg)
        {
            // parse message
            opts.success(index, file, msg);
  
            // restart process after success
            process();
        }
  
        // error
        function error (index, file, err)
        {
            // parse error
            opts.error(index, file, err);
  
            // restart process after error
            process();
        }
  
        /*
            public interface
        */
    
        // open file browser for selection
        function select()
        {
            $('#uploadbox_input').trigger('click');
        }
  
        // remove all entries from queue
        function reset(index)
        {
            for (index in queue)
                remove(index);
        }
  
        // initiate upload process
        function upload()
        {
            if (!queue_status)
                process();
        }
  
        // set options
        function configure(options)
        {
            // update current configuration
            opts = $.extend({}, opts, options);
  
            // return new configuration
            return opts;
        }
  
        // verify browser compatibility
        function compatible()
        {
            return window.File && window.FileReader && window.FormData && window.XMLHttpRequest;
        }
  
        // export functions
        return {
            'select'        : select,
            'remove'        : remove,
            'upload'        : upload,
            'reset'         : reset,
            'configure'     : configure,
            'compatible'    : compatible
        };
    }
})(jQuery);