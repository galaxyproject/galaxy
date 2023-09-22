import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import { TagService } from "./tagService";
import { createTag } from "./model";
import autocompleteResponse from "./testData/autocompleteResponse.txt";

describe("Tags/tagService.js", () => {
    const axiosMock = new MockAdapter(axios);
    const svcParams = {
        id: 123,
        itemClass: "fooClass",
        context: "",
        debounceInterval: 50, // shorter value than default for unit tests
    };
    const testLabel = "fo0bar123";
    const expectedParams = {
        item_id: 123,
        item_class: "fooClass",
        context: "",
    };

    const svc = new TagService(svcParams);
    beforeEach(() => {
        axiosMock.onAny().reply(200, autocompleteResponse);
    });

    afterEach(() => {
        axiosMock.reset();
    });

    describe("save", () => {
        const testTag = createTag(testLabel);

        const expectedSaveUrl = `/tag/add_tag_async`;

        it("should save a string tag", async () => {
            const savedTag = await svc.save(testLabel);
            expect(savedTag.text).toBe(testLabel);
            expect(axiosMock.history.get[0].url).toBe(expectedSaveUrl);
            expect(axiosMock.history.get[0].params).toEqual({ ...expectedParams, new_tag: testLabel });
        });

        it("should save an object tag", async () => {
            const savedTag = await svc.save(testTag);
            expect(savedTag.text).toBe(testLabel);
            expect(axiosMock.history.get[0].url).toBe(expectedSaveUrl);
            expect(axiosMock.history.get[0].params).toEqual({ ...expectedParams, new_tag: testLabel });
        });

        // TODO: test error conditions
    });
    describe("delete", () => {
        const testTag = createTag(testLabel);

        const expectedDeleteUrl = `/tag/remove_tag_async`;

        it("should delete a text tag", async () => {
            const result = await svc.delete(testTag);
            expect(result).toBeTruthy();
            expect(axiosMock.history.get[0].url).toBe(expectedDeleteUrl);
            expect(axiosMock.history.get[0].params).toEqual({ ...expectedParams, tag_name: testLabel });
        });

        it("should delete an object tag", async () => {
            const result = await svc.delete(testTag);
            expect(result).toBeTruthy();
            expect(axiosMock.history.get[0].url).toBe(expectedDeleteUrl);
            expect(axiosMock.history.get[0].params).toEqual({ ...expectedParams, tag_name: testLabel });
        });

        // TODO: test error conditions
    });

    describe("autocomplete", () => {
        const searchString = "foo";
        const expectedSearchUrl = `/tag/tag_autocomplete_data`;

        const checkAutocompleteResult = (result) => {
            expect(result).toBeTruthy();
            expect(result instanceof Array).toBeTruthy();
            expect(result.length == 2).toBeTruthy();
            expect(result[0] instanceof Object).toBeTruthy();
            expect((result[0].text = "abc")).toBeTruthy();
        };

        // straight ajax request, unused in practice, but it's easier to
        // test this call if we just expose it
        const { ...searchParams } = expectedParams;
        delete searchParams.context;

        it("ajax call should return tag objects", async () => {
            const result = await svc.autocomplete(searchString);
            expect(axiosMock.history.get[0].url).toBe(expectedSearchUrl);
            expect(axiosMock.history.get[0].params).toEqual({ ...searchParams, q: searchString });
            checkAutocompleteResult(result);
        });
    });
});
