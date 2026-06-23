import { Upload } from "tus-js-client";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { buildUploadFingerprint, createTusUpload, type FileStream, type NamedBlob } from "./tusUpload";

// Mock tus-js-client
vi.mock("tus-js-client", () => ({
    Upload: vi.fn(),
}));

const mockUploadConstructor = vi.mocked(Upload);

describe("tusUpload", () => {
    describe("buildUploadFingerprint", () => {
        it("should build fingerprint for File", async () => {
            const file = new File(["content"], "test.txt", {
                type: "text/plain",
                lastModified: 1234567890,
            });
            const historyId = "hist123";

            const fingerprintFn = buildUploadFingerprint(file, historyId);
            const fingerprint = await fingerprintFn();

            expect(fingerprint).toBe("tus-br-test.txt-text/plain-7-1234567890-hist123");
        });

        it("should build fingerprint for Blob with name", async () => {
            const blob = new Blob(["content"], { type: "text/plain" }) as NamedBlob;
            blob.name = "blob.txt";
            const historyId = "hist456";

            const fingerprintFn = buildUploadFingerprint(blob, historyId);
            const fingerprint = await fingerprintFn();

            // Blobs don't have lastModified, so it will be undefined in the fingerprint
            expect(fingerprint).toBe("tus-br-blob.txt-text/plain-7--hist456");
        });

        it("should build fingerprint for FileStream", async () => {
            const stream = new ReadableStream();
            const fileStream: FileStream = {
                name: "stream.txt",
                size: 100,
                type: "text/plain",
                lastModified: 9876543210,
                stream,
                isStream: true,
            };
            const historyId = "hist789";

            const fingerprintFn = buildUploadFingerprint(fileStream, historyId);
            const fingerprint = await fingerprintFn();

            expect(fingerprint).toBe("tus-br-stream.txt-text/plain-100-9876543210-hist789");
        });

        it("should handle missing optional fields", async () => {
            const blob = new Blob(["test"]) as NamedBlob;
            blob.name = "test";
            const historyId = "hist000";

            const fingerprintFn = buildUploadFingerprint(blob, historyId);
            const fingerprint = await fingerprintFn();

            expect(fingerprint).toContain("tus-br-test");
            expect(fingerprint).toContain("hist000");
        });
    });

    describe("createTusUpload", () => {
        let mockUpload: {
            findPreviousUploads: ReturnType<typeof vi.fn>;
            resumeFromPreviousUpload: ReturnType<typeof vi.fn>;
            start: ReturnType<typeof vi.fn>;
            url: string | null;
            options?: Record<string, unknown>;
        };

        beforeEach(() => {
            vi.clearAllMocks();

            // Create mock upload instance
            mockUpload = {
                findPreviousUploads: vi.fn().mockResolvedValue([]),
                resumeFromPreviousUpload: vi.fn(),
                start: vi.fn(),
                url: null,
                options: undefined,
            };

            // Mock the Upload constructor using a class factory
            mockUploadConstructor.mockImplementation(function (_input: unknown, options: unknown) {
                // Store the options for later access
                mockUpload.options = options as Record<string, unknown>;
                return mockUpload as unknown as InstanceType<typeof Upload>;
            } as unknown as typeof Upload);
        });

        it("should successfully upload a file", async () => {
            const file = new File(["content"], "upload.txt", { type: "text/plain" });
            const onProgress = vi.fn();
            const onError = vi.fn();

            const uploadPromise = createTusUpload({
                file,
                endpoint: "http://localhost/upload",
                historyId: "hist123",
                chunkSize: 1024,
                onProgress,
                onError,
            });

            // Wait for the upload to be initialized
            await vi.waitFor(() => expect(mockUpload.options).toBeDefined());

            // Simulate successful upload
            mockUpload.url = "http://localhost/upload/session123";
            const options = mockUpload.options as Record<string, unknown>;
            await (options.onSuccess as () => void)();

            const result = await uploadPromise;

            expect(result).toEqual({
                sessionId: "session123",
                fileName: "upload.txt",
            });
            expect(mockUpload.start).toHaveBeenCalled();
            expect(onError).not.toHaveBeenCalled();
        });

        it("should handle progress updates with rounding", async () => {
            const file = new File(["content"], "progress.txt");
            const onProgress = vi.fn();
            const onError = vi.fn();

            createTusUpload({
                file,
                endpoint: "http://localhost/upload",
                historyId: "hist123",
                chunkSize: 1024,
                onProgress,
                onError,
            });

            // Wait for the upload to be initialized
            await vi.waitFor(() => expect(mockUpload.options).toBeDefined());

            const options = mockUpload.options as Record<string, unknown>;

            // Simulate progress callbacks
            (options.onProgress as (bytesUploaded: number, bytesTotal: number) => void)(50, 100);
            expect(onProgress).toHaveBeenCalledWith(50);

            (options.onProgress as (bytesUploaded: number, bytesTotal: number) => void)(33, 100);
            expect(onProgress).toHaveBeenCalledWith(33);

            (options.onProgress as (bytesUploaded: number, bytesTotal: number) => void)(66.66, 100);
            expect(onProgress).toHaveBeenCalledWith(67); // Rounded up
        });

        it("should reject on 403 authorization error", async () => {
            // Mock console.error since we're testing error logging
            const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});

            const file = new File(["content"], "forbidden.txt");
            const onProgress = vi.fn();
            const onError = vi.fn();

            const uploadPromise = createTusUpload({
                file,
                endpoint: "http://localhost/upload",
                historyId: "hist123",
                chunkSize: 1024,
                onProgress,
                onError,
            });

            // Wait for the upload to be initialized
            await vi.waitFor(() => expect(mockUpload.options).toBeDefined());

            const options = mockUpload.options as Record<string, unknown>;
            const error = new Error("Forbidden") as Error & {
                originalResponse?: { getStatus: () => number };
            };
            error.originalResponse = { getStatus: () => 403 };

            (options.onError as (error: Error) => void)(error);

            await expect(uploadPromise).rejects.toThrow("Forbidden");
            expect(onError).toHaveBeenCalledWith(error);
            expect(consoleErrorSpy).toHaveBeenCalled();

            consoleErrorSpy.mockRestore();
        });

        it("should retry on non-403 errors", async () => {
            const file = new File(["content"], "retry.txt");
            const onProgress = vi.fn();
            const onError = vi.fn();

            const uploadPromise = createTusUpload({
                file,
                endpoint: "http://localhost/upload",
                historyId: "hist123",
                chunkSize: 1024,
                onProgress,
                onError,
            });

            // Wait for the upload to be initialized
            await vi.waitFor(() => expect(mockUpload.options).toBeDefined());

            const options = mockUpload.options as Record<string, unknown>;
            const error = new Error("Network error") as Error & {
                originalResponse?: { getStatus: () => number };
            };
            error.originalResponse = { getStatus: () => 500 };

            // Trigger error (non-403 should log and retry but not call onError)
            (options.onError as (error: Error) => void)(error);

            // For non-403 errors, TUS client handles retry internally
            // The onError callback should NOT be called (only for 403)
            expect(onError).not.toHaveBeenCalled();

            // Now succeed after retry
            mockUpload.url = "http://localhost/upload/session456";
            await (options.onSuccess as () => void)();

            const result = await uploadPromise;
            expect(result.sessionId).toBe("session456");
        });

        it("should resume from previous upload if available", async () => {
            const previousUpload = { uploadUrl: "http://localhost/upload/previous123" };
            mockUpload.findPreviousUploads.mockResolvedValue([previousUpload]);

            const file = new File(["content"], "resume.txt");

            const uploadPromise = createTusUpload({
                file,
                endpoint: "http://localhost/upload",
                historyId: "hist123",
                chunkSize: 1024,
                onProgress: vi.fn(),
                onError: vi.fn(),
            });

            // Wait for the upload to be initialized and resume to be called
            await vi.waitFor(() => {
                expect(mockUpload.resumeFromPreviousUpload).toHaveBeenCalledWith(previousUpload);
            });

            expect(mockUpload.start).toHaveBeenCalled();

            // Complete the upload
            mockUpload.url = "http://localhost/upload/session789";
            const options = mockUpload.options as Record<string, unknown>;
            await (options.onSuccess as () => void)();

            const result = await uploadPromise;
            expect(result.sessionId).toBe("session789");
        });

        it("should handle FileStream by extracting reader", async () => {
            const stream = new ReadableStream({
                start(controller) {
                    controller.enqueue(new Uint8Array([1, 2, 3]));
                    controller.close();
                },
            });

            const fileStream: FileStream = {
                name: "stream.bin",
                size: 3,
                lastModified: Date.now(),
                stream,
                isStream: true,
            };

            createTusUpload({
                file: fileStream,
                endpoint: "http://localhost/upload",
                historyId: "hist123",
                chunkSize: 1024,
                onProgress: vi.fn(),
                onError: vi.fn(),
            });

            // Verify Upload was called with the stream reader, not the FileStream object
            expect(mockUploadConstructor).toHaveBeenCalled();
            const callArgs = mockUploadConstructor.mock.calls[0];
            expect(callArgs?.[0]).toBeDefined();
            // The first argument should be a ReadableStreamDefaultReader
            expect(callArgs?.[0]).toHaveProperty("read");
        });

        it("should reject if no session ID is returned", async () => {
            const file = new File(["content"], "no-session.txt");
            const onProgress = vi.fn();
            const onError = vi.fn();

            const uploadPromise = createTusUpload({
                file,
                endpoint: "http://localhost/upload",
                historyId: "hist123",
                chunkSize: 1024,
                onProgress,
                onError,
            });

            // Wait for the upload to be initialized
            await vi.waitFor(() => expect(mockUpload.options).toBeDefined());

            // Simulate success but with no URL
            mockUpload.url = null;
            const options = mockUpload.options as Record<string, unknown>;
            await (options.onSuccess as () => void)();

            await expect(uploadPromise).rejects.toThrow("No session ID received");
            expect(onError).toHaveBeenCalled();
        });
    });
});
