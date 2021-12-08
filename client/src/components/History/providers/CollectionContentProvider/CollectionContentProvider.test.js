import { map } from "rxjs/operators";
import { watchUntil, getLocalVue } from "jest/helpers";
import { shallowMount } from "@vue/test-utils";
import { cacheContent, cacheCollectionContent, wipeDatabase, loadDscContent } from "components/providers/History/caching";
import { bulkCacheDscContent } from "components/providers/History/caching/db/observables";
import { summarizeCacheOperation } from "components/providers/History/caching/loadHistoryContents";
import { SearchParams } from "../../model/SearchParams";
import CollectionContentProvider from "./CollectionContentProvider";
import { sameVueObj, payloadChange } from "../../test/providerTestHelpers";
import { testCollection, testCollectionContent } from "../../test/testCollection";
import { defaultPayload } from "../ContentProvider";
// import { reportPayload } from "../../test/providerTestHelpers";

// mocking
jest.mock("app");
jest.mock("components/providers/History/caching");

// fake server call
// prettier-ignore
loadDscContent.mockImplementation((cfg) => (inputs$) => {
    return inputs$.pipe(
        map((inputs) => {
            const [url, , pagination] = inputs;
            const { offset, limit } = pagination;
            // console.log("mock loader", url, pagination);
            const result = testCollectionContent
                .filter((row) => url == row.parent_url)
                .slice(offset, offset + limit);
            return result;
        }),
        bulkCacheDscContent(),
        summarizeCacheOperation()
    );
});

let dsc;
const localVue = getLocalVue();

beforeEach(async () => {
    dsc = await cacheContent(testCollection, true);
});

afterEach(async () => {
    dsc = null;
    await wipeDatabase();
});

describe("CollectionContentProvider", () => {
    const pageSize = 5;
    const debouncePeriod = 250;
    let wrapper;

    afterEach(async () => {
        if (wrapper) {
            wrapper.destroy();
        }
        wrapper = undefined;
    });

    describe("blank initialization state", () => {
        // current payload
        beforeEach(async () => {
            wrapper = await shallowMount(CollectionContentProvider, {
                localVue,
                propsData: {
                    parent: dsc,
                    pageSize,
                    debug: false,
                    debouncePeriod,
                },
                scopedSlots: {
                    default() {},
                },
            });
            await wrapper.vm.$nextTick();
        });

        test("should expose update methods", () => {
            // allows child scroller component to update the position in the history
            // via an event handler
            expect(wrapper.vm.setScrollPos).toBeInstanceOf(Function);
        });

        test("should show an empty payload", () => {
            expect(SearchParams.equals(new SearchParams(), wrapper.vm.params)).toBe(true);
            expect(sameVueObj(wrapper.vm.payload, defaultPayload));
        });
    });

    describe("waiting for simulated server loads", () => {
        beforeEach(async () => {
            wrapper = await shallowMount(CollectionContentProvider, {
                localVue,
                propsData: {
                    parent: dsc,
                    pageSize,
                    debug: false,
                    debouncePeriod,
                },
                scopedSlots: {
                    default: function (props) {
                        // reportPayload(props.payload, { indexKey: "element_index" });
                        // payload = props.payload;
                    },
                },
            });

            // eslint-disable-next-line no-unused-vars
            const spinUp = await watchUntil(wrapper.vm, function () {
                const allDone = wrapper.vm.payload.contents.length > 0;
                // console.log("done?", allDone);
                return allDone;
            });

            // console.log(spinUp);
        });

        test("initial load, no scrolling", async () => {
            const payload = wrapper.vm.payload;
            expect(payload).toBeDefined();
            // reportPayload(payload, { indexKey: "element_index" });
            // reportPayload(initialPayload, { indexKey: "element_index" });
            const { contents, topRows, bottomRows, startKey, totalMatches } = payload;
            expect(topRows).toEqual(0);
            expect(contents.length).toBeGreaterThanOrEqual(2 * wrapper.vm.pageSize);
            expect(totalMatches).toEqual(testCollectionContent.length);
            expect(bottomRows).toBeGreaterThan(0);
            expect(bottomRows).toEqual(testCollectionContent.length - contents.length);

            const testStartIndex = testCollectionContent[0].element_index;
            expect(startKey).toEqual(testStartIndex);
        });

        test("should update to reflect independent cache changes", async () => {
            let hasFoobar;
            const payload = wrapper.vm.payload;

            // check initial emit, for foobars
            expect(payload).toBeDefined();
            hasFoobar = payload.contents.some((o) => o.foobar == 123);
            expect(hasFoobar).toBeFalsy();

            // add a foobar
            const testChild = payload.contents[0];
            testChild.foobar = 123;
            const updateResult = await cacheCollectionContent(testChild, true);
            expect(updateResult.foobar).toEqual(123);

            // check subsequent payload for a foobar
            const updatedPayload = await payloadChange({ vm: wrapper.vm });
            // reportPayload(updatedPayload, { label: "updated", indexKey: "element_index" });
            hasFoobar = updatedPayload.contents.some((o) => o.foobar == 123);
            expect(hasFoobar).toBeTruthy();
        });
    });
});
