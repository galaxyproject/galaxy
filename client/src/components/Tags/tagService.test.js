import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import { TagService } from "./tagService";
import { createTag } from "./model";
import { interval } from "rxjs";
import { take, takeUntil } from "rxjs/operators";

// test response
import autocompleteResponse from "./testData/autocompleteResponse.txt";

const axiosMock = new MockAdapter(axios);

describe("Tags/tagService.js", () => {
    const svcParams = {
        id: 123,
        itemClass: "fooClass",
        context: "",
        debounceInterval: 50, // shorter value than default for unit tests
    };

    const svc = new TagService(svcParams);

    afterEach(() => {
        axiosMock.reset();
    });

    describe("save", () => {
        const testLabel = "fo0bar123";
        const testTag = createTag(testLabel);

        const { id, itemClass, context } = svcParams;
        const expectedSaveUrl = `/tag/add_tag_async?item_id=${id}&item_class=${itemClass}&context=${context}&new_tag=${testLabel}`;

        it("should save a string tag", async () => {
            axiosMock.onAny().reply(200);
            const savedTag = await svc.save(testLabel);
            expect(savedTag.text).toBe(testLabel);
            expect(axiosMock.history.get[0].url).toBe(expectedSaveUrl);
        });

        it("should save an object tag", async () => {
            axiosMock.onAny().reply(200);
            const savedTag = await svc.save(testTag);
            expect(savedTag.text).toBe(testLabel);
            expect(axiosMock.history.get[0].url).toBe(expectedSaveUrl);
        });

        // TODO: test error conditions
    });
    describe("delete", () => {
        const testLabel = "fo0bar123";
        const testTag = createTag(testLabel);

        const { id, itemClass, context } = svcParams;
        const expectedDeleteUrl = `/tag/remove_tag_async?item_id=${id}&item_class=${itemClass}&context=${context}&tag_name=${testLabel}`;

        it("should delete a text tag", async () => {
            axiosMock.onAny().reply(200);
            const result = await svc.delete(testTag);
            expect(result).toBeTruthy();
            expect(axiosMock.history.get[0].url).toBe(expectedDeleteUrl);
        });

        it("should delete an object tag", async () => {
            axiosMock.onAny().reply(200);
            const result = await svc.delete(testTag);
            expect(result).toBeTruthy();
            expect(axiosMock.history.get[0].url).toBe(expectedDeleteUrl);
        });

        // TODO: test error conditions
    });

    describe("autocomplete", () => {
        const searchString = "foo";
        const { id, itemClass } = svcParams;
        const expectedSearchUrl = `/tag/tag_autocomplete_data?item_id=${id}&item_class=${itemClass}&q=${searchString}`;

        const checkAutocompleteResult = (result) => {
            expect(result).toBeTruthy();
            expect(result instanceof Array).toBeTruthy();
            expect(result.length == 2).toBeTruthy();
            expect(result[0] instanceof Object).toBeTruthy();
            expect((result[0].text = "abc")).toBeTruthy();
        };

        // straight ajax request, unused in practice, but it's easier to
        // test this call if we just expose it
        it("ajax call should return tag objects", async () => {
            axiosMock.onGet().reply(200, autocompleteResponse);
            const result = await svc.autocomplete(searchString);
            expect(axiosMock.history.get[0].url).toBe(expectedSearchUrl);
            checkAutocompleteResult(result);
        });

        // hit the search input with multiple entries, only one ajax call
        // should result because of debouncing
        it("should debounce autocomplete search inputs", (done) => {
            let searchResult;
            axiosMock.onAny().reply(200, autocompleteResponse);

            // ends subscription to observable so test doesn't go on forever
            const spamCount = Math.floor(Math.random() * 10);
            const timer = interval(5000).pipe(take(1));

            // stub ajax request to return the success response if the
            // searchString is the expected input

            svc.autocompleteOptions.pipe(takeUntil(timer)).subscribe(
                (result) => (searchResult = result),
                (err) => console.log("error", err),
                () => {
                    expect(axiosMock.history.get.length).toBe(1);
                    checkAutocompleteResult(searchResult);
                    done();
                }
            );

            // spam a bunch of key inputs
            for (let i = 0; i < spamCount; i++) svc.autocompleteSearchText = new String(Math.random());
            svc.autocompleteSearchText = searchString;
        });
    });
});
