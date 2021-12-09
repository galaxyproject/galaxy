/* eslint-disable no-unused-vars */
import { mountRenderless, watchForChange } from "jest/helpers";
import { wipeDatabase } from "components/providers/History/caching";
import { cacheContent, cacheCollectionContent } from "components/providers/History/caching";
import { DatasetCollection } from "components/History/model/DatasetCollection";
import DscProvider from "./DscProvider";

// test data as root-level collections
// import rootContents from "../../test/json/historyContentWithCollection.json";

// test data for a nested collection
// import nestedContents from "../../test/json/collectionContent.json";

import { testCollection, testNestedCollection } from "components/History/test/testCollection";

// Imports dependencies without firing up worker because that blows with Jest
jest.mock("app");
jest.mock("components/providers/History/caching");

beforeEach(wipeDatabase);
afterEach(wipeDatabase);

describe("DscProvider", () => {
    let wrapper;

    afterEach(async () => {
        if (wrapper) {
            wrapper.destroy();
        }
        wrapper = undefined;
    });

    describe("monitors a root collection (direct child of a history)", () => {
        let rootCollection;

        beforeEach(async () => {
            rootCollection = await cacheContent(testCollection, true);
            expect(rootCollection).toBeDefined();

            wrapper = await mountRenderless(DscProvider, {
                propsData: {
                    collection: rootCollection,
                    isRoot: true,
                },
            });
            expect(wrapper).toBeDefined();

            const { newVal: dsc } = await watchForChange({ vm: wrapper.vm, propName: "dsc" });
            expect(dsc._id).toEqual(rootCollection._id);
        });

        afterEach(() => {
            rootCollection = undefined;
        });

        test("should successfully mount and emit the pre-cached data", () => {
            // compare output to input prop, should be the same because we didn't change anything
            const root = new DatasetCollection(rootCollection);
            const emitted = new DatasetCollection(wrapper.vm.dsc);
            const { _rev, cached_at, ...originalProps } = root;
            const { _rev: new_rev, cached_at: new_cached_at, ...newProps } = emitted;
            expect(originalProps).toEqual(newProps);
        });

        test("should emit updates as they occur", async () => {
            const { cached_at: old_cached_at, _rev: old_rev, ...oldProps } = wrapper.vm.dsc;

            // write a new field to the collection
            const fooVal = "abc123";
            rootCollection.foo = fooVal;
            const updatedRoot = await cacheContent(rootCollection, true);
            expect(updatedRoot.foo).toEqual(fooVal);

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
        let nestedCollection;
        const parent_url = "/foo";

        beforeEach(async () => {
            // cache a collection root
            nestedCollection = await cacheCollectionContent(testNestedCollection, true);
            expect(nestedCollection).toBeDefined();

            // mount and monitor
            wrapper = await mountRenderless(DscProvider, {
                propsData: {
                    collection: nestedCollection,
                    isRoot: false,
                },
            });
            expect(wrapper).toBeDefined();

            const { newVal: dsc } = await watchForChange({ vm: wrapper.vm, propName: "dsc" });
            expect(dsc._id).toEqual(nestedCollection._id);
        });

        afterEach(() => {
            nestedCollection = undefined;
        });

        test("should successfully mount and emit the pre-cached data", () => {
            const orig = new DatasetCollection(nestedCollection);
            const emitted = new DatasetCollection(wrapper.vm.dsc);
            const { _rev, cached_at, ...originalProps } = orig;
            const { _rev: new_rev, cached_at: new_cached_at, ...newProps } = emitted;
            expect(originalProps).toEqual(newProps);
        });

        test("should emit updates as they occur", async () => {
            const { cached_at: old_cached_at, _rev: old_rev, ...oldProps } = wrapper.vm.dsc;

            // write a new field to the collection
            const fooVal = "abc123";
            nestedCollection.foo = fooVal;
            const updateResult = await cacheCollectionContent(nestedCollection, true);
            expect(updateResult.foo).toEqual(fooVal);

            // wait for next update then check the foo val
            // await wait(500);
            await wrapper.vm.$nextTick();

            // all same props except _rev and cached_at and foo
            expect(wrapper.vm.dsc.foo).toEqual(fooVal);
        });
    });
});
