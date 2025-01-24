import flushPromises from "flush-promises";

import { collectionCreatorModalSetup } from "./modal";

jest.mock("app");

describe("modal.js", () => {
    let showOptions = null;
    let hidden = false;
    const mockApp = {
        modal: {
            show(showOptions_) {
                showOptions = showOptions_;
            },
            hide() {
                hidden = true;
            },
        },
    };
    let options;
    let showEl;
    let resolution;
    let rejected;

    describe("collectionCreatorModalSetup", () => {
        beforeEach(() => {
            hidden = false;
            rejected = false;
            const object = collectionCreatorModalSetup({}, mockApp);
            options = object.options;
            showEl = object.showEl;
            object.promise
                .catch((rejection_) => {
                    rejected = true;
                })
                .then((resolution_) => {
                    resolution = resolution_;
                });
        });

        it("should create showEl and resolve oncreate", async () => {
            expect(showOptions).toBe(null);
            showEl();
            expect(showOptions.title).toContain("Create a collection");

            expect(hidden).toBeFalsy();
            options.oncreate(null, "testres");
            await flushPromises();
            expect(resolution).toEqual("testres");
            expect(hidden).toBeTruthy();
        });

        it("should hide oncancel", async () => {
            expect(hidden).toBeFalsy();
            options.oncancel();
            await flushPromises();
            expect(hidden).toBeTruthy();
            expect(rejected).toBeTruthy();
        });
    });
});
