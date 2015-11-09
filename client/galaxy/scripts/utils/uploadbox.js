/*
    galaxy upload plugins - requires FormData and XMLHttpRequest
*/
;(function($){
    // add event properties
    jQuery.event.props.push("dataTransfer");

    /**
        Posts file data to the API
    */
    $.uploadpost = function (config) {
        // parse options
        var cnf = $.extend({}, {
            data            : {},
            success         : function() {},
            error           : function() {},
            progress        : function() {},
            url             : null,
            maxfilesize     : 2048,
            error_filesize  : 'File exceeds 2GB. Please use an FTP client.',
            error_default   : 'Please make sure the file is available.',
            error_server    : 'Upload request failed.',
            error_login     : 'Uploads require you to log in.'
        }, config);

        // link data
        var data = cnf.data;

        // check errors
        if (data.error_message) {
            cnf.error(data.error_message);
            return;
        }

        // construct form data
        var form = new FormData();
        for (var key in data.payload) {
            form.append(key, data.payload[key]);
        }

        // add files to submission
        var sizes = 0;
        for (var key in data.files) {
            var d = data.files[key];
            form.append(d.name, d.file, d.file.name);
            sizes += d.file.size;
        }

        // check file size, unless it's an ftp file
        if (sizes > 1048576 * cnf.maxfilesize) {
            cnf.error(cnf.error_filesize);
            return;
        }

        // prepare request
        xhr = new XMLHttpRequest();
        xhr.open('POST', cnf.url, true);
        xhr.setRequestHeader('Accept', 'application/json');
        xhr.setRequestHeader('Cache-Control', 'no-cache');
        xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');

        // captures state changes
        xhr.onreadystatechange = function() {
            // check for request completed, server connection closed
            if (xhr.readyState == xhr.DONE) {
                // parse response
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
                    var text = xhr.statusText;
                    if (xhr.status == 403) {
                        text = cnf.error_login;
                    } else if (xhr.status == 0) {
                        text = cnf.error_server;
                    } else if (!text) {
                        text = cnf.error_default;
                    }
                    cnf.error(text + ' (' + xhr.status + ')');
                } else {
                    cnf.success(response);
                }
            }
        }

        // prepare upload progress
        xhr.upload.addEventListener('progress', function(e) {
            if (e.lengthComputable) {
                cnf.progress(Math.round((e.loaded * 100) / e.total));
            }
        }, false);

        // send request
        Galaxy.emit.debug('uploadbox::uploadpost()', 'Posting following data.', cnf);
        xhr.send(form);
    }

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
            opts.ondragleave(e);
            if(e.dataTransfer) {
                opts.onchange(e.dataTransfer.files);
                e.preventDefault();
            }
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
        // parse options
        var opts = $.extend({}, {
            dragover        : function() {},
            dragleave       : function() {},
            announce        : function(d) {},
            initialize      : function(d) {},
            progress        : function(d, m) {},
            success         : function(d, m) {},
            error           : function(d, m) { alert(m); },
            complete        : function() {}
        }, options);

        // file queue
        var queue = {};

        // queue index/length counter
        var queue_index = 0;
        var queue_length = 0;

        // indicates if queue is currently running
        var queue_running = false;
        var queue_stop = false;

        // element
        var uploadinput = $(this).uploadinput({
            multiple    : true,
            onchange    : function(files) { add(files); },
            ondragover  : options.ondragover,
            ondragleave : options.ondragleave
        });

        // add new files to upload queue
        function add(files) {
            if (files && files.length && !queue_running) {
                var current_index = queue_index;
                for (var i = 0; i < files.length; i++) {
                    var index = String(queue_index++);
                    queue[index] = files[i];
                    opts.announce(index, queue[index]);
                    queue_length++;
                }
                return current_index;
            }
        }

        // remove file from queue
        function remove(index) {
            if (queue[index]) {
                delete queue[index];
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

            // create and submit data
            $.uploadpost({
                url      : opts.url,
                data     : opts.initialize(index),
                success  : function(message) { opts.success(index, message); process();},
                error    : function(message) { opts.error(index, message); process();},
                progress : function(percentage) { opts.progress(index, percentage); }
            });
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
            for (index in queue) {
                remove(index);
            }
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
            queue_stop = true;
        }

        // set options
        function configure(options) {
            opts = $.extend({}, opts, options);
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

