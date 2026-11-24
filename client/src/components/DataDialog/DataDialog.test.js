import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Model } from "./model";
import { Services } from "./services";

import DataDialog from "./DataDialog.vue";
import SelectionDialog from "@/components/SelectionDialog/SelectionDialog.vue";

vi.mock("app");

const mockOptions = {
    callback: () => {},
    history: "history",
    modalStatic: true,
};

describe("model.js", () => {
    let result = null;
    it("Model operations for single, no format", () => {
        const model = new Model();
        try {
            model.add({ idx: 1 });
            throw Error("Accepted invalid record.");
        } catch (error) {
            expect(error.message).toBe("Invalid record with no <id>.");
        }
        model.add({ id: 1 });
        expect(model.count()).toBe(1);
        expect(model.exists(1)).toBe(true);
        model.add({ id: 2, tag: "tag" });
        expect(model.count()).toBe(1);
        expect(model.exists(1)).toBe(false);
        expect(model.exists(2)).toBe(true);
        result = model.finalize();
        expect(result.id).toBe(2);
        expect(result.tag).toBe("tag");
    });

    it("Model operations for multiple, with format", () => {
        const model = new Model({ multiple: true, format: "tag" });
        model.add({ id: 1, tag: "tag_1" });
        expect(model.count()).toBe(1);
        model.add({ id: 2, tag: "tag_2" });
        expect(model.count()).toBe(2);
        result = model.finalize();
        expect(result.length).toBe(2);
        expect(result[0]).toBe("tag_1");
        expect(result[1]).toBe("tag_2");
        model.add({ id: 1 });
        expect(model.count()).toBe(1);
        result = model.finalize();
        expect(result[0]).toBe("tag_2");
    });
});

describe("model.js clear", () => {
    it("drops every selected record", () => {
        const model = new Model({ multiple: true });
        model.add({ id: 1 });
        model.add({ id: 2 });
        model.clear();
        expect(model.count()).toBe(0);
        expect(model.exists(1)).toBe(false);
        expect(model.finalize()).toEqual([]);
    });
});

describe("services/Services:isDataset", () => {
    it("Test dataset identifier", () => {
        const services = new Services(mockOptions);
        expect(services.isDataset({})).toBe(false);
        expect(services.isDataset({ history_content_type: "dataset" })).toBe(true);
        expect(services.isDataset({ history_content_type: "xyz" })).toBe(false);
        expect(services.isDataset({ type: "file" })).toBe(true);
        expect(services.getRecord({ hid: 1, history_content_type: "dataset" }).isLeaf).toBe(true);
        expect(services.getRecord({ hid: 2, history_content_type: "xyz" }).isLeaf).toBe(false);
        expect(services.getRecord({ type: "file" }).isLeaf).toBe(true);
    });
});

describe("services.js/Services", () => {
    it("Test data population from raw data", () => {
        const rawData = {
            hid: 1,
            id: 1,
            history_id: 0,
            name: "name_1",
        };
        const services = new Services(mockOptions);
        const items = services.getItems(rawData);
        expect(items.length).toBe(1);
        const first = items[0];
        expect(first.label).toBe("1: name_1");
        expect(first.download).toBe("http://localhost:/api/histories/0/contents/1/display");
    });
});

