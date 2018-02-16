/*
    galaxy upload plugins - requires FormData and XMLHttpRequest
*/
($ => {
    // add event properties
    jQuery.event.props.push("dataTransfer");

    /**
        Post helper, sends multiform data to the API
    */
    var uploadsubmit = config => {
        var cnf = $.extend({
            error_default: "Please make sure the file is available.",
            error_server: "Upload request failed.",
            error_login: "Uploads require you to log in."
        }, config);
        console.debug(cnf);
        var xhr = new XMLHttpRequest();
        xhr.open("POST", cnf.url, true);
        xhr.setRequestHeader("Cache-Control", "no-cache");
        xhr.setRequestHeader("X-Requested-With", "XMLHttpRequest");
        xhr.setRequestHeader("X-Content-Range", "bytes " + cnf.content_range);
        xhr.setRequestHeader("Session-ID", cnf.session_id);
        xhr.setRequestHeader("Content-Type", "application/octet-stream");
        xhr.setRequestHeader("Content-Disposition", 'attachment; filename="big.TXT"');
        xhr.onreadystatechange = () => {
            if (xhr.readyState == xhr.DONE) {
                var response = null;
                var extra_info = "";
                if (xhr.responseText) {
                    try {
                        response = jQuery.parseJSON(xhr.responseText);
                        extra_info = response.err_msg;
                    } catch (e) {
                        response = xhr.responseText;
                        extra_info = response;
                    }
                }
                if (xhr.status < 200 || xhr.status > 299) {
                    var text = xhr.statusText;
                    if (xhr.status == 403) {
                        text = cnf.error_login;
                    } else if (xhr.status == 0) {
                        text = cnf.error_server;
                    } else if (!text) {
                        text = cnf.error_default;
                    }
                    cnf.error(`${text} (${xhr.status}). ${extra_info}`);
                } else {
                    cnf.success(response);
                }
            }
        };
        xhr.upload.addEventListener("progress", cnf.progress, false);
        xhr.send(cnf.form);
    }

    /**
        Posts chunked files to the API.
    */
    $.uploadchunk = config => {
        // parse options
        var cnf = $.extend(
            {},
            {
                data: {},
                success: function() {},
                error: function() {},
                progress: function() {},
                chunksize: 2,
                attempts: 5,
                url: null,
                error_file: "File not provied.",
                error_attempt: "Maximum number of attempts reached."
            },
            config
        );

        // initial validation
        var data = cnf.data;
        if (data.error_message) {
            cnf.error(data.error_message);
            return;
        }
        var file_data = data.files && data.files[0];
        if (!file_data) {
            cnf.error(cnf.error_file);
            return;
        }
        var file = file_data.file;
        var attempts = cnf.attempts;

        // submission helper
        function send(start, success, error) {
            // access slice caller
            var slicer = file.mozSlice || file.webkitSlice || file.slice;
            if (!slicer) {
                cnf.error("Browser does not support chunked uploads.");
                return;
            }

            // build form data
            var end = Math.min(start + cnf.chunksize, file.size);
            var file_chunk = slicer.bind(file)(start, end);
            // approximated progress handler, ignores payloads other than file
            uploadsubmit({
                url: "/_upload_chunk",
                file: file_chunk,
                session_id: 1111215056,
                content_range: start + "-" + (end - 1) + "/" + file.size,
                success: success,
                error: success,
                progress: e => {
                    if (e.lengthComputable) {
                        cnf.progress(Math.min(Math.round((start + e.loaded) * 100 / file.size), 100));
                    }
                }
            });
        }

        // chunk processing helper
        function process(start) {
            var start = start || 0;
            var size = file.size;
            console.debug("Submitting chunk at " + start + " bytes...");
            send(start, response => {
                var new_start = start + cnf.chunksize;
                if (new_start < size) {
                    // send next chunk
                    attempts = cnf.attempts;
                    process(new_start);
                } else {
                    // submission complete show success
                    console.debug("Success.");
                    cnf.success(response);
                }
            }, response => {
                // retry or show error
                if (--attempts > 0) {
                    console.debug("Retrying...");
                    process(start);
                } else {
                    console.debug(cnf.error_attempt);
                    cnf.error(cnf.error_attempt);
                }
            });
        }

        // initiate processing queue for chunks
        process();
    };

    /**
        Posts multiple files without chunking to the API.
    */
    $.uploadpost = config => {
        var cnf = $.extend(
            {},
            {
                data: {},
                success: function() {},
                error: function() {},
                progress: function() {},
                url: null,
                maxfilesize: 2048,
                error_filesize: "File exceeds 2GB. Please use a FTP client."
            },
            config
        );
        var data = cnf.data;
        if (data.error_message) {
            cnf.error(data.error_message);
            return;
        }

        // construct form data
        var form = new FormData();
        for (let key in data.payload) {
            form.append(key, data.payload[key]);
        }

        // add files to submission
        var sizes = 0;
        for (let key in data.files) {
            var d = data.files[key];
            form.append(d.name, d.file, d.file.name);
            sizes += d.file.size;
        }

        // check file size, unless it's an ftp file
        if (sizes > 1048576 * cnf.maxfilesize) {
            cnf.error(cnf.error_filesize);
            return;
        }

        // submit request
        uploadsubmit({
            url: cnf.url,
            form: form,
            success: cnf.success,
            error: cnf.error,
            progress: e => {
                if (e.lengthComputable) {
                    cnf.progress(Math.round(e.loaded * 100 / e.total));
                }
            }
        });
    };

    /**
        Handles the upload events drag/drop etc.
    */
    $.fn.uploadinput = function(options) {
        // initialize
        var el = this;
        var opts = $.extend(
            {},
            {
                ondragover: function() {},
                ondragleave: function() {},
                onchange: function() {},
                multiple: false
            },
            options
        );

        // append hidden upload field
        var $input = $(`<input type="file" style="display: none" ${(opts.multiple && "multiple") || ""}/>`);
        el.append(
            $input.change(function(e) {
                opts.onchange(e.target.files);
                $(this).val("");
            })
        );

        // drag/drop events
        el.on("drop", e => {
            opts.ondragleave(e);
            if (e.dataTransfer) {
                opts.onchange(e.dataTransfer.files);
                e.preventDefault();
            }
        });
        el.on("dragover", e => {
            e.preventDefault();
            opts.ondragover(e);
        });
        el.on("dragleave", e => {
            e.stopPropagation();
            opts.ondragleave(e);
        });

        // exports
        return {
            dialog: function() {
                $input.trigger("click");
            }
        };
    };

    /**
        Handles the upload queue and events such as drag/drop etc.
    */
    $.fn.uploadbox = function(options) {
        // parse options
        var opts = $.extend(
            {},
            {
                dragover: function() {},
                dragleave: function() {},
                announce: function(d) {},
                initialize: function(d) {},
                progress: function(d, m) {},
                success: function(d, m) {},
                error: function(d, m) {
                    alert(m);
                },
                complete: function() {}
            },
            options
        );

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
            multiple: true,
            onchange: function(files) {
                _.each(files, file => {
                    file.chunkmode = true;
                });
                add(files);
            },
            ondragover: options.ondragover,
            ondragleave: options.ondragleave
        });

        // add new files to upload queue
        function add(files) {
            if (files && files.length && !queue_running) {
                var index = undefined;
                _.each(files, (file, key) => {
                    if (
                        file.mode !== "new" &&
                        _.filter(queue, f => f.name === file.name && f.size === file.size).length
                    ) {
                        file.duplicate = true;
                    }
                });
                _.each(files, file => {
                    if (!file.duplicate) {
                        index = String(queue_index++);
                        queue[index] = file;
                        opts.announce(index, queue[index]);
                        queue_length++;
                    }
                });
                return index;
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
            for (let key in queue) {
                index = key;
                break;
            }

            // get current file from queue
            var file = queue[index];

            // remove from queue
            remove(index);

            // create and submit data
            var submitter = file.chunkmode ? $.uploadchunk : $.uploadpost;
            submitter({
                url: opts.url,
                data: opts.initialize(index),
                success: function(message) {
                    opts.success(index, message);
                    process();
                },
                error: function(message) {
                    opts.error(index, message);
                    process();
                },
                progress: function(percentage) {
                    opts.progress(index, percentage);
                }
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
            select: select,
            add: add,
            remove: remove,
            start: start,
            stop: stop,
            reset: reset,
            configure: configure,
            compatible: compatible
        };
    };
})(jQuery);
