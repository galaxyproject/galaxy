import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { fetchDatasets, submitUpload } from "@/utils/upload";

import { UploadQueue } from "./upload-queue.js";

vi.mock("@/utils/upload", async (importOriginal) => {
    const actual = await importOriginal();
    return {
        ...actual,
        fetchDatasets: vi.fn(),
        submitUpload: vi.fn((config) => {
            config.success?.();
        }),
    };
});

function createFile(name = null, size = 0, mode = "local") {
    return { name, size, mode };
}

function createQueue(options = {}) {
    return new UploadQueue({ ...options, error: vi.fn() });
}

function createLocalUploadQueue() {
    const fileEntries = {};
    return createQueue({
        get: (index) => fileEntries[index],
        announce: (index, file) => {
            fileEntries[index] = {
                fileMode: file.mode,
                fileName: file.name,
                fileSize: file.size,
                fileContent: "fileContent",
                fileData: new File(["test content"], file.name || "test.txt", { type: "text/plain" }),
                targetHistoryId: "mockhistoryid",
            };
        },
    });
}

describe("UploadQueue", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    it("initializes an empty, idle queue with supplied and default options", () => {
        const queue = createQueue({ foo: 1 });
        expect(queue.size).toEqual(0);
        expect(queue.isRunning).toBe(false);
        expect(queue.opts.foo).toEqual(1);
        expect(queue.opts.multiple).toBe(true);
        expect(queue.opts.error).not.toHaveBeenCalled();
    });

    it("resetting the queue removes all files from it", () => {
        const queue = createQueue();
        queue.add([createFile("a"), createFile("b")]);
        expect(queue.size).toEqual(2);
        queue.reset();
        expect(queue.size).toEqual(0);
        expect(queue.opts.error).not.toHaveBeenCalled();
    });

    it("merges new options without discarding existing ones", () => {
        const queue = createQueue({ foo: 1 });
        expect(queue.opts.foo).toEqual(1);
        expect(queue.opts.bar).toBeUndefined();
        queue.configure({ bar: 2 });
        expect(queue.opts.foo).toEqual(1);
        expect(queue.opts.bar).toEqual(2);
        expect(queue.opts.error).not.toHaveBeenCalled();
    });

    it("marks the queue running before processing finishes", () => {
        const queue = createQueue();
        queue._process = vi.fn(); // Keep processing pending so start does not immediately return to idle.
        expect(queue.isRunning).toBe(false);
        queue.start();
        expect(queue.isRunning).toBe(true);
        expect(queue.opts.error).not.toHaveBeenCalled();
    });

    it("does not restart processing an already running queue", () => {
        const queue = createQueue();
        const mockedProcess = vi.fn();
        queue._process = mockedProcess;
        queue.isRunning = true;
        queue.start();
        expect(mockedProcess).not.toHaveBeenCalled();
        expect(queue.opts.error).not.toHaveBeenCalled();
    });

    it("processes both local files and drains the queue", () => {
        const queue = createLocalUploadQueue();
        const processSpy = vi.spyOn(queue, "_process");
        queue.add([createFile("a"), createFile("b")]);
        queue.start();
        expect(queue.size).toEqual(0);
        expect(queue.opts.error).not.toHaveBeenCalled();
        expect(processSpy).toHaveBeenCalledTimes(3);
        expect(submitUpload).toHaveBeenCalledTimes(2);
    });

    it("marks the queue paused when stopped", () => {
        const queue = createQueue();
        queue.start();
        expect(queue.isPaused).toBe(false);
        queue.stop();
        expect(queue.isPaused).toBe(true);
    });

    it("adding files increases the queue size by the number of files", () => {
        const queue = createQueue();
        expect(queue.size).toEqual(0);
        queue.add([createFile("a"), createFile("b")]);
        expect(queue.nextIndex).toEqual(2);
        expect(queue.size).toEqual(2);
        queue.add([createFile("c")]);
        expect(queue.size).toEqual(3);
    });

    it("adding files increases the next index by the number of files", () => {
        const queue = createQueue();
        expect(queue.nextIndex).toEqual(0);
        queue.add([createFile("a"), createFile("b")]);
        expect(queue.nextIndex).toEqual(2);
    });

    it("duplicate files are not added to the queue, unless the mode is set to 'new'", () => {
        const queue = createQueue();
        const originalFile = createFile("a", 1);
        const duplicateFile = createFile("a", 1);
        const pastedFile = createFile("a", 1, "new");
        queue.add([originalFile, duplicateFile]);
        expect(queue.size).toEqual(1);
        expect(queue.nextIndex).toEqual(1);
        queue.add([pastedFile]);
        expect(queue.size).toEqual(2);
        expect(queue.nextIndex).toEqual(2);
    });

    it("announces the added file with its string index", () => {
        const mockAnnounce = vi.fn();
        const queue = createQueue({ announce: mockAnnounce });
        const file = createFile("a");
        expect(mockAnnounce).not.toHaveBeenCalled();
        queue.add([file]);
        expect(mockAnnounce).toHaveBeenCalledExactlyOnceWith("0", file);
        expect(mockAnnounce.mock.calls[0][1]).toBe(file);
    });

    it("removing a file reduces the queue size by 1", () => {
        const queue = createQueue();
        queue.add([createFile("a"), createFile("b")]);
        expect(queue.size).toEqual(2);
        queue.remove("0");
        expect(queue.size).toEqual(1);
    });

    it("removing a file by index out of sequence is allowed", () => {
        const queue = createQueue();
        const file1 = createFile("a");
        const file2 = createFile("b");
        const file3 = createFile("c");
        queue.add([file1, file2, file3]);
        expect(queue.size).toEqual(3);
        queue.remove("1"); // remove file2 (which has index=1)
        expect(queue.size).toEqual(2);
        expect(queue.queue.get("0")).toBe(file1);
        expect(queue.queue.get("1")).toBeUndefined();
        expect(queue.queue.get("2")).toBe(file3);
        expect(queue.opts.error).not.toHaveBeenCalled();
    });

    it("removing a file that was already submitted is a noop", () => {
        const queue = createLocalUploadQueue();
        queue.add([createFile("a", 1), createFile("b", 2)]);
        queue.start();
        expect(queue.size).toEqual(0);
        expect(() => queue.remove("0")).not.toThrow();
        queue.add([createFile("a", 1)]);
        expect(queue.size).toEqual(1);
        expect(queue.opts.error).not.toHaveBeenCalled();
    });

    it("processes remaining files in insertion order", () => {
        const queue = createQueue();
        queue.add([createFile("a"), createFile("b")]);
        let nextIndex = queue._processIndex();
        expect(nextIndex).toEqual("0");
        queue.remove(nextIndex);
        nextIndex = queue._processIndex();
        expect(nextIndex).toEqual("1");
        queue.remove(nextIndex);
        expect(queue._processIndex()).toBeUndefined();
        expect(queue.opts.error).not.toHaveBeenCalled();
    });

    it("submits three remote files in one payload for their target history", () => {
        const fileEntries = {};
        const queue = createQueue({
            historyId: "historyId",
            announce: (index, file) => {
                fileEntries[index] = {
                    deferred: true,
                    fileContent: `http://test.me.${index}`,
                    fileMode: "url",
                    fileName: file.name,
                    fileSize: 100,
                    spaceToTab: true,
                    status: "queued",
                    toPosixLines: false,
                    targetHistoryId: "historyId",
                };
            },
            get: (index) => fileEntries[index],
        });
        queue.add([createFile("a"), createFile("b"), createFile("c")]);
        expect(queue.size).toEqual(3);
        queue.start();
        expect(fetchDatasets).toHaveBeenCalledTimes(1);
        expect(fetchDatasets).toHaveBeenCalledWith(
            {
                auto_decompress: true,
                files: [],
                history_id: "historyId",
                targets: [
                    {
                        auto_decompress: true,
                        destination: { type: "hdas" },
                        elements: [
                            {
                                auto_decompress: true,
                                dbkey: "?",
                                deferred: true,
                                ext: "auto",
                                name: "a",
                                space_to_tab: true,
                                src: "url",
                                to_posix_lines: false,
                                url: "http://test.me.0",
                            },
                            {
                                auto_decompress: true,
                                dbkey: "?",
                                deferred: true,
                                ext: "auto",
                                name: "b",
                                space_to_tab: true,
                                src: "url",
                                to_posix_lines: false,
                                url: "http://test.me.1",
                            },
                            {
                                auto_decompress: true,
                                dbkey: "?",
                                deferred: true,
                                ext: "auto",
                                name: "c",
                                space_to_tab: true,
                                src: "url",
                                to_posix_lines: false,
                                url: "http://test.me.2",
                            },
                        ],
                    },
                ],
            },
            expect.objectContaining({ success: expect.any(Function), error: expect.any(Function) }),
        );
        expect(queue.opts.error).not.toHaveBeenCalled();
    });
});
