import { UploadQueue } from "./uploadbox";

describe("UploadQueue", () => {
    const mockDialog = jest.fn();

    function TestUploadQueue(options) {
        // Provide a stub for the $uploadBox default value (used in constuctor);
        // and a mocked dialog function (used in select).
        const stubOptions = {
            $uploadBox: {
                uploadinput: () => ({ dialog: mockDialog }),
            },
        };
        if (options) {
            Object.assign(stubOptions, options);
        }
        return new UploadQueue(stubOptions);
    }

    function StubFile(name = null, size = 0, mode = null) {
        this.name = name;
        this.size = size;
        this.mode = mode;
    }

    test("a queue is initialized to correct state", () => {
        const q = TestUploadQueue({ foo: 1 });
        expect(q.size).toEqual(0);
        expect(q.isRunning).toBe(false);
        expect(q.opts.foo).toEqual(1); // passed as options
        expect(q.opts.multiple).toBe(true); // default value
    });

    test("calling select calls uploadinput.dialog", () => {
        const q = TestUploadQueue();
        expect(mockDialog.mock.calls.length).toBe(0);
        q.select();
        expect(mockDialog.mock.calls.length).toBe(1); // called once
    });

    test("resetting the queue removes all files from it", () => {
        const q = TestUploadQueue();
        q.add([new StubFile("a"), new StubFile("b")]);
        expect(q.size).toEqual(2);
        q.reset();
        expect(q.size).toEqual(0);
    });

    test("calling configure updates options", () => {
        const q = TestUploadQueue({ foo: 1 });
        expect(q.opts.foo).toEqual(1);
        expect(q.opts.bar).toBeUndefined();
        q.configure({ bar: 2 }); // overwrite bar
        expect(q.opts.foo).toEqual(1); // value unchangee
        expect(q.opts.bar).toEqual(2); // value overwritten
    });

    describe("checking browser compatibility", () => {
        const compatibleBrowser = {
            File: 1,
            FormData: 1,
            XMLHttpRequest: 1,
            FileList: 1,
        };
        const incompatibleBrowser = Object.assign(
            {},
            compatibleBrowser,
            { File: 0 } // set File to 0 to make it incompatible.
        );
        let spy;

        beforeEach(() => {
            spy = jest.spyOn(window, "window", "get");
            spy.mockImplementation(() => compatibleBrowser);
        });

        afterEach(() => {
            spy.mockRestore();
        });

        test("calling compatible checks 4 window properties", () => {
            const q = TestUploadQueue();
            expect(spy.mock.calls.length).toEqual(0);
            q.compatible();
            expect(spy.mock.calls.length).toEqual(4);
        });

        test("calling compatible returns truthy or falsy depending on values of 4 window properties", () => {
            const q = TestUploadQueue();
            expect(q.compatible()).toBeTruthy();
            spy.mockImplementation(() => incompatibleBrowser); // make browser incompatible
            expect(q.compatible()).toBeFalsy();
        });
    });

    test("calling start sets isRunning to true", () => {
        const q = TestUploadQueue();
        q._process = jest.fn(); // mock this, otherwise it'll reset isRunning after it's done.
        expect(q.isRunning).toBe(false);
        q.start();
        expect(q.isRunning).toBe(true);
    });

    test("calling start is a noop if queue is running", () => {
        const q = TestUploadQueue();
        const mockedProcess = jest.fn();
        q._process = mockedProcess();
        q.isRunning = true;
        q.start();
        expect(mockedProcess.mock.calls.length === 0); // function was not called
    });

    test("calling start processes all files in queue", () => {
        const q = TestUploadQueue();
        const mockedSubmit = jest.fn((index) => q._process());
        q._submitUpload = mockedSubmit;
        const spy = jest.spyOn(q, "_process");

        q.add([new StubFile("a"), new StubFile("b")]);
        q.start();
        expect(q.size).toEqual(0);
        expect(spy.mock.calls.length).toEqual(3); // called for 2,1,0 files.
        spy.mockRestore(); // not necessary, but safer, in case we later modify implementation.
    });
    test("calling stop sets isPaused to true", () => {
        const q = TestUploadQueue();
        q.start();
        expect(q.isPaused).toBe(false);
        q.stop();
        expect(q.isPaused).toBe(true);
    });

    describe("adding files", () => {
        test("adding files increases the queue size by the number of files", () => {
            const q = TestUploadQueue();
            expect(q.size).toEqual(0);
            q.add([new StubFile("a"), new StubFile("b")]);
            expect(q.size).toEqual(2);
            q.add([new StubFile("c")]);
            expect(q.size).toEqual(3);
        });

        test("adding files increases the next index by the number of files", () => {
            const q = TestUploadQueue();
            expect(q.nextIndex).toEqual(0);
            q.add([new StubFile("a"), new StubFile("b")]);
            expect(q.nextIndex).toEqual(2);
        });

        test("duplicate files are not added to the queue, unless the mode is set to 'new'", () => {
            const q = TestUploadQueue();
            const file1 = new StubFile("a", 1);
            const file2 = new StubFile("a", 1);
            const file3 = new StubFile("a", 1, "new");
            q.add([file1, file2]); // file2 is a duplicate of file1, so only 1 file is added
            expect(q.size).toEqual(1); // queue size incremented by 1
            expect(q.nextIndex).toEqual(1); // next index value incremented by 1
            q.add([file3]); // file3 is a duplicate of file1 and file2, but its mode is "new"
            expect(q.size).toEqual(2); // queue size incremented by 1
            expect(q.nextIndex).toEqual(2); // next index value incremented by 1
        });

        test("adding a file calls opts.announce with correct arguments", () => {
            const mockAnnounce = jest.fn();
            const q = TestUploadQueue({ announce: mockAnnounce });
            const file = new StubFile("a");
            expect(mockAnnounce.mock.calls.length).toBe(0);
            q.add([file]);
            expect(mockAnnounce.mock.calls.length).toBe(1); // called once
            expect(mockAnnounce.mock.calls[0][0]).toBe(0); // first arg is index=0
            expect(mockAnnounce.mock.calls[0][1]).toBe(file); // second arg is file
        });
    });

    describe("removing files", () => {
        test("removing a file reduces the queue size by 1", () => {
            const q = TestUploadQueue();
            q.add([new StubFile("a"), new StubFile("b")]);
            expect(q.size).toEqual(2);
            q.remove(0);
            expect(q.size).toEqual(1);
        });

        test("removing a file by index out of sequence is allowed", () => {
            const q = TestUploadQueue();
            const file1 = new StubFile("a");
            const file2 = new StubFile("b");
            const file3 = new StubFile("c");
            q.add([file1, file2, file3]);
            expect(q.size).toEqual(3);
            q.remove(1); // remove file2 (which has index=1)
            expect(q.size).toEqual(2);
            expect(q.queue.get(0)).toBe(file1);
            expect(q.queue.get(1)).toBeUndefined();
            expect(q.queue.get(2)).toBe(file3);
        });

        test("removing a file via _firstItemIndex, obeys FIFO protocol", () => {
            const q = TestUploadQueue();
            q.add([new StubFile("a"), new StubFile("b")]);
            let nextIndex = q._firstItemIndex();
            expect(nextIndex).toEqual(0);
            q.remove(nextIndex);
            nextIndex = q._firstItemIndex();
            expect(nextIndex).toEqual(1);
            q.remove(nextIndex);
            expect(q._firstItemIndex()).toBeUndefined();
        });
    });
});
