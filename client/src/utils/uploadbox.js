/*
    galaxy upload utilities - requires FormData and XMLHttpRequest
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

// Posts chunked files to the API.
export function submitUpload(config) {
    // set options
    const cnf = {
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
        ...config,
    };

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
}

(($) => {
    // add event properties
    jQuery.event.props.push("dataTransfer");

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
})(jQuery);

export class UploadQueue {
    constructor(options) {
        this.opts = {
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
            ...options,
        };
        this.queue = new Map(); // items stored by key (referred to as index)
        this.nextIndex = 0;
        this.fileSet = new Set(); // Used for fast duplicate checking
        this._initFlags();

        // Element
        this.uploadinput = options.$uploadBox.uploadinput({
            multiple: this.opts.multiple,
            onchange: (files) => {
                _.each(files, (file) => {
                    file.chunk_mode = true;
                });
                this.add(files);
            },
            ondragover: options.ondragover,
            ondragleave: options.ondragleave,
        });
    }

    _initFlags() {
        this.isRunning = false;
        this.isPaused = false;
    }

    // Open file browser for selection
    select() {
        this.uploadinput.dialog();
    }

    // Remove all entries from queue
    reset() {
        this.queue.clear();
        this.fileSet.clear();
    }

    // Initiate upload process
    start() {
        if (!this.isRunning) {
            this.isRunning = true;
            this._process();
        }
    }

    // Pause upload process
    stop() {
        this.isPaused = true;
    }

    // Set options
    configure(options) {
        this.opts = Object.assign(this.opts, options);
        return this.opts;
    }

    // Verify browser compatibility
    compatible() {
        return window.File && window.FormData && window.XMLHttpRequest && window.FileList;
    }

    // Add new files to upload queue
    add(files) {
        if (files && files.length && !this.isRunning) {
            files.forEach((file) => {
                const fileSetKey = file.name + file.size; // Concat name and size to create a "file signature".
                if (file.mode === "new" || !this.fileSet.has(fileSetKey)) {
                    this.fileSet.add(fileSetKey);
                    const index = this.nextIndex++;
                    this.queue.set(index, file);
                    this.opts.announce(index, file);
                }
            });
        }
    }

    // Remove file from queue
    remove(index) {
        // Removes the item identified by index.
        // Returns true if an item was removed, and false otherwise.
        return this.queue.delete(index);
    }

    get size() {
        return this.queue.size;
    }

    _firstItemIndex() {
        // Return index to first item in queue (in FIFO order).
        // If queue is empty, return undefined.
        return this.queue.keys().next().value;
    }

    // Process an upload, recursive
    _process() {
        if (this.size === 0 || this.isPaused) {
            this._initFlags();
            this.opts.complete();
            return;
        } else {
            this.isRunning = true;
        }
        const index = this._firstItemIndex();
        this.remove(index);
        this._submitUpload(index);
    }

    // create and submit data
    _submitUpload(index) {
        submitUpload({
            url: this.opts.url,
            data: this.opts.initialize(index),
            success: (message) => {
                this.opts.success(index, message);
                this._process();
            },
            warning: (message) => {
                this.opts.warning(index, message);
            },
            error: (message) => {
                this.opts.error(index, message);
                this._process();
            },
            progress: (percentage) => {
                this.opts.progress(index, percentage);
            },
        });
    }
}
