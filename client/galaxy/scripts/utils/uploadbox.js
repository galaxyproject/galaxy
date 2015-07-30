/*
    galaxy upload plugins - requires FormData and XMLHttpRequest
*/
;(function($){
    // add event properties
    jQuery.event.props.push("dataTransfer");

    /**
        Handles the upload events drag/drop etc.
    */
    $.fn.uploadinput = function(options) {
        // initialize
        var el = this;
        var opts = $.extend({}, {
            ondragover  : function() {},
            ondragleave : function() {},
            onchange    : function() {},
            multiple    : false
        }, options);

        // append hidden upload field
        var $input = $('<input type="file" style="display: none" ' + (opts.multiple && 'multiple' || '') + '/>');
        el.append($input).change(function (e) {
            opts.onchange(e.target.files);
            $(this).val('');
        });

        // drag/drop events
        el.on('drop', function (e) {
            if(e.dataTransfer) {
                opts.onchange(e.dataTransfer.files);
                e.preventDefault();
            }
            return false;
        });
        el.on('dragover',  function (e) {
            e.preventDefault();
            opts.ondragover(e);
        });
        el.on('dragleave', function (e) {
            e.stopPropagation();
            opts.ondragleave(e);
        });

        // exports
        return {
            dialog: function () {
                $input.trigger('click');
            }
        }
    }

    /**
        Handles the upload queue and events such as drag/drop etc.
    */
    $.fn.uploadbox = function(options) {

        // default options
        var default_opts = {
            url             : '',
            paramname       : 'content',
            maxfilesize     : 2048,
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

        // file queue
        var queue = {};

        // queue index counter
        var queue_index = 0;

        // queue length
        var queue_length = 0;

        // indicates if queue is currently running
        var queue_running = false;
        var queue_stop = false;

        // xml request element
        var xhr = null;

        // parse options
        var opts = $.extend({}, default_opts, options);

        // element
        var uploadinput = $(this).uploadinput({
            multiple    : true,
            onchange    : function(files) {
                add(files);
            }
        });

        // progress
        function progress(e) {
            // get percentage
            if (e.lengthComputable) {
                opts.progress(this.index, this.file, Math.round((e.loaded * 100) / e.total));
            }
        }

        // respond to an upload request
        function add(files) {
            // only allow adding file if current batch is complete
            if (queue_running) {
                return;
            }

            // backup queue index
            var current_index = queue_index;

            // add files to queue
            for (var i = 0; i < files.length; i++) {
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
        function remove(index) {
            if (queue[index]) {
                // remove from queue
                delete queue[index];

                // update counter
                queue_length--;
            }
        }

        // process an upload, recursive
        function process() {
            // validate
            if (queue_length == 0 || queue_stop) {
                queue_stop = false;
                queue_running = false;
                opts.complete();
                return;
            } else {
                queue_running = true;
            }

            // get an identifier from the queue
            var index = -1;
            for (var key in queue) {
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
            if (filesize < maxfilesize || file.mode == 'ftp') {
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
        function send (index, file, data) {
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
            xhr.onreadystatechange = function() {
                // check for request completed, server connection closed
                if (xhr.readyState != xhr.DONE) {
                    return;
                }

                // retrieve response
                var response = null;
                if (xhr.responseText) {
                    try {
                        response = jQuery.parseJSON(xhr.responseText);
                    } catch (e) {
                        response = xhr.responseText;
                    }
                }

                // pass any error to the error option
                if (xhr.status < 200 || xhr.status > 299) {
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
                } else {
                    // parse response
                    success(index, file, response);
                }
            }

            // prepare upload progress
            xhr.upload.index = index;
            xhr.upload.file = file;
            xhr.upload.addEventListener('progress', progress, false);

            // send request
            xhr.send(formData);
        }

        // success
        function success (index, file, msg) {
            // parse message
            opts.success(index, file, msg);
  
            // restart process after success
            process();
        }

        // error
        function error (index, file, err) {
            // parse error
            opts.error(index, file, err);

            // restart process after error
            process();
        }

        /*
            public interface
        */

        // open file browser for selection
        function select() {
            uploadinput.dialog();
        }

        // remove all entries from queue
        function reset(index) {
            for (index in queue)
                remove(index);
        }

        // initiate upload process
        function start() {
            if (!queue_running) {
                queue_running = true;
                process();
            }
        }

        // stop upload process
        function stop() {
            // request stop
            queue_stop = true;
        }

        // set options
        function configure(options) {
            // update current configuration
            opts = $.extend({}, opts, options);

            // return new configuration
            return opts;
        }

        // verify browser compatibility
        function compatible() {
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

