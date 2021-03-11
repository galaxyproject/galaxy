import { shallowMount } from "@vue/test-utils";
import { map } from "rxjs/operators";
import { History, SearchParams } from "../../model";
import HistoryContentProvider from "./HistoryContentProvider";
import { bulkCacheContent, wipeDatabase } from "../../caching";
import { getPropRange } from "../../caching/loadHistoryContents";
import { watchForChange, getLocalVue, wait } from "jest/helpers";

//#region Test Data

import rawHistory from "../../test/json/History.json";
import rawHistoryContent from "../../test/json/historyContent.json";

const historyContent = rawHistoryContent.map((item) => {
    item.history_id = rawHistory.id;
    return item;
});

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
    return map(() => {
        return {
            summary: {},
            matches: SearchParams.pageSize,
            totalMatches: historyContent.length,
            minHid: minHid,
            maxHid: maxHid,
            minContentHid: minHid,
            maxContentHid: maxHid,
            limit: 0,
            offset: 0,
        };
    });
});

//#endregion

const payloadChange = async ({ vm, label = "payload change" }) => {
    await watchForChange({ vm, propName: "payload", label });
    return vm.payload;
};

describe("HistoryContentProvider", () => {
    const localVue = getLocalVue();
    const propsData = {
        parent: testHistory,
        pageSize: 5,
    };
    let wrapper;
    let slotProps;

    beforeEach(async () => {
        await wipeDatabase();
        slotProps = undefined;
    });

    afterEach(async () => {
        if (wrapper) {
            await wrapper.destroy();
        }
        await wipeDatabase();
    });

    xdescribe("blank initialization state", () => {
        beforeEach(async () => {
            slotProps = null;
            wrapper = shallowMount(HistoryContentProvider, {
                localVue,
                propsData,
                scopedSlots: {
                    default(props) {
                        slotProps = props;
                    },
                },
            });
            await wrapper.vm.$nextTick();
        });

        test("should expose all the update methods and default vars", () => {
            // allows child scroller component to update the position in the history
            // via an event handler
            expect(wrapper.vm.setScrollPos).toBeInstanceOf(Function);

            // when data comes in from the observables, these are the handlers that
            // run in the subscription, so we can test the provider's logic without
            // having to invoke the observables directly
            expect(wrapper.vm.setPayload).toBeInstanceOf(Function);
        });

        test("should show an empty payload", async () => {
            expect(SearchParams.equals(new SearchParams(), wrapper.vm.params)).toBe(true);
            expect(wrapper.vm.pageSize).toEqual(propsData.pageSize);
        });
    });

    describe("with pre-inserted content", () => {
        beforeEach(async () => {
            await bulkCacheContent(historyContent);

            wrapper = shallowMount(HistoryContentProvider, {
                localVue,
                propsData: {
                    parent: testHistory,
                    pageSize: 5,
                },
                scopedSlots: {
                    default(props) {
                        slotProps = props;
                    },
                },
            });

            await payloadChange({ vm: wrapper.vm });
        });

        // If the cache adds some content, should still be at the top, but the
        // bottomRows should change to reflect the difference between the
        // returned content rows and the total matches

        xtest("initial load, no scrolling", async () => {
            const payload = slotProps.payload;
            expect(payload).toBeDefined();
            const { contents, topRows, bottomRows, startKey, totalMatches } = payload;
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
            const { contents: firstContents, ...firstPayload } = slotProps.payload;

            // shift the scroller down to half way through that content list
            // make sure it's visible and not hidden
            const targetElement = historyContent[Math.floor(historyContent.length / 2)];
            expect(targetElement.visible).toBe(true);
            expect(targetElement.deleted).toBe(false);

            const targetKey = targetElement.hid;
            expect(targetKey).toBeDefined();
            expect(targetKey).toBeGreaterThan(0);

            // set the scroll position to a fixed key, then look at what comes out
            // console.log("scrolling to", targetKey);
            // wrapper.vm.setScrollPos({ key: targetKey });

            // // what we should get out is a range of content around targetKey and
            // // startKey should == targetKey because we know it's in the content
            // const { contents, ...secondPayload } = await payloadChange({
            //     vm: wrapper.vm,
            // });
            // await wait(1000);

            // // should get a window around targetKey, targetKey should be the startKey
            // const hids = contents.map((o) => o.hid);
            // console.log("second payload", secondPayload);
            // console.log("hids", hids);

            // expect(hids).toContain(targetKey);
            // expect(secondPayload.startKey).toEqual(targetKey);
        });

        // This simulates dragging the scrollbar to a place in the history where
        // there is no exact match of HID. The provider should still render
        // contents around the targetHID, if they exist

        xtest("should show results when we pick a HID by scroller height rather than exact match", async () => {
            // set scroller to non-existent hid
            wrapper.vm.setScrollPos({ cursor: 0.52323, key: null });

            const { contents, startKey, topRows, bottomRows, totalMatches } = await payloadChange({
                vm: wrapper.vm,
                label: "scroll cursor dealie",
            });
            const hids = contents.map((o) => o.hid);
            // show({ hids, startKey, targetKey, topRows, bottomRows, totalMatches });

            expect(hids).toContain(startKey);
            expect(startKey).toBeGreaterThan(0);
            expect(topRows).toBeGreaterThan(0);
            expect(bottomRows).toEqual(totalMatches - contents.length - topRows);
        });
    });
});
