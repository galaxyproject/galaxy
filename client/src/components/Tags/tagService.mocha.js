import sinon from "sinon";
import { TagService, __RewireAPI__ as rewire } from "./tagService";
import { createTag } from "./model";
import { interval } from "rxjs";
import { take, takeUntil } from "rxjs/operators";

// test response
import autocompleteResponse from "./testData/autocompleteResponse.txt";

describe("Tags/tagService.js", () => {
    const svcParams = {
        id: 123,
        itemClass: "fooClass",
        context: "",
        debounceInterval: 50, // shorter value than default for unit tests
    };

    const svc = new TagService(svcParams);

    const mockAxios = {
        get: () => null,
    };

    let stub;

    beforeEach(() => {
        rewire.__Rewire__("axios", mockAxios);
    });

    afterEach(() => {
        if (stub) stub.restore();
    });

    describe("save", () => {
        const testLabel = "fo0bar123";
        const testTag = createTag(testLabel);

        const { id, itemClass, context } = svcParams;
        const expectedSaveUrl = `/tag/add_tag_async?item_id=${id}&item_class=${itemClass}&context=${context}&new_tag=${testLabel}`;

        it("should save a string tag", async () => {
            stub = sinon.stub(mockAxios, "get").resolves({ status: 200 });
            const savedTag = await svc.save(testLabel);
            expect(savedTag.text).to.equal(testLabel);
            assert(stub.calledWith(expectedSaveUrl));
        });

        it("should save an object tag", async () => {
            stub = sinon.stub(mockAxios, "get").resolves({ status: 200 });
            const savedTag = await svc.save(testTag);
            expect(savedTag.text).to.equal(testLabel);
            assert(stub.calledWith(expectedSaveUrl));
        });

        // TODO: test error conditions
    });

    describe("delete", () => {
        const testLabel = "fo0bar123";
        const testTag = createTag(testLabel);

        const { id, itemClass, context } = svcParams;
        const expectedDeleteUrl = `/tag/remove_tag_async?item_id=${id}&item_class=${itemClass}&context=${context}&tag_name=${testLabel}`;

        it("should delete a text tag", async () => {
            stub = sinon.stub(mockAxios, "get").resolves({ status: 200 });
            const result = await svc.delete(testTag);
            assert(result);
            assert(stub.calledWith(expectedDeleteUrl));
        });

        it("should delete an object tag", async () => {
            stub = sinon.stub(mockAxios, "get").resolves({ status: 200 });
            const result = await svc.delete(testTag);
            assert(result);
            assert(stub.calledWith(expectedDeleteUrl));
        });

        // TODO: test error conditions
    });

    describe("autocomplete", () => {
        const searchString = "foo";
        const { id, itemClass } = svcParams;
        const expectedSearchUrl = `/tag/tag_autocomplete_data?item_id=${id}&item_class=${itemClass}&q=${searchString}`;

        const successResponse = {
            status: 200,
            data: autocompleteResponse,
        };

        const checkAutocompleteResult = (result) => {
            assert(result);
            assert(result instanceof Array);
            assert(result.length == 2);
            assert(result[0] instanceof Object);
            assert((result[0].text = "abc"));
        };

        // straight ajax request, unused in practice, but it's easier to
        // test this call if we just expose it
        it("ajax call should return tag objects", async () => {
            stub = sinon.stub(mockAxios, "get").resolves(successResponse);
            const result = await svc.autocomplete(searchString);
            assert(stub.calledWith(expectedSearchUrl), "Called with wrong search url");
            checkAutocompleteResult(result);
        });

        // hit the search input with multiple entries, only one ajax call
        // should result because of debouncing
        it("should debounce autocomplete search inputs", (done) => {
            let searchResult;

            // ends subscription to observable so test doesn't go on forever
            const spamCount = Math.floor(Math.random() * 10);
            const timer = interval(1500).pipe(take(1));

            // stub ajax request to return the success response if the
            // searchString is the expected input
            stub = sinon.stub(mockAxios, "get").resolves(successResponse);

            svc.autocompleteOptions.pipe(takeUntil(timer)).subscribe(
                (result) => (searchResult = result),
                (err) => console.log("error", err),
                () => {
                    assert(stub.called, "Ajax call not made");
                    assert(stub.callCount == 1, `Wrong number of ajax calls: ${stub.callCount}`);
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
