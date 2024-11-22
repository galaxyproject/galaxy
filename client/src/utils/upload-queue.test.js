import { sendPayload } from "@/utils/upload-submit.js";

import { UploadQueue } from "./upload-queue.js";

jest.mock("@/utils/upload-submit.js");
sendPayload.mockImplementation(() => jest.fn());

function StubFile(name = null, size = 0, mode = "local") {
    return { name, size, mode };
}

function instrumentedUploadQueue(options = {}) {
    const uploadQueue = new UploadQueue(options);
    uploadQueue.encountedErrors = false;
    uploadQueue.opts.error = function (d, m) {
        uploadQueue.encountedErrors = true;
    };
    return uploadQueue;
}

describe("UploadQueue", () => {
    test("a queue is initialized to correct state", () => {
        const q = instrumentedUploadQueue({ foo: 1 });
        expect(q.size).toEqual(0);
        expect(q.isRunning).toBe(false);
        expect(q.opts.foo).toEqual(1); // passed as options
        expect(q.opts.multiple).toBe(true); // default value
        expect(q.encountedErrors).toBeFalsy();
    });

    test("resetting the queue removes all files from it", () => {
        const q = instrumentedUploadQueue();
        q.add([StubFile("a"), StubFile("b")]);
        expect(q.size).toEqual(2);
        q.reset();
        expect(q.size).toEqual(0);
        expect(q.encountedErrors).toBeFalsy();
    });

    test("calling configure updates options", () => {
        const q = instrumentedUploadQueue({ foo: 1 });
        expect(q.opts.foo).toEqual(1);
        expect(q.opts.bar).toBeUndefined();
        q.configure({ bar: 2 }); // overwrite bar
        expect(q.opts.foo).toEqual(1); // value unchangee
        expect(q.opts.bar).toEqual(2); // value overwritten
        expect(q.encountedErrors).toBeFalsy();
    });

    test("calling start sets isRunning to true", () => {
        const q = instrumentedUploadQueue();
        q._process = jest.fn(); // mock this, otherwise it'll reset isRunning after it's done.
        expect(q.isRunning).toBe(false);
        q.start();
        expect(q.isRunning).toBe(true);
        expect(q.encountedErrors).toBeFalsy();
    });

    test("calling start is a noop if queue is running", () => {
        const q = instrumentedUploadQueue();
        const mockedProcess = jest.fn();
        q._process = mockedProcess();
        q.isRunning = true;
        q.start();
        expect(mockedProcess.mock.calls.length === 0); // function was not called
        expect(q.encountedErrors).toBeFalsy();
    });

    test("calling start processes all files in queue", () => {
        const fileEntries = {};
        const q = instrumentedUploadQueue({
            get: (index) => fileEntries[index],
            announce: (index, file) => {
                fileEntries[index] = {
                    fileMode: file.mode,
                    fileName: file.name,
                    fileSize: file.size,
                    fileContent: "fileContent",
                    targetHistoryId: "mockhistoryid",
                };
            },
        });
        const spy = jest.spyOn(q, "_process");
        const mockedSubmit = jest.fn(() => q._process());
        q._processSubmit = mockedSubmit;
        q.add([StubFile("a"), StubFile("b")]);
        q.start();
        expect(q.size).toEqual(0);
        expect(q.encountedErrors).toBeFalsy();
        expect(spy.mock.calls.length).toEqual(3); // called for 2, 1, 0 files.
        spy.mockRestore(); // not necessary, but safer, in case we later modify implementation.
    });

    test("calling stop sets isPaused to true", () => {
        const q = instrumentedUploadQueue();
        q.start();
        expect(q.isPaused).toBe(false);
        q.stop();
        expect(q.isPaused).toBe(true);
    });

    test("adding files increases the queue size by the number of files", () => {
        const q = instrumentedUploadQueue();
        expect(q.size).toEqual(0);
        q.add([StubFile("a"), StubFile("b")]);
        expect(q.nextIndex).toEqual(2);
        expect(q.size).toEqual(2);
        q.add([StubFile("c")]);
        expect(q.size).toEqual(3);
    });

    test("adding files increases the next index by the number of files", () => {
        const q = instrumentedUploadQueue();
        expect(q.nextIndex).toEqual(0);
        q.add([StubFile("a"), StubFile("b")]);
        expect(q.nextIndex).toEqual(2);
    });

    test("duplicate files are not added to the queue, unless the mode is set to 'new'", () => {
        const q = instrumentedUploadQueue();
        const file1 = StubFile("a", 1);
        const file2 = StubFile("a", 1);
        const file3 = StubFile("a", 1, "new");
        q.add([file1, file2]); // file2 is a duplicate of file1, so only 1 file is added
        expect(q.size).toEqual(1); // queue size incremented by 1
        expect(q.nextIndex).toEqual(1); // next index value incremented by 1
        q.add([file3]); // file3 is a duplicate of file1 and file2, but its mode is "new"
        expect(q.size).toEqual(2); // queue size incremented by 1
        expect(q.nextIndex).toEqual(2); // next index value incremented by 1
    });

    test("adding a file calls opts.announce with correct arguments", () => {
        const mockAnnounce = jest.fn();
        const q = instrumentedUploadQueue({ announce: mockAnnounce });
        const file = StubFile("a");
        expect(mockAnnounce.mock.calls.length).toBe(0);
        q.add([file]);
        expect(mockAnnounce.mock.calls.length).toBe(1); // called once
        expect(mockAnnounce.mock.calls[0][0]).toBe("0"); // first arg is index=0
        expect(mockAnnounce.mock.calls[0][1]).toBe(file); // second arg is file
    });

    test("removing a file reduces the queue size by 1", () => {
        const fileEntries = {};
        const q = instrumentedUploadQueue({
            announce: (index, file) => {
                fileEntries[index] = file;
            },
        });
        q.add([StubFile("a"), StubFile("b")]);
        expect(q.size).toEqual(2);
        q.remove("0");
        expect(q.size).toEqual(1);
    });

    test("removing a file by index out of sequence is allowed", () => {
        const q = instrumentedUploadQueue();
        const file1 = StubFile("a");
        const file2 = StubFile("b");
        const file3 = StubFile("c");
        q.add([file1, file2, file3]);
        expect(q.size).toEqual(3);
        q.remove("1"); // remove file2 (which has index=1)
        expect(q.size).toEqual(2);
        expect(q.queue.get("0")).toBe(file1);
        expect(q.queue.get("1")).toBeUndefined();
        expect(q.queue.get("2")).toBe(file3);
        expect(q.encountedErrors).toBeFalsy();
    });

    test("removing a file via _processIndex, obeys FIFO protocol", () => {
        const q = instrumentedUploadQueue();
        q.add([StubFile("a"), StubFile("b")]);
        let nextIndex = q._processIndex();
        expect(nextIndex).toEqual("0");
        q.remove(nextIndex);
        nextIndex = q._processIndex();
        expect(nextIndex).toEqual("1");
        q.remove(nextIndex);
        expect(q._processIndex()).toBeUndefined();
        expect(q.encountedErrors).toBeFalsy();
    });

    test("remote file batch", () => {
        const fileEntries = {};
        const q = instrumentedUploadQueue({
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
        q.add([StubFile("a"), StubFile("b"), StubFile("c")]);
        expect(q.size).toEqual(3);
        q.start();
        expect(sendPayload.mock.calls[0][0]).toEqual({
            auto_decompress: true,
            files: [],
            history_id: "historyId",
            targets: [
                {
                    destination: { type: "hdas" },
                    elements: [
                        {
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
        });
        expect(q.encountedErrors).toBeFalsy();
    });
});
