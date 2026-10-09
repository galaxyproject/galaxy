import { Upload } from "tus-js-client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ensureDefined } from "./assertions";
import { buildUploadFingerprint, createTusUpload, type FileStream, type UploadableFile } from "./tusUpload";

vi.mock("tus-js-client", () => ({ Upload: vi.fn() }));

const uploadConstructor = vi.mocked(Upload);
type UploadOptions = ConstructorParameters<typeof Upload>[1];
type PreviousUploads = Awaited<ReturnType<Upload["findPreviousUploads"]>>;

class FakeUpload implements Upload {
    file: Upload["file"] = new Blob();
    options: UploadOptions = {};
    url: string | null = null;
    findPreviousUploads = vi.fn<Upload["findPreviousUploads"]>().mockResolvedValue([]);
    resumeFromPreviousUpload = vi.fn<Upload["resumeFromPreviousUpload"]>();
    start = vi.fn<Upload["start"]>();
    abort = vi.fn<Upload["abort"]>().mockResolvedValue(undefined);
}

describe("buildUploadFingerprint", () => {
    it("includes the File's name, MIME type, size, modification time, and history", async () => {
        const file = new File(["content"], "test.txt", { type: "text/plain", lastModified: 1234567890 });

        expect(await buildUploadFingerprint(file, "hist123")()).toBe("tus-br-test.txt-text/plain-7-1234567890-hist123");
    });

    it("leaves modification time empty for a named Blob", async () => {
        const blob = Object.assign(new Blob(["content"], { type: "text/plain" }), { name: "blob.txt" });

        expect(await buildUploadFingerprint(blob, "hist456")()).toBe("tus-br-blob.txt-text/plain-7--hist456");
    });

    it("uses FileStream metadata rather than the stream reader", async () => {
        const fileStream: FileStream = {
            name: "stream.txt",
            size: 100,
            type: "text/plain",
            lastModified: 9876543210,
            stream: new ReadableStream(),
            isStream: true,
        };

        expect(await buildUploadFingerprint(fileStream, "hist789")()).toBe(
            "tus-br-stream.txt-text/plain-100-9876543210-hist789",
        );
    });

    it("leaves missing MIME type and modification time empty", async () => {
        const blob = Object.assign(new Blob(["test"]), { name: "test" });

        expect(await buildUploadFingerprint(blob, "hist000")()).toBe("tus-br-test--4--hist000");
    });
});

