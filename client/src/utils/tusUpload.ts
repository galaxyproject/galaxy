import * as tus from "tus-js-client";

/**
 * Represents a file stream for upload.
 * Used when uploading content from ReadableStream sources (e.g., ZIP file entries).
 */
export interface FileStream {
    name: string;
    size: number;
    type?: string;
    lastModified: number;
    stream: ReadableStream<Uint8Array>;
    isStream: true;
}

/**
 * Represents a Blob with a name property.
 * TypeScript doesn't natively support extending Blob with name,
 * so we use this interface for type safety.
 */
export interface NamedBlob extends Blob {
    name: string;
}

/**
 * Union type for all uploadable file types.
 */
export type UploadableFile = File | NamedBlob | FileStream;

/**
 * Options for creating a TUS upload.
 */
export interface TusUploadOptions {
    /** The file to upload */
    file: UploadableFile;
    /** The TUS upload endpoint URL */
    endpoint: string;
    /** The Galaxy history ID for fingerprinting */
    historyId: string;
    /** Size of upload chunks in bytes */
    chunkSize: number;
    /** Called with upload progress percentage (0-100) */
    onProgress: (percentage: number) => void;
    /** Called when an error occurs */
    onError: (error: Error) => void;
}

/**
 * Result of a successful TUS upload.
 */
export interface TusUploadResult {
    /** The session ID from the completed upload */
    sessionId: string;
    /** The name of the uploaded file */
    fileName: string;
}

/**
 * Builds a fingerprint function for TUS upload resumption.
 * The fingerprint uniquely identifies an upload and allows it to be resumed.
 *
 * @param file - The file being uploaded
 * @param historyId - The Galaxy history ID
 * @returns A function that returns the fingerprint string
 */
export function buildUploadFingerprint(file: UploadableFile, historyId: string) {
    return async (): Promise<string> => {
        // For FileStream objects, we need to use the metadata from the original file
        // since the ReadableStream reader doesn't have this information
        const fingerprint = [
            "tus-br",
            file.name,
            "type" in file ? file.type : undefined,
            file.size,
            "lastModified" in file ? file.lastModified : undefined,
            historyId,
        ].join("-");

        return fingerprint;
    };
}

/**
 * Starts a TUS upload, checking for previous uploads to resume.
 *
 * @param upload - The TUS Upload instance
 */
async function startTusUpload(upload: tus.Upload): Promise<void> {
    // Check if there are any previous uploads to continue
    const previousUploads = await upload.findPreviousUploads();

    // Found previous uploads so we select the first one
    if (previousUploads.length && previousUploads[0]) {
        console.debug("previous Upload", previousUploads);
        upload.resumeFromPreviousUpload(previousUploads[0]);
    }

    // Start the upload
    upload.start();
}

/**
 * Creates and executes a TUS upload.
 *
 * @param options - Upload configuration options
 * @returns Promise resolving to upload result with session ID and file name
 * @throws Error if upload fails with 403 (authorization) or other unrecoverable errors
 */
export async function createTusUpload(options: TusUploadOptions): Promise<TusUploadResult> {
    const { file, endpoint, historyId, chunkSize, onProgress, onError } = options;
    const startTime = performance.now();

    return new Promise((resolve, reject) => {
        console.debug(`Starting chunked upload for ${file.name} [chunkSize=${chunkSize}].`);

        // Determine the upload input based on file type
        // For FileStream, extract the reader; otherwise use the file/blob directly
        const uploadInput = "isStream" in file && file.isStream ? file.stream.getReader() : (file as File | Blob);

        const upload = new tus.Upload(uploadInput, {
            endpoint,
            retryDelays: [0, 3000, 10000],
            fingerprint: buildUploadFingerprint(file, historyId),
            chunkSize,
            uploadSize: file.size,
            storeFingerprintForResuming: false,
            onError: (err: Error) => {
                const status = (
                    err as Error & { originalResponse?: { getStatus: () => number } }
                ).originalResponse?.getStatus();
                if (status === 403) {
                    console.error(`Failed because of missing authorization: ${err}`);
                    onError(err);
                    reject(err);
                } else {
                    // 🎵 Never gonna give you up 🎵
                    console.log(`Failed because: ${err}\n, will retry in 10 seconds`);
                    setTimeout(() => startTusUpload(upload), 10000);
                }
            },
            onProgress: (bytesUploaded: number, bytesTotal: number) => {
                const percentage = ((bytesUploaded / bytesTotal) * 100).toFixed(2);
                console.log(bytesUploaded, bytesTotal, percentage + "%");
                onProgress(Math.round(parseFloat(percentage)));
            },
            onSuccess: () => {
                const uploadTimeSeconds = (performance.now() - startTime) / 1000;
                console.log(`Upload of ${file.name} to ${upload.url} took ${uploadTimeSeconds} seconds`);

                const sessionId = upload.url?.split("/").pop();
                if (!sessionId) {
                    const error = new Error("No session ID received from upload");
                    onError(error);
                    reject(error);
                    return;
                }

                resolve({
                    sessionId,
                    fileName: file.name,
                });
            },
        });

        startTusUpload(upload).catch(reject);
    });
}
