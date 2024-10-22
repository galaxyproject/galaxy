/*
    galaxy upload utilities - requires FormData and XMLHttpRequest
*/
import { uploadPayload } from "@/utils/upload-payload.js";
import { sendPayload, uploadSubmit } from "@/utils/upload-submit.js";

export class UploadQueue {
    constructor(options) {
        this.opts = {
            announce: (d) => {},
            get: (d) => {},
            progress: (d, m) => {},
            success: (d, m) => {},
            warning: (d, m) => {},
            error: (d, m) => {
                console.error(m);
            },
            complete: () => {},
            multiple: true,
            ...options,
        };
        this.queue = new Map(); // items stored by key (referred to as index)
        this.nextIndex = 0;
        this.fileSet = new Set(); // Used for fast duplicate checking
        this.isRunning = false;
        this.isPaused = false;
    }

    // Add new files to upload queue
    add(files) {
        if (files && files.length && !this.isRunning) {
            // files is a FileList which is not an array, convert to iterate.
            Array.from(files).forEach((file) => {
                const fileSetKey = file.name + file.size; // Concat name and size to create a "file signature".
                if (file.mode === "new" || !this.fileSet.has(fileSetKey)) {
                    this.fileSet.add(fileSetKey);
                    const index = String(this.nextIndex++);
                    this.queue.set(index, file);
                    this.opts.announce(index, file);
                }
            });
        }
    }

    // Set options
    configure(options) {
        this.opts = Object.assign(this.opts, options);
        return this.opts;
    }

    // Remove file from queue and file set by index
    remove(index) {
        const file = this.queue.get(index);
        const fileSetKey = file.name + file.size;
        this.queue.delete(index) && this.fileSet.delete(fileSetKey);
    }

    // Remove all entries from queue
    reset() {
        this.queue.clear();
        this.fileSet.clear();
    }

    // Returns queue size
    get size() {
        return this.queue.size;
    }

    // Initiate upload process
    start() {
        if (!this.isRunning) {
            this.isRunning = true;
            this._processUrls();
            this._process();
        }
    }

    // Pause upload process
    stop() {
        this.isPaused = true;
    }

    // Process an upload, recursive
    _process() {
        if (this.size === 0 || this.isPaused) {
            this.isRunning = false;
            this.isPaused = false;
            this.opts.complete();
            return;
        } else {
            this.isRunning = true;
        }
        // Return index to first item in queue (in FIFO order).
        const index = this._processIndex();
        try {
            // Remove item from queue
            this.remove(index);
            // Collect upload request data
            const item = this.opts.get(index);
            if (!item.targetHistoryId) {
                throw new Error(`Missing target history for upload item [${index}] ${item.fileName}`);
            }
            const data = uploadPayload([item], item.targetHistoryId);
            // Initiate upload request
            this._processSubmit(index, data);
        } catch (e) {
            // Parse error message for failed upload item
            this.opts.error(index, String(e));
            // Continue queue
            this._process();
        }
    }

    // Submit remote files as single batch request per target history
    _processUrls() {
        const batchByHistory = {};
        for (const index of this.queue.keys()) {
            const model = this.opts.get(index);
            if (model.status === "queued" && model.fileMode === "url") {
                if (!model.targetHistoryId) {
                    throw new Error(`Missing target history for upload item [${index}] ${model.fileName}`);
                }
                if (!batchByHistory[model.targetHistoryId]) {
                    batchByHistory[model.targetHistoryId] = [];
                }
                batchByHistory[model.targetHistoryId].push({ index, ...model });
                this.remove(index);
            }
        }

        for (const historyId in batchByHistory) {
            const list = batchByHistory[historyId];
            try {
                const data = uploadPayload(list, historyId);
                sendPayload(data, {
                    success: (message) => {
                        list.forEach((model) => {
                            this.opts.success(model.index, message);
                        });
                    },
                    error: (message) => {
                        list.forEach((model) => {
                            this.opts.error(model.index, message);
                        });
                    },
                });
            } catch (e) {
                list.forEach((model) => {
                    this.opts.error(model.index, String(e));
                });
            }
        }
    }

    // Get next item to be processed
    _processIndex() {
        return this.queue.keys().next().value;
    }

    // Submit request data
    _processSubmit(index, data) {
        uploadSubmit({
            data: data,
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
