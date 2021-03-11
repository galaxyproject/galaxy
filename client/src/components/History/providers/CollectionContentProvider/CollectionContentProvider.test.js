import { NEVER } from "rxjs";
import { cacheContent, cacheCollectionContent, bulkCacheDscContent, wipeDatabase } from "../../caching";
import { SearchParams } from "../../model/SearchParams";
import CollectionContentProvider from "./CollectionContentProvider";
import { watchForChange, mountRenderless, getLocalVue } from "jest/helpers";

// sample data
import rawRootCollection from "../../test/json/DatasetCollection.json";
import rawCollection from "../../test/json/collectionContent.json";
import rawNestedCollection from "../../test/json/collectionContent.nested.json";

//#region Mocking

jest.mock("app");

jest.mock("../../caching");

import { loadCollectionContents } from "./loadCollectionContents";
jest.mock("./loadCollectionContents");

// Don't actually load anything, we're testing the cache response
loadCollectionContents.mockImplementation((config) => (src$) => {
    return NEVER;
});

//#endregion

const mountProvider = async (Component, propsData) => {
    const localVue = getLocalVue();
    const wrapper = mountRenderless(Component, { localVue, propsData });
    await wrapper.vm.$nextTick();
    return wrapper;
};

describe("CollectionContentProvider", () => {
    beforeEach(wipeDatabase);
    afterEach(wipeDatabase);

    let wrapper;
    afterEach(() => {
        if (wrapper) wrapper.destroy();
    });

    describe("initialization state", () => {
        let parent;

        // No loading
        beforeEach(async () => {
            parent = await cacheContent(rawRootCollection, true);
            wrapper = await mountProvider(CollectionContentProvider, {
                parent,
            });
        });

        test("should load with default values", async () => {
            await watchForChange({ vm: wrapper.vm, propName: "payload" });
            const { contents, startKey, topRows, bottomRows, totalMatches } = wrapper.vm.payload;

            // no content, so no startKey and empty contnets
            expect(contents).toEqual([]);
            expect(startKey).toEqual(undefined);

            // result derived entirely from parent
            expect(topRows).toEqual(0);
            expect(bottomRows).toEqual(parent.element_count);
            expect(totalMatches).toEqual(parent.element_count);

            // check passthrough vals
            expect(wrapper.vm.params).toEqual(new SearchParams());
            expect(wrapper.vm.pageSize).toEqual(SearchParams.pageSize);

            // check exposed methods
            expect(wrapper.vm.setScrollPos).toBeInstanceOf(Function);
        });
    });

    describe("should emit payload to reflect cached content", () => {
        let parent;
        let children;
        let grandChildren;

        // dummy up children to have matching ids
        const loadChildren = async (childProps, parent_url, returnDocs) => {
            const processed = childProps.map((props) => ({ parent_url, ...props }));
            return await bulkCacheDscContent(processed, returnDocs);
        };

        const loadCollectionTree = async () => {
            // root dsc
            parent = await cacheContent(rawRootCollection, true);

            // first layer of collection contents
            children = await loadChildren(rawCollection, parent.contents_url, true);

            // 2nd layer of nested collection contents
            grandChildren = [];
            for (const child of children) {
                const gc = await loadChildren(rawNestedCollection, child.contents_url, true);
                grandChildren.push(...gc);
            }
        };

        // No loading
        beforeEach(async () => {
            await loadCollectionTree();
            parent = await cacheContent(rawRootCollection, true);
            wrapper = await mountProvider(CollectionContentProvider, {
                parent,
            });
        });

        test("should load with pre-inserted cached children values", async () => {
            await watchForChange({ vm: wrapper.vm, propName: "payload" });
            const { contents, startKey, topRows, bottomRows, totalMatches } = wrapper.vm.payload;
            const { params, pageSize } = wrapper.vm;

            const ids = contents.map((o) => o.id);
            const childIds = children.map((o) => o.id);

            expect(ids).toEqual(childIds);
            expect(startKey).toBe(0);
            expect(topRows).toBe(0);
            expect(bottomRows).toBe(0); // length of all children < pagesize
            expect(totalMatches).toBe(children.length);
            expect(params).toEqual(new SearchParams());
            expect(pageSize).toEqual(SearchParams.pageSize);
        });

        // If the cache adds some content, should still be at the top, but the
        // bottomRows should change to reflect the new rows that are now
        // rendered in the contents

        test("should emit when a new item is inserted", async () => {
            await watchForChange({ vm: wrapper.vm, propName: "payload" });
            expect(wrapper.vm.payload.contents.length).toEqual(children.length);

            // clone and update a row
            const lastChild = children[children.length - 1];
            // eslint-disable-next-line no-unused-vars
            const { _id, _rev, ...existingProps } = lastChild;
            const newChild = {
                ...existingProps,
                element_index: existingProps.element_index + 1,
            };

            const insertResult = await cacheCollectionContent(newChild);
            expect(insertResult.updated).toBe(true);
            await watchForChange({ vm: wrapper.vm, propName: "payload" });

            const { contents } = wrapper.vm.payload;
            expect(contents.length).toBe(children.length + 1);
        });

        test("should emit when an existing item is updated", async () => {
            await watchForChange({ vm: wrapper.vm, propName: "payload" });

            const lastChild = children[children.length - 1];
            lastChild.foo = 123;

            const updatedResult = await cacheCollectionContent(lastChild);
            expect(updatedResult.updated).toBe(true);

            await watchForChange({ vm: wrapper.vm, propName: "payload" });

            const { contents } = wrapper.vm.payload;
            expect(contents.length).toBe(children.length);
        });
    });
});