describe("DataDialog.vue", () => {
    let wrapper;

    afterEach(() => {
        vi.restoreAllMocks();
    });
    /*
    const rawData = [
        {
            id: 1,
            hid: 1,
            name: "dataset_1",
            history_content_type: "dataset",
        },
        {
            id: 2,
            name: "dataset_2",
            type: "file",
        },
        {
            id: 3,
            hid: 3,
            name: "collection_1",
            history_content_type: "dataset_collection",
        },
    ];
    */

    it("loads correctly, embeds a SelectionDialog", () => {
        wrapper = shallowMount(DataDialog, {
            propsData: mockOptions,
            stubs: {
                Icon: true,
            },
        });
        expect(wrapper.findComponent(SelectionDialog).exists()).toBe(true);
        // Cannot get nested slot templates to render into the wrapper
        ///  Lots of open issues around this
        ///  ... Maybe because named slots have many issues
        //   - https://github.com/vuejs/vue-test-utils/issues?utf8=%E2%9C%93&q=is%3Aissue+is%3Aopen+slot
        //   ... Maybe because it is a modal and no longer inside the template DOM element?
        //   - https://github.com/vuejs/vue-test-utils/issues/1333

        // expect(wrapper.find(".fa-spinner").text()).to.equals("");
        // expect(wrapper.contains(".fa-spinner")).to.equals(true);
        // await wrapper.vm.$nextTick();
        // expect(wrapper.findAll(".fa-folder").length).to.equals(2);
        // expect(wrapper.findAll(".fa-file-o").length).to.equals(2);

        // SelectionDialog DOM properties are tested now in SelectionDialog.test.js however.
    });

    it("navigates back through nested folders to the history root", async () => {
        const folder = { id: "folder", label: "Folder", url: "/api/libraries/library/contents", isLeaf: false };
        const nestedFolder = {
            id: "nested",
            label: "Nested folder",
            url: "/api/folders/nested/contents",
            isLeaf: false,
        };
        const get = vi
            .spyOn(Services.prototype, "get")
            .mockResolvedValueOnce([folder])
            .mockResolvedValueOnce([nestedFolder])
            .mockResolvedValueOnce([])
            .mockResolvedValueOnce([nestedFolder])
            .mockResolvedValueOnce([folder]);
        wrapper = shallowMount(DataDialog, {
            propsData: { ...mockOptions, library: false },
        });
        await flushPromises();
        const dialog = () => wrapper.findComponent(SelectionDialog);
        const historyUrl = get.mock.calls[0][0];
        expect(dialog().props("undoShow")).toBe(false);

        dialog().vm.$emit("onClick", folder);
        await flushPromises();
        expect(get).toHaveBeenLastCalledWith(folder.url);
        expect(dialog().props("undoShow")).toBe(true);

        dialog().vm.$emit("onOpen", nestedFolder);
        await flushPromises();
        expect(get).toHaveBeenLastCalledWith(nestedFolder.url);

        dialog().vm.$emit("onUndo");
        await flushPromises();
        expect(get).toHaveBeenLastCalledWith(folder.url);
        expect(dialog().props("items")).toEqual([nestedFolder]);
        expect(dialog().props("undoShow")).toBe(true);

        dialog().vm.$emit("onUndo");
        await flushPromises();
        expect(get).toHaveBeenLastCalledWith(historyUrl);
        expect(dialog().props("items")).toEqual([folder]);
        expect(dialog().props("undoShow")).toBe(false);
        expect(get).toHaveBeenCalledTimes(5);
    });

    it("reloads the listing from the new history when the history prop changes", async () => {
        const get = vi.spyOn(Services.prototype, "get").mockResolvedValue([]);
        const requestedUrls = () => get.mock.calls.map(([url]) => url);
        wrapper = shallowMount(DataDialog, {
            propsData: { ...mockOptions, history: "first" },
            stubs: { Icon: true },
        });
        await flushPromises();
        expect(requestedUrls()).toHaveLength(1);
        expect(requestedUrls()[0]).toContain("api/histories/first/contents");

        await wrapper.setProps({ history: "second" });
        await flushPromises();
        expect(requestedUrls()).toHaveLength(2);
        expect(requestedUrls()[1]).toContain("api/histories/second/contents");
        get.mockRestore();
    });

    it("clears the selection when the history prop changes", async () => {
        const leaf = { id: "dataset_1", label: "1: dataset", isLeaf: true };
        vi.spyOn(Services.prototype, "get").mockResolvedValue([leaf]);
        wrapper = shallowMount(DataDialog, {
            propsData: { ...mockOptions, history: "first", library: false, multiple: true },
            stubs: { Icon: true },
        });
        await flushPromises();
        const dialog = () => wrapper.findComponent(SelectionDialog);
        const rowVariant = () => dialog().props("items")[0]._rowVariant;
        expect(dialog().props("disableOk")).toBe(true);

        dialog().vm.$emit("onClick", leaf);
        await flushPromises();
        expect(dialog().props("disableOk")).toBe(false);
        expect(rowVariant()).toBe("success");

        await wrapper.setProps({ history: "second" });
        await flushPromises();
        expect(dialog().props("disableOk")).toBe(true);
        // The model, not just hasValue, must be empty: formatRows reads it for the reloaded rows
        expect(rowVariant()).toBe("default");
    });

    it("ignores a slow response for the previous history", async () => {
        const deferred = () => {
            const handlers = {};
            const promise = new Promise((resolve, reject) => Object.assign(handlers, { resolve, reject }));
            return { promise, ...handlers };
        };
        const pending = [deferred(), deferred()];
        let call = 0;
        const get = vi.spyOn(Services.prototype, "get").mockImplementation(() => pending[call++].promise);
        wrapper = shallowMount(DataDialog, {
            propsData: { ...mockOptions, history: "first", library: false },
            stubs: { Icon: true },
        });
        await wrapper.setProps({ history: "second" });
        expect(get).toHaveBeenCalledTimes(2);

        pending[1].resolve([{ id: "second_1", label: "second dataset", isLeaf: true }]);
        await flushPromises();
        pending[0].resolve([{ id: "first_1", label: "first dataset", isLeaf: true }]);
        await flushPromises();

        const labels = wrapper
            .findComponent(SelectionDialog)
            .props("items")
            .map((item) => item.label);
        expect(labels).toEqual(["second dataset"]);
    });

    it("ignores a failed response for the previous history", async () => {
        const leaf = { id: "second_1", label: "second dataset", isLeaf: true };
        let rejectFirst;
        let call = 0;
        vi.spyOn(Services.prototype, "get").mockImplementation(() => {
            if (call++ === 0) {
                return new Promise((_, reject) => {
                    rejectFirst = reject;
                });
            }
            return Promise.resolve([leaf]);
        });
        wrapper = shallowMount(DataDialog, {
            propsData: { ...mockOptions, history: "first", library: false },
            stubs: { Icon: true },
        });
        await wrapper.setProps({ history: "second" });
        await flushPromises();
        rejectFirst(new Error("stale failure"));
        await flushPromises();

        expect(wrapper.findComponent(SelectionDialog).props("errorMessage")).toBe("");
    });
});
