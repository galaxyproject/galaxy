import { UploadQueue } from "./uploadbox";

describe("UploadQueue", () => {
    it("returns the correct next index", async () => {
        const stubOptions = {
            $uploadBox: {
                uploadinput: () => {},
            },
        };
        const uploadQueue = new UploadQueue(stubOptions);

        uploadQueue.queue[0] = "a";
        uploadQueue.queue[1] = "b";
        expect(uploadQueue._nextIndex()).toEqual("0");
    });
});
