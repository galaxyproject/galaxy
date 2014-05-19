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
        maxfilesize     : 2048,
        maxfilenumber   : 50,
        dragover        : function() {},
        dragleave       : function() {},
        announce        : function() {},
        initialize      : function() {},
        progress        : function() {},
        success         : function() {},
        error           : function(index, file, message) { alert(message); },
        complete        : function() {},
        error_filesize  : "File exceeds 2GB. Please use an FTP client.",
        error_default   : "Please make sure the file is available.",
        error_server    : "Upload request failed.",
        error_login     : "Uploads require you to log in.",
        error_missing   : "No upload content available."
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
    var queue_running = false;
    var queue_stop = false;
  
    // element
    var el = null;
  
    // xml request element
    var xhr = null;
  
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
            
            // reset
            $(this).val('');
        });

        // drop event
        function drop(e)
        {
            // check if it's a file transfer
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
            if (queue_running)
                return;
  
            // backup queue index
            var current_index = queue_index;
  
            // add files to queue
            for (var i = 0; i < files.length; i++)
            {
                // check
                if(queue_length >= opts.maxfilenumber)
                    break;

                // new identifier
                var index = String(queue_index++);
  
                // add to queue
                queue[index] = files[i];
  
                // announce
                opts.announce(index, queue[index], '');
  
                // increase counter
                queue_length++;
            }
  
            // return
            return current_index;
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
            if (queue_length == 0 || queue_stop)
            {
                queue_stop = false;
                queue_running = false;
                opts.complete();
                return;
            } else
                queue_running = true;
  
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
  
            // collect file details
            var filesize = file.size;
            var filemode = file.mode;
  
            // identify maximum file size
            var maxfilesize = 1048576 * opts.maxfilesize;
  
            // check file size, unless it's an ftp file
            if (filesize < maxfilesize || file.mode == 'ftp')
            {
                // get parameters
                var data = opts.initialize(index, file);
  
                // validate
                if (data)
                    send(index, file, data);
                else
                    error(index, file, opts.error_missing);
            } else {
                // skip file
                error(index, file, opts.error_filesize);
            }
        }
  
        // send file
        function send (index, file, data)
        {
            // construct form data
            var formData = new FormData();
            for (var key in data) {
                formData.append(key, data[key]);
            }
  
            // check file size
            if (file.size > 0 && opts.paramname) {
                formData.append(opts.paramname, file, file.name);
            }
  
            // prepare request
            xhr = new XMLHttpRequest();
            xhr.open('POST', opts.url, true);
            xhr.setRequestHeader('Accept', 'application/json');
            xhr.setRequestHeader('Cache-Control', 'no-cache');
            xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
            
            // captures state changes
            xhr.onreadystatechange = function()
            {
                // check for request completed, server connection closed
                if (xhr.readyState != xhr.DONE)
                    return;
  
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
                    // format status
                    var text = xhr.statusText;
                    if (xhr.status == 403)
                        text = opts.error_login;
                    else if (xhr.status == 0)
                        text = opts.error_server;
                    else if (!text)
                        text = opts.error_default;
  
                    // request error
                    error(index, file, text + " (" + xhr.status + ")");
                } else
                    // parse response
                    success(index, file, response);
            }

            // prepare upload progress
            xhr.upload.index = index;
            xhr.upload.file = file;
            xhr.upload.addEventListener('progress', progress, false);

            // send request
            xhr.send(formData);
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
        function start()
        {
            if (!queue_running)
            {
                queue_running = true;
                process();
            }
        }
  
        // stop upload process
        function stop()
        {
            // request stop
            queue_stop = true;
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
            return window.File && window.FormData && window.XMLHttpRequest && window.FileList;
        }
  
        // export functions
        return {
            'select'        : select,
            'add'           : add,
            'remove'        : remove,
            'start'         : start,
            'stop'          : stop,
            'reset'         : reset,
            'configure'     : configure,
            'compatible'    : compatible
        };
    }
})(jQuery);

