import { shallowMount } from "@vue/test-utils";
import { watchUntil, getLocalVue } from "jest/helpers";
import { sameVueObj, payloadChange } from "components/providers/History/test/providerTestHelpers";
import HistoryContentProvider from "./HistoryContentProvider";
import { SearchParams } from "components/providers/History/SearchParams";
import { bulkCacheContent, wipeDatabase } from "components/providers/History/caching";
import { defaultPayload } from "../ContentProvider";
import { serverContent, testHistory, testHistoryContent } from "components/providers/History/test/testHistory";

// reads hids
const payloadHids = (payload) => payload.contents?.map((o) => o.hid) || [];
const localVue = getLocalVue();

// mocking
jest.mock("app");
jest.mock("components/providers/History/caching");
jest.mock("./loadContents");

afterEach(() => wipeDatabase());

describe("HistoryContentProvider", () => {
    let wrapper;

    beforeEach(async () => {});

    afterEach(async () => {
        if (wrapper) {
            await wrapper.destroy();
        }
    });

    describe("blank initialization state", () => {
        beforeEach(async () => {
            wrapper = await shallowMount(HistoryContentProvider, {
                localVue,
                propsData: {
                    parent: testHistory,
                    pageSize: 10,
                    debug: false,
                    debouncePeriod: 200,
                },
                scopedSlots: {
                    default() {},
                },
            });
            // wait for default emit
            await payloadChange({ vm: wrapper.vm });
        });

        test("should expose update methods", async () => {
            expect(wrapper.vm.setScrollPos).toBeInstanceOf(Function);
        });

        test("should show an empty payload", () => {
            expect(SearchParams.equals(new SearchParams(), wrapper.vm.params)).toBe(true);
            expect(sameVueObj(wrapper.vm.payload, defaultPayload));
        });
    });

    describe("with pre-inserted content", () => {
        beforeEach(async () => {
            // eslint-disable-next-line no-unused-vars
            const cachedContent = await bulkCacheContent(testHistoryContent, true);

            wrapper = await shallowMount(HistoryContentProvider, {
                localVue,
                propsData: {
                    parent: testHistory,
                    pageSize: 10,
                    debug: false,
                    debouncePeriod: 200,
                },
                scopedSlots: {
                    default() {},
                },
            });

            // eslint-disable-next-line no-unused-vars
            const spinUp = await watchUntil(wrapper.vm, function () {
                const allDone = wrapper.vm.payload.contents.length > 0;
                // console.log("done?", allDone);
                return allDone;
            });
        });

        // If the cache adds some content, should still be at the top, but the
        // bottomRows should change to reflect the difference between the
        // returned content rows and the total matches

        test("initial load, no scrolling", async () => {
            const payload = wrapper.vm.payload;
            // reportPayload(payload);

            // test data on server
            const allContent = serverContent();
            // maximum hid in the fake server content
            const maxServerHid = allContent[0].hid;
            expect(payload).toBeDefined();

            const { contents, topRows, bottomRows, startKey, totalMatches } = payload;
            expect(topRows).toEqual(0);
            expect(contents.length).toBeGreaterThanOrEqual(2 * wrapper.vm.pageSize);
            expect(bottomRows).toBeGreaterThan(0);
            expect(bottomRows).toEqual(allContent.length - contents.length);
            expect(startKey).toEqual(maxServerHid);
            expect(totalMatches).toEqual(allContent.length);
        });

        // When the scroller moves, we may end up over a known content row, in
        // which case the scroller handler will get an exact HID match, if so,
        // we should have new content values from the hidMap and some topRows
        // bottomRows

        test("scroll to known key", async () => {
            const payload = wrapper.vm.payload;

            // shift the scroller down to half way through that content list
            // make sure it's visible and not hidden
            const targetElement = testHistoryContent[Math.floor(testHistoryContent.length / 2)];
            expect(targetElement.visible).toBe(true);
            expect(targetElement.deleted).toBe(false);

            const targetKey = targetElement.hid;
            expect(targetKey).toBeDefined();
            expect(targetKey).toBeGreaterThan(0);

            // console.log("setting scroll pos to targetKey", targetKey);
            wrapper.vm.setScrollPos({ key: targetKey });

            // need to wait for it to settle down
            await await payloadChange({ vm: wrapper.vm });

            // check to see if what we want is there
            const scrollPayload = wrapper.vm.payload;
            expect(payload).toBeDefined();
            const { startKey } = scrollPayload;
            const hids = payloadHids(scrollPayload);
            // console.log("hids", hids);

            expect(hids).toContain(targetKey);
            expect(startKey).toEqual(targetKey);
        });

        // This simulates dragging the scrollbar to a place in the history where
        // there is no exact match of HID. The provider should still render
        // contents around the targetHID, if they exist

        test("should show results when we pick a HID by scroller height", async () => {
            // set scroller to non-existent hid
            wrapper.vm.setScrollPos({ cursor: 0.52323 });
            const scrollPayload = await payloadChange({ vm: wrapper.vm });
            const { contents, startKey, topRows, bottomRows, totalMatches } = scrollPayload;
            const hids = payloadHids(scrollPayload);

            expect(hids).toContain(startKey);
            expect(startKey).toBeGreaterThan(0);
            expect(topRows).toBeGreaterThan(0);
            expect(bottomRows).toEqual(totalMatches - contents.length - topRows);
        });
    });
});
