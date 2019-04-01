/*
    galaxy upload plugins - requires FormData and XMLHttpRequest
*/

import _ from "underscore";
import jQuery from "jquery";
import { getAppRoot } from "onload/loadConfig";

($ => {
    // add event properties
    jQuery.event.props.push("dataTransfer");

    /**
        xhr request helper
    */
    var _uploadrequest = config => {
        var cnf = $.extend(
            {
                error_default: "Please make sure the file is available.",
                error_server: "Upload request failed.",
                error_login: "Uploads require you to log in.",
                error_retry: "Waiting for server to resume..."
            },
            config
        );
        console.debug(cnf);
        var xhr = new XMLHttpRequest();
        xhr.open("POST", cnf.url, true);
        xhr.setRequestHeader("Cache-Control", "no-cache");
        xhr.setRequestHeader("X-Requested-With", "XMLHttpRequest");
        xhr.setRequestHeader("Accept", "application/json");
        xhr.onreadystatechange = () => {
            if (xhr.readyState == xhr.DONE) {
                if ([502, 0].indexOf(xhr.status) !== -1 && cnf.warning) {
                    cnf.warning(cnf.error_retry);
                } else if (xhr.status < 200 || xhr.status > 299) {
                    var text = xhr.statusText;
                    if (xhr.status == 403) {
                        text = cnf.error_login;
                    } else if (xhr.status == 0) {
                        text = cnf.error_server;
                    } else if (!text) {
                        text = cnf.error_default;
                    }
                    cnf.error(`${text} (${xhr.status})`);
                } else {
                    var response = null;
                    if (xhr.responseText) {
                        try {
                            response = jQuery.parseJSON(xhr.responseText);
                        } catch (e) {
                            response = xhr.responseText;
                        }
                    }
                    cnf.success(response);
                }
            }
        };
        xhr.upload.addEventListener("progress", cnf.progress, false);
        xhr.send(cnf.data);
    };

    /**
        Posts chunked files to the API.
    */
    $.uploadchunk = function(config) {
        // parse options
        var cnf = $.extend(
            {},
            {
                data: {},
                success: () => {},
                error: () => {},
                warning: () => {},
                progress: () => {},
                attempts: 70000,
                timeout: 5000,
                url: null,
                error_file: "File not provided.",
                error_attempt: "Maximum number of attempts reached.",
                error_tool: "Tool submission failed."
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
        var session_id = `${cnf.session.id}-${new Date().valueOf()}-${file.size}`;
        var chunk_size = cnf.session.chunk_upload_size;
        console.debug(`Starting chunked uploads [size=${chunk_size}].`);

        // chunk processing helper
        function process(start) {
            start = start || 0;
            var slicer = file.mozSlice || file.webkitSlice || file.slice;
            if (!slicer) {
                cnf.error("Browser does not support chunked uploads.");
                return;
            }
            var end = Math.min(start + chunk_size, file.size);
            var size = file.size;
            console.debug(`Submitting chunk at ${start} bytes...`);
            var form = new FormData();
            form.append("session_id", session_id);
            form.append("session_start", start);
            form.append("session_chunk", slicer.bind(file)(start, end));
            _uploadrequest({
                url: `${getAppRoot()}api/uploads`,
                data: form,
                success: upload_response => {
                    var new_start = start + chunk_size;
                    if (new_start < size) {
                        attempts = cnf.attempts;
                        process(new_start);
                    } else {
                        console.debug("Upload completed.");
                        data.payload.inputs = JSON.parse(data.payload.inputs);
                        data.payload.inputs["files_0|file_data"] = {
                            session_id: session_id,
                            name: file.name
                        };
                        data.payload.inputs = JSON.stringify(data.payload.inputs);
                        $.ajax({
                            url: `${getAppRoot()}api/tools`,
                            method: "POST",
                            data: data.payload,
                            success: tool_response => {
                                cnf.success(tool_response);
                            },
                            error: tool_response => {
                                var err_msg =
                                    tool_response && tool_response.responseJSON && tool_response.responseJSON.err_msg;
                                cnf.error(err_msg || cnf.error_tool);
                            }
                        });
                    }
                },
                warning: upload_response => {
                    if (--attempts > 0) {
                        console.debug("Retrying last chunk...");
                        cnf.warning(upload_response);
                        setTimeout(() => process(start), cnf.timeout);
                    } else {
                        console.debug(cnf.error_attempt);
                        cnf.error(cnf.error_attempt);
                    }
                },
                error: upload_response => {
                    console.debug(upload_response);
                    cnf.error(upload_response);
                },
                progress: e => {
                    if (e.lengthComputable) {
                        cnf.progress(Math.min(Math.round(((start + e.loaded) * 100) / file.size), 100));
                    }
                }
            });
        }

        // initiate processing queue for chunks
        process();
    };

    /**
        Posts multiple files without chunking to the API.
    */
    $.uploadpost = function(config) {
        var cnf = $.extend(
            {},
            {
                data: {},
                success: () => {},
                error: () => {},
                progress: () => {},
                url: null,
                maxfilesize: 1048576 * 2048,
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
        if (sizes > cnf.maxfilesize) {
            cnf.error(cnf.error_filesize);
            return;
        }

        // submit request
        _uploadrequest({
            url: cnf.url,
            data: form,
            success: cnf.success,
            error: cnf.error,
            progress: e => {
                if (e.lengthComputable) {
                    cnf.progress(Math.round((e.loaded * 100) / e.total));
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
                ondragover: () => {},
                ondragleave: () => {},
                onchange: () => {},
                multiple: false
            },
            options
        );

        // append hidden upload field
        var $input = $(`<input type="file" style="display: none" ${(opts.multiple && "multiple") || ""}/>`);
        el.append(
            $input.change(e => {
                opts.onchange(e.target.files);
                e.target.value = null;
            })
        );

        // drag/drop events
        let element = el.get(0);
        element.addEventListener("drop", e => {
            opts.ondragleave(e);
            if (e.dataTransfer) {
                opts.onchange(e.dataTransfer.files);
                e.preventDefault();
            }
        });
        element.addEventListener("dragover", e => {
            e.preventDefault();
            opts.ondragover(e);
        });
        element.addEventListener("dragleave", e => {
            e.stopPropagation();
            opts.ondragleave(e);
        });

        // exports
        return {
            dialog: () => {
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
                dragover: () => {},
                dragleave: () => {},
                announce: d => {},
                initialize: d => {},
                progress: (d, m) => {},
                success: (d, m) => {},
                warning: (d, m) => {},
                error: (d, m) => {
                    alert(m);
                },
                complete: () => {}
            },
            options
        );

        // file queue
        var queue = {};

        // session options
        var session = null;

        // queue index/length counter
        var queue_index = 0;
        var queue_length = 0;

        // indicates if queue is currently running
        var queue_running = false;
        var queue_stop = false;

        // element
        var uploadinput = $(this).uploadinput({
            multiple: true,
            onchange: files => {
                _.each(files, file => {
                    file.chunk_mode = true;
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
            var submitter = $.uploadpost;
            if (
                file.chunk_mode &&
                session &&
                session.id &&
                session.chunk_upload_size &&
                session.chunk_upload_size > 0
            ) {
                submitter = $.uploadchunk;
            }
            submitter({
                url: opts.url,
                data: opts.initialize(index),
                session: session,
                success: message => {
                    opts.success(index, message);
                    process();
                },
                warning: message => {
                    opts.warning(index, message);
                },
                error: message => {
                    opts.error(index, message);
                    process();
                },
                progress: percentage => {
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
        function start(_session) {
            session = _session;
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
