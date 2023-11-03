/*
    galaxy upload utilities - requires FormData and XMLHttpRequest
*/

import axios from "axios";
import { getAppRoot } from "onload/loadConfig";
import * as tus from "tus-js-client";

function buildFingerprint(cnf) {
    return async (file) => {
        return ["tus-br", file.name, file.type, file.size, file.lastModified, cnf.data.history_id].join("-");
    };
}

export function sendPayload(payload, cnf) {
    axios
        .post(`${getAppRoot()}api/tools/fetch`, payload)
        .then((response) => {
            cnf.success(response.data);
        })
        .catch((error) => {
            cnf.error(error.response?.data.err_msg || "Request failed.");
        });
}

function tusUpload(uploadables, index, data, tusEndpoint, cnf) {
    // uploadables must be an array of files or blobs with a name property
    const startTime = performance.now();
    const chunkSize = cnf.chunkSize;
    const uploadable = uploadables[index];
    if (!uploadable) {
        // We've uploaded all files or blobs; delete files from data and submit fetch payload
        delete data["files"];
        return sendPayload(data, cnf);
    }
    console.debug(`Starting chunked upload for ${uploadable.name} [chunkSize=${chunkSize}].`);
    const upload = new tus.Upload(uploadable, {
        endpoint: tusEndpoint,
        retryDelays: [0, 3000, 10000],
        fingerprint: buildFingerprint(cnf),
        chunkSize: chunkSize,
        storeFingerprintForResuming: false,
        onError: function (err) {
            const status = err.originalResponse?.getStatus();
            if (status == 403) {
                console.error(`Failed because of missing authorization: ${err}`);
                cnf.error(err);
            } else {
                // 🎵 Never gonna give you up 🎵
                console.log(`Failed because: ${err}\n, will retry in 10 seconds`);
                setTimeout(() => tusUploadStart(upload), 10000);
            }
        },
        onChunkComplete: function (chunkSize, bytesAccepted, bytesTotal) {
            const percentage = ((bytesAccepted / bytesTotal) * 100).toFixed(2);
            console.log(bytesAccepted, bytesTotal, percentage + "%");
            cnf.progress(Math.round(percentage));
        },
        onSuccess: function () {
            console.log(
                `Upload of ${uploadable.name} to ${upload.url} took ${(performance.now() - startTime) / 1000} seconds`
            );
            data[`files_${index}|file_data`] = {
                session_id: upload.url.split("/").at(-1),
                name: uploadable.name,
            };
            tusUpload(uploadables, index + 1, data, tusEndpoint, cnf);
        },
    });
    tusUploadStart(upload);
}

function tusUploadStart(upload) {
    // Check if there are any previous uploads to continue.
    upload.findPreviousUploads().then((previousUploads) => {
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
export function uploadSubmit(config) {
    // set options
    const cnf = {
        data: {},
        success: () => {},
        error: () => {},
        warning: () => {},
        progress: () => {},
        attempts: 70000,
        timeout: 5000,
        error_file: "File not provided.",
        error_attempt: "Maximum number of attempts reached.",
        error_tool: "Tool submission failed.",
        chunkSize: 10485760,
        isComposite: false,
        ...config,
    };
    // initial validation
    var data = cnf.data;
    if (data.error_message) {
        cnf.error(data.error_message);
        return;
    }
    // execute upload
    const tusEndpoint = `${getAppRoot()}api/upload/resumable_upload/`;
    if (data.files.length || cnf.isComposite) {
        return tusUpload(data.files, 0, data, tusEndpoint, cnf);
    } else {
        if (data.targets.length && data.targets[0].elements.length) {
            const pasted = data.targets[0].elements[0];
            if (pasted.src == "url") {
                return sendPayload(data, cnf);
            } else {
                const blob = new Blob([pasted.paste_content]);
                blob.name = data.targets[0].elements[0].name || "default";
                return tusUpload([blob], 0, data, tusEndpoint, cnf);
            }
        }
    }
}