describe("createTusUpload", () => {
    let upload: FakeUpload;

    beforeEach(() => {
        upload = new FakeUpload();
        uploadConstructor.mockReset();
        uploadConstructor.mockImplementation(function (input, options) {
            upload.file = input;
            upload.options = options;
            return upload;
        });
    });

    afterEach(() => {
        vi.restoreAllMocks();
        vi.useRealTimers();
    });

    function beginUpload(file: UploadableFile, signal?: AbortSignal) {
        const onProgress = vi.fn();
        const onError = vi.fn();
        const result = createTusUpload({
            file,
            endpoint: "http://localhost/upload",
            historyId: "hist123",
            chunkSize: 1024,
            onProgress,
            onError,
            signal,
        });
        const callbacks = {
            onProgress: ensureDefined(upload.options.onProgress),
            onError: ensureDefined(upload.options.onError),
            onSuccess: ensureDefined(upload.options.onSuccess),
        };
        return { result, onProgress, onError, callbacks };
    }

    async function startUpload(file: UploadableFile) {
        const pending = beginUpload(file);
        await vi.waitFor(() => expect(upload.start).toHaveBeenCalledOnce());
        return pending;
    }

    it("resolves with the session ID and file name after a successful upload", async () => {
        const file = new File(["content"], "upload.txt", { type: "text/plain" });
        const { result, onError, callbacks } = await startUpload(file);

        upload.url = "http://localhost/upload/session123";
        callbacks.onSuccess();

        expect(await result).toEqual({ sessionId: "session123", fileName: "upload.txt" });
        expect(upload.start).toHaveBeenCalledOnce();
        expect(onError).not.toHaveBeenCalled();
    });

    it("reports uploaded percentages rounded to the nearest integer", async () => {
        const { result, onProgress, callbacks } = await startUpload(new File(["content"], "progress.txt"));

        callbacks.onProgress(50, 100);
        expect(onProgress).toHaveBeenLastCalledWith(50);
        callbacks.onProgress(33, 100);
        expect(onProgress).toHaveBeenLastCalledWith(33);
        callbacks.onProgress(66.66, 100);
        expect(onProgress).toHaveBeenLastCalledWith(67);

        upload.url = "http://localhost/upload/progress-session";
        callbacks.onSuccess();
        await result;
    });

    it("reports and rejects a 403 authorization error", async () => {
        const consoleError = vi.spyOn(console, "error").mockImplementation(() => {});
        const { result, onError, callbacks } = await startUpload(new File(["content"], "forbidden.txt"));
        const error = Object.assign(new Error("Forbidden"), { originalResponse: { getStatus: () => 403 } });
        const rejection = expect(result).rejects.toThrow("Forbidden");

        callbacks.onError(error);

        await rejection;
        expect(onError).toHaveBeenCalledWith(error);
        expect(consoleError).toHaveBeenCalled();
    });

    it("restarts ten seconds after a non-403 error and can then succeed", async () => {
        vi.useFakeTimers();
        const { result, onError, callbacks } = await startUpload(new File(["content"], "retry.txt"));
        const error = Object.assign(new Error("Network error"), { originalResponse: { getStatus: () => 500 } });

        callbacks.onError(error);
        expect(onError).not.toHaveBeenCalled();
        await vi.advanceTimersByTimeAsync(9999);
        expect(upload.start).toHaveBeenCalledTimes(1);
        await vi.advanceTimersByTimeAsync(1);
        expect(upload.start).toHaveBeenCalledTimes(2);

        upload.url = "http://localhost/upload/session456";
        callbacks.onSuccess();

        expect((await result).sessionId).toBe("session456");
    });

    it("resumes the previous upload before starting", async () => {
        const previousUpload = {
            uploadUrl: "http://localhost/upload/previous123",
            size: 7,
            metadata: {},
            creationTime: "2026-01-01T00:00:00Z",
        };
        upload.findPreviousUploads.mockResolvedValue([previousUpload]);
        const { result, callbacks } = await startUpload(new File(["content"], "resume.txt"));

        expect(upload.resumeFromPreviousUpload).toHaveBeenCalledWith(previousUpload);
        expect(upload.start).toHaveBeenCalledOnce();
        expect(upload.resumeFromPreviousUpload).toHaveBeenCalledBefore(upload.start);
        upload.url = "http://localhost/upload/session789";
        callbacks.onSuccess();

        expect((await result).sessionId).toBe("session789");
    });

    it("does not start if the signal aborts while previous uploads are being fetched", async () => {
        const controller = new AbortController();
        let resolvePreviousUploads: ((uploads: PreviousUploads) => void) | undefined;
        const previousUploads = new Promise<PreviousUploads>((resolve) => {
            resolvePreviousUploads = resolve;
        });
        upload.findPreviousUploads.mockReturnValue(previousUploads);
        const { result, onError } = beginUpload(new File(["content"], "cancelled.txt"), controller.signal);
        const rejection = expect(result).rejects.toThrow("Upload aborted");

        expect(uploadConstructor).toHaveBeenCalledOnce();
        controller.abort();
        ensureDefined(resolvePreviousUploads)([]);
        await previousUploads;

        expect(upload.start).not.toHaveBeenCalled();
        await rejection;
        expect(upload.abort).toHaveBeenCalled();
        expect(onError).toHaveBeenCalledWith(expect.objectContaining({ name: "AbortError" }));
    });

    it("passes the FileStream's reader to the upload", async () => {
        const stream = new ReadableStream<Uint8Array>({
            start(controller) {
                controller.enqueue(new Uint8Array([1, 2, 3]));
                controller.close();
            },
        });
        const fileStream: FileStream = {
            name: "stream.bin",
            size: 3,
            lastModified: 1234567890,
            stream,
            isStream: true,
        };
        const { result, callbacks } = await startUpload(fileStream);

        expect(uploadConstructor).toHaveBeenCalledOnce();
        expect(upload.file).toHaveProperty("read");
        expect(stream.locked).toBe(true);
        upload.url = "http://localhost/upload/stream-session";
        callbacks.onSuccess();
        await result;
    });

    it("reports and rejects a successful upload without a session URL", async () => {
        const { result, onError, callbacks } = await startUpload(new File(["content"], "no-session.txt"));
        const rejection = expect(result).rejects.toThrow("No session ID received");

        upload.url = null;
        callbacks.onSuccess();

        await rejection;
        expect(onError).toHaveBeenCalled();
    });
});
