import flushPromises from "flush-promises";
import Modal from "utils/modal";

import { collectionCreatorModalSetup } from "./modal";

jest.mock("utils/modal");

describe("modal.js", () => {
    let mockShow;
    let mockHide;

    beforeEach(() => {
        mockShow = jest.fn();
        mockHide = jest.fn();
        Modal.mockImplementation(() => ({
            show: mockShow,
            hide: mockHide,
        }));
    });

    it("should create showEl and resolve oncreate", async () => {
        let resolution;
        const { promise, options, showEl } = collectionCreatorModalSetup({});
        promise.then((res) => (resolution = res));

        expect(mockShow).not.toHaveBeenCalled();
        showEl();
        expect(mockShow).toHaveBeenCalled();
        const showArgs = mockShow.mock.calls[0][0];
        expect(showArgs.title).toContain("Create a collection");

        options.oncreate(null, "testres");
        await flushPromises();
        expect(resolution).toBe("testres");
        expect(mockHide).toHaveBeenCalled();
    });

    it("should hide oncancel and reject", async () => {
        let rejected = false;
        const { promise, options } = collectionCreatorModalSetup({});
        promise.catch(() => (rejected = true));

        options.oncancel();
        await flushPromises();
        expect(mockHide).toHaveBeenCalled();
        expect(rejected).toBe(true);
    });
});
