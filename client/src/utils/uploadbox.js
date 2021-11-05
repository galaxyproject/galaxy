/*
    galaxy upload plugins - requires FormData and XMLHttpRequest
*/

import _ from "underscore";
import jQuery from "jquery";
import { getAppRoot } from "onload/loadConfig";
import * as tus from "tus-js-client";
import axios from "axios";

function submitPayload(payload, cnf) {
    axios
        .post(`${getAppRoot()}api/tools/fetch`, payload)
        .then((response) => {
            cnf.success(response.data);
        })
        .catch((error) => {
            cnf.error(error.response.data.err_msg);
        });
}

function tusUpload(data, index, tusEndpoint, cnf) {
    const startTime = performance.now();
    const chunkSize = cnf.chunkSize;
    const file = data.files[index];
    if (!file) {
        // We've uploaded all files, delete files from data and submit fetch payload
        delete data["files"];
        return submitPayload(data, cnf);
    }
    console.debug(`Starting chunked upload for ${file.name} [chunkSize=${chunkSize}].`);
    const upload = new tus.Upload(file, {
        endpoint: tusEndpoint,
        chunkSize: chunkSize,
        metadata: data.payload,
        onError: function (error) {
            console.log("Failed because: " + error);
            cnf.error(error);
        },
        onProgress: function (bytesUploaded, bytesTotal) {
            var percentage = ((bytesUploaded / bytesTotal) * 100).toFixed(2);
            console.log(bytesUploaded, bytesTotal, percentage + "%");
            cnf.progress(percentage);
        },
        onSuccess: function () {
            console.log(
                `Upload of ${upload.file.name} to ${upload.url} took ${(performance.now() - startTime) / 1000} seconds`
            );
            data[`files_${index}|file_data`] = {
                session_id: upload.url.split("/").at(-1),
                name: upload.file.name,
            };
            tusUpload(data, index + 1, tusEndpoint, cnf);
        },
    });
    // Check if there are any previous uploads to continue.
    upload.findPreviousUploads().then(function (previousUploads) {
        // Found previous uploads so we select the first one.
        if (previousUploads.length) {
            console.log("previous Upload", previousUploads);
            upload.resumeFromPreviousUpload(previousUploads[0]);
        }

        // Start the upload
        upload.start();
    });
}

(($) => {
    // add event properties
    jQuery.event.props.push("dataTransfer");

    /**
        Posts chunked files to the API.
    */
    $.uploadchunk = function (config) {
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
                error_tool: "Tool submission failed.",
                chunkSize: 10485760,
            },
            config
        );

        // initial validation
        var data = cnf.data;
        if (data.error_message) {
            cnf.error(data.error_message);
            return;
        }
        if (!data.files.length) {
            // No files attached, don't need to use TUS uploader
            return submitPayload(data, cnf);
        }
        const tusEndpoint = `${getAppRoot()}api/upload/resumable_upload/`;
        tusUpload(data, 0, tusEndpoint, cnf);
    };

    /**
        Handles the upload events drag/drop etc.
    */
    $.fn.uploadinput = function (options) {
        // initialize
        var el = this;
        var opts = $.extend(
            {},
            {
                ondragover: () => {},
                ondragleave: () => {},
                onchange: () => {},
                multiple: false,
            },
            options
        );

        // append hidden upload field
        var $input = $(`<input type="file" style="display: none" ${(opts.multiple && "multiple") || ""}/>`);
        el.append(
            $input.change((e) => {
                opts.onchange(e.target.files);
                e.target.value = null;
            })
        );

        // drag/drop events
        const element = el.get(0);
        element.addEventListener("drop", (e) => {
            opts.ondragleave(e);
            if (e.dataTransfer) {
                opts.onchange(e.dataTransfer.files);
                e.preventDefault();
            }
        });
        element.addEventListener("dragover", (e) => {
            e.preventDefault();
            opts.ondragover(e);
        });
        element.addEventListener("dragleave", (e) => {
            e.stopPropagation();
            opts.ondragleave(e);
        });

        // exports
        return {
            dialog: () => {
                $input.trigger("click");
            },
        };
    };

    /**
        Handles the upload queue and events such as drag/drop etc.
    */
    $.fn.uploadbox = function (options) {
        // parse options
        var opts = $.extend(
            {},
            {
                dragover: () => {},
                dragleave: () => {},
                announce: (d) => {},
                initialize: (d) => {},
                progress: (d, m) => {},
                success: (d, m) => {},
                warning: (d, m) => {},
                error: (d, m) => {
                    alert(m);
                },
                complete: () => {},
                multiple: true,
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
            multiple: opts.multiple,
            onchange: (files) => {
                _.each(files, (file) => {
                    file.chunk_mode = true;
                });
                add(files);
            },
            ondragover: options.ondragover,
            ondragleave: options.ondragleave,
        });

        // add new files to upload queue
        function add(files) {
            if (files && files.length && !queue_running) {
                var index = undefined;
                _.each(files, (file, key) => {
                    if (
                        file.mode !== "new" &&
                        _.filter(queue, (f) => f.name === file.name && f.size === file.size).length
                    ) {
                        file.duplicate = true;
                    }
                });
                _.each(files, (file) => {
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
            for (const key in queue) {
                index = key;
                break;
            }

            // remove from queue
            remove(index);

            // create and submit data
            var submitter = $.uploadchunk;
            var requestData = opts.initialize(index);

            submitter({
                url: opts.initUrl(index),
                data: requestData,
                success: (message) => {
                    opts.success(index, message);
                    process();
                },
                warning: (message) => {
                    opts.warning(index, message);
                },
                error: (message) => {
                    opts.error(index, message);
                    process();
                },
                progress: (percentage) => {
                    opts.progress(index, percentage);
                },
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
            compatible: compatible,
        };
    };
})(jQuery);
