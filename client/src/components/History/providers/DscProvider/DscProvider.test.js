/* eslint-disable no-unused-vars */
import { createLocalVue } from "@vue/test-utils";
import { wait, mountRenderless } from "jest/helpers";
import { wipeDatabase } from "../../caching";
import { cacheContent, getCachedContent, cacheCollectionContent, getCachedCollectionContent } from "../../caching";
import { DatasetCollection } from "../../model/DatasetCollection";
import DscProvider from "./DscProvider";
import { vueRxShortcutPlugin } from "components/plugins";

// test data as root-level collections
import rootContents from "../../test/json/historyContentWithCollection.json";

// test data for a nested collection
import nestedContents from "../../test/json/collectionContent.json";

// Imports dependencies without firing up worker because that blows with Jest
jest.mock("app");
jest.mock("../../caching");

const mountProvider = async (Component, propsData) => {
    const localVue = createLocalVue();
    localVue.use(vueRxShortcutPlugin);
    const wrapper = mountRenderless(Component, localVue, propsData);
    await wrapper.vm.$nextTick();
    return wrapper;
};

beforeEach(wipeDatabase);
afterEach(wipeDatabase);

describe("DscProvider", () => {
    let wrapper;
    let rootCollection;
    let nestedCollection;
    const fakeContentUrl = "/foo/bar";

    beforeEach(async () => {
        // cache a root level collection as history content
        const rawContent = rootContents[0];
        const cacheResult = await cacheContent(rawContent, true);
        rootCollection = new DatasetCollection(cacheResult);

        // cache a nested collection as dscContent
        const rawNested = nestedContents[0];
        rawNested.parent_url = fakeContentUrl;
        const nestedCacheResult = await cacheCollectionContent(rawNested, true);
        nestedCollection = new DatasetCollection(nestedCacheResult);
    });

    afterEach(async () => {
        if (wrapper) {
            wrapper.destroy();
        }
    });

    describe("monitors a root collection (direct child of a history)", () => {
        beforeEach(async () => {
            wrapper = await mountProvider(DscProvider, {
                collection: rootCollection,
                isRoot: true,
            });
        });

        test("should successfully mount and emit the pre-cached data", () => {
            expect(wrapper).toBeDefined();
            const { _rev, cached_at, ...originalProps } = rootCollection;
            const { _rev: new_rev, cached_at: new_cached_at, ...newProps } = wrapper.vm.dsc;
            expect(originalProps).toEqual(newProps);
        });

        test("should emit updates as they occur", async () => {
            const { cached_at: old_cached_at, _rev: old_rev, ...oldProps } = wrapper.vm.dsc;

            // write a new field to the collection
            const fooVal = "abc123";
            rootCollection.foo = fooVal;
            const updatedRoot = await cacheContent(rootCollection, true);

            // double-check it's really changed
            const lookup = await getCachedContent(updatedRoot._id);
            expect(lookup.foo).toEqual(fooVal);

            // wait for next update then check the foo val
            await wrapper.vm.$nextTick();

            // all same props except _rev and cached_at and foo
            const { cached_at, _rev, foo, ...newProps } = wrapper.vm.dsc;
            expect(foo).toEqual(fooVal);
            expect(old_cached_at).toBeLessThan(cached_at);
            expect(old_rev).not.toEqual(_rev);
            expect(newProps).toEqual(oldProps);
        });
    });

    describe("monitors nested collection", () => {
        beforeEach(async () => {
            wrapper = await mountProvider(DscProvider, {
                collection: nestedCollection,
                isRoot: false,
            });
        });

        test("should successfully mount and emit the pre-cached data", () => {
            expect(wrapper).toBeDefined();
            expect(wrapper.vm.dsc).toEqual(nestedCollection);
        });

        test("should emit updates as they occur", async () => {
            const { cached_at: old_cached_at, _rev: old_rev, ...oldProps } = wrapper.vm.dsc;

            // write a new field to the collection
            const fooVal = "abc123";
            nestedCollection.foo = fooVal;
            const updateResult = await cacheCollectionContent(nestedCollection);
            expect(updateResult.updated).toBe(true);

            // double-check it's really cached
            const lookup = await getCachedCollectionContent(updateResult.id);
            expect(lookup.foo).toEqual(fooVal);

            // wait for next update then check the foo val
            await wait(500);
            await wrapper.vm.$nextTick();

            // all same props except _rev and cached_at and foo
            const { cached_at, _rev, foo, ...newProps } = wrapper.vm.dsc;
            expect(foo).toEqual(fooVal);
            expect(old_cached_at).toBeLessThan(cached_at);
            expect(old_rev).not.toEqual(_rev);
            expect(newProps).toEqual(oldProps);
        });
    });
});
