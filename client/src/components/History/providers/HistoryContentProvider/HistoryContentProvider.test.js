import { pipe } from "rxjs";
import { map } from "rxjs/operators";

import { createLocalVue } from "@vue/test-utils";
import { History } from "../../model/History";
import { SearchParams } from "../../model/SearchParams";
import HistoryContentProvider from "./HistoryContentProvider";
import { wait, mountRenderless } from "jest/helpers";
import { bulkCacheContent, wipeDatabase } from "../../caching";
import { getPropRange } from "../../caching/loadHistoryContents";

//#region Test Data

import rawHistory from "../../test/json/History.json";
import rawHistoryContent from "../../test/json/historyContent.json";

// doctor up some sample content
const historyContent = rawHistoryContent.map((item) => {
    item.history_id = rawHistory.id;
    return item;
});

// set hid_counter to total length +1 because the stupid api can't count
const testHistory = new History({
    ...rawHistory,
    hid_counter: historyContent[0].hid + 1,
});

//#endregion

//#region Mocking

jest.mock("../../caching");

import { loadContents } from "./loadContents";
jest.mock("./loadContents");

const loadContentsResults = historyContent;
const { min: minHid, max: maxHid } = getPropRange(loadContentsResults, "hid");

loadContents.mockImplementation((config) => {
    return pipe(
        map(([history, params, hid]) => {
            return {
                minContentHid: minHid,
                maxContentHid: maxHid,
                minHid: minHid,
                maxHid: maxHid,
                matchesUp: 0,
                matchesDown: SearchParams.pageSize,
                matches: SearchParams.pageSize,
                totalMatchesUp: 0,
                totalMatches: historyContent.length,
            };
        })
    );
});

//#endregion

//#region Mounting

const localVue = createLocalVue();
const mountCmp = async (propsData, delay = 250) => {
    const wrapper = await mountRenderless(HistoryContentProvider, localVue, propsData);
    await wait(delay);
    await localVue.nextTick();
    return wrapper;
};

//#endregion

// clean up before and after tests
beforeEach(wipeDatabase);
afterAll(wipeDatabase);

describe("HistoryContentProvider", () => {
    let wrapper;
    afterEach(async () => {
        if (wrapper) {
            wrapper.destroy();
        }
    });

    describe("blank initialization state", () => {
        // No loading, no watching, no polling, all output variables should be
        // dependent solely upon input history

        beforeEach(async () => {
            wrapper = await mountCmp({
                parent: testHistory,
                debouncePeriod: 0,
                bench: 5,
                disableLoad: true,
                disableWatch: true,
            });
        });

        test("should expose all the update methods we need to test the provider", () => {
            // showAll(wrapper.vm);

            // allows child components to update search params via event handler
            expect(wrapper.vm.updateParams).toBeInstanceOf(Function);

            // allows child scroller component to update the position in the history
            // via an event handler
            expect(wrapper.vm.setScrollPos).toBeInstanceOf(Function);

            // when data comes in from the observables, these are the handlers that
            // run in the subscription, so we can test the provider's logic without
            // having to invoke the observables directly
            expect(wrapper.vm.setPayload).toBeInstanceOf(Function);
        });

        test("should load with default values", async () => {
            expect(wrapper.vm.params).toEqual(new SearchParams());
            expect(wrapper.vm.pageSize).toEqual(SearchParams.pageSize);
        });
    });

    describe("with pre-inserted content", () => {
        const loadDelay = 250;

        beforeEach(async () => {
            await bulkCacheContent(historyContent);
            wrapper = await mountCmp({
                parent: testHistory,
                pageSize: 5,
                debouncePeriod: 0,
                disableLoad: true,
                disablePoll: true,
            });
        });

        // If the cache adds some content, should still be at the top, but the
        // bottomRows should change to reflect the difference between the
        // returned content rows and the total matches

        test("initial load, no scrolling", async () => {
            const { contents, topRows, bottomRows, startKey, totalMatches } = wrapper.vm.payload;

            expect(topRows).toEqual(0);
            expect(contents.length).toEqual(wrapper.vm.pageSize + 1, "wrong pagesize");
            expect(bottomRows).toBeGreaterThan(0);
            expect(bottomRows).toEqual(historyContent.length - contents.length);
            expect(startKey).toEqual(maxHid);
            expect(totalMatches).toEqual(historyContent.length);
        });

        // When the scroller moves, we may end up over a known content row, in
        // which case the scroller handler will get an exact HID match, if so,
        // we should have new content values from the hidMap and some topRows
        // bottomRows

        test("scroll to known key", async () => {
            // shift the scroller down to half way through that content list
            // make sure it's visible and not hidden
            const targetElement = historyContent[Math.floor(historyContent.length / 2)];
            expect(targetElement.visible).toBe(true);
            expect(targetElement.deleted).toBe(false);

            const targetKey = targetElement.hid;
            expect(targetKey).toBeDefined();
            expect(targetKey).toBeGreaterThan(0);

            wrapper.vm.setScrollPos({ key: targetKey });
            await wait(loadDelay);
            await localVue.nextTick();

            // what we should get out is a range of content around targetKey and
            // startKey should == targetKey because we know it's in the content
            const { contents, startKey } = wrapper.vm.payload;

            // should get a window around 133, 133 should be the startKey
            const hids = contents.map((o) => o.hid);
            expect(hids).toContain(targetKey);
            expect(startKey).toEqual(targetKey);
        });

        // This simulates dragging the scrollbar to a place in the history where
        // there is no exact match of HID. The provider should still render
        // contents around the targetHID, if they exist

        test("should show results when we pick a HID by scroller height rather than exact match", async () => {
            // set scroller to non-existent hid
            wrapper.vm.setScrollPos({ cursor: 0.52323 });
            await wait(loadDelay);
            await localVue.nextTick();

            const { contents, startKey, targetKey, topRows, bottomRows, totalMatches } = wrapper.vm.payload;
            const hids = contents.map((o) => o.hid);

            expect(hids).toContain(startKey);
            expect(startKey).toBeGreaterThan(0);
            expect(targetKey).toBeGreaterThan(0);
            expect(topRows).toBeGreaterThan(0);
            expect(bottomRows).toEqual(totalMatches - contents.length - topRows);
        });
    });
});
