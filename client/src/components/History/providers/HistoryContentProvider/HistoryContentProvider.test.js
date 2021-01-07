import { pipe } from "rxjs";
import { map } from "rxjs/operators";
import { createLocalVue } from "@vue/test-utils";
import { History } from "../../model/History";
import { SearchParams } from "../../model/SearchParams";
import HistoryContentProvider from "./HistoryContentProvider";
import { bulkCacheContent, wipeDatabase } from "../../caching";
import { getPropRange } from "../../caching/loadHistoryContents";
import { watchForChange, mountRenderless } from "jest/helpers";
import { vueRxShortcutPlugin } from "components/plugins";

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

jest.mock("app");
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

const payloadChange = async ({ vm, label = "payload change" }) => {
    await watchForChange({ vm, propName: "payload", label });
    return vm.payload;
};

const mountProvider = async (Component, propsData) => {
    const localVue = createLocalVue();
    localVue.use(vueRxShortcutPlugin);
    const wrapper = mountRenderless(Component, { localVue, propsData });
    await wrapper.vm.$nextTick();
    return wrapper;
};

describe("HistoryContentProvider", () => {
    let wrapper;

    const defaultProps = {
        parent: testHistory,
        // debouncePeriod: 0,
        bench: 5,
        disableLoad: true,
    };

    afterEach(async () => {
        if (wrapper) {
            await wrapper.destroy();
        }
        await wipeDatabase();
    });

    // No loading, no watching, no polling, all output variables should be
    // dependent solely upon input history

    describe("blank initialization state", () => {
        beforeEach(async () => {
            await wipeDatabase();
            wrapper = await mountProvider(HistoryContentProvider, defaultProps);
        });

        test("should expose all the update methods and default vars", () => {
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

        test("should show an empty payload", async () => {
            await payloadChange({ vm: wrapper.vm });
            expect(wrapper.vm.params).toEqual(new SearchParams());
            expect(wrapper.vm.pageSize).toEqual(SearchParams.pageSize);
        });
    });

    describe("with pre-inserted content", () => {
        beforeEach(async () => {
            await wipeDatabase();
            await bulkCacheContent(historyContent);
            wrapper = await mountProvider(HistoryContentProvider, {
                ...defaultProps,
                pageSize: 5,
            });
        });

        // If the cache adds some content, should still be at the top, but the
        // bottomRows should change to reflect the difference between the
        // returned content rows and the total matches

        test("initial load, no scrolling", async () => {
            await watchForChange({ vm: wrapper.vm, propName: "payload" });
            const { contents, topRows, bottomRows, startKey, totalMatches } = wrapper.vm.payload;
            // show ({ itemCount: contents.length, topRows, bottomRows, startKey, totalMatches });

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
            await watchForChange({ vm: wrapper.vm, propName: "payload" });

            // shift the scroller down to half way through that content list
            // make sure it's visible and not hidden
            const targetElement = historyContent[Math.floor(historyContent.length / 2)];
            expect(targetElement.visible).toBe(true);
            expect(targetElement.deleted).toBe(false);

            const targetKey = targetElement.hid;
            expect(targetKey).toBeDefined();
            expect(targetKey).toBeGreaterThan(0);

            // set that scroll position, then look at what comes out
            // show(targetKey);
            wrapper.vm.setScrollPos({ key: targetKey });

            // what we should get out is a range of content around targetKey and
            // startKey should == targetKey because we know it's in the content
            const { contents: secondContents, ...secondPayload } = await payloadChange({
                vm: wrapper.vm,
                label: "second dealie",
            });
            // show({ items: secondContents.length, ...secondPayload });

            // should get a window around 133, 133 should be the startKey
            const hids = secondContents.map((o) => o.hid);
            expect(hids).toContain(targetKey);
            expect(secondPayload.startKey).toEqual(targetKey);
        });

        // This simulates dragging the scrollbar to a place in the history where
        // there is no exact match of HID. The provider should still render
        // contents around the targetHID, if they exist

        test("should show results when we pick a HID by scroller height rather than exact match", async () => {
            await watchForChange({ vm: wrapper.vm, propName: "payload" });

            // set scroller to non-existent hid
            wrapper.vm.setScrollPos({ cursor: 0.52323 });

            const { contents, startKey, targetKey, topRows, bottomRows, totalMatches } = await payloadChange({
                vm: wrapper.vm,
                label: "scroll cursor dealie",
            });
            const hids = contents.map((o) => o.hid);
            // show({ hids, startKey, targetKey, topRows, bottomRows, totalMatches });

            expect(hids).toContain(startKey);
            expect(startKey).toBeGreaterThan(0);
            expect(targetKey).toBeGreaterThan(0);
            expect(topRows).toBeGreaterThan(0);
            expect(bottomRows).toEqual(totalMatches - contents.length - topRows);
        });
    });
});
