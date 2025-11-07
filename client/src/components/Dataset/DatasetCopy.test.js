import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { getLocalVue } from "tests/jest/helpers";

import { GalaxyApi } from "@/api";

import DatasetCopy from "./DatasetCopy.vue";

jest.mock("@/api", () => {
    const get = jest.fn();
    const post = jest.fn();
    return {
        GalaxyApi: jest.fn(() => ({
            GET: get,
            POST: post,
        })),
    };
});

const localVue = getLocalVue();

beforeEach(() => {
    jest.clearAllMocks();
});

function mountComponent() {
    return mount(DatasetCopy, {
        localVue,
        directives: { localize: () => {} },
    });
}

it("loads histories and contents on mount", async () => {
    GalaxyApi().GET.mockResolvedValueOnce({
        data: [
            { id: "h1", name: "History One" },
            { id: "h2", name: "History Two" },
        ],
        error: null,
    });

    GalaxyApi().GET.mockResolvedValueOnce({
        data: [
            { id: "d1", name: "A", hid: 1, history_content_type: "dataset" },
            { id: "d2", name: "B", hid: 2, history_content_type: "collection" },
        ],
        error: null,
    });

    const wrapper = mountComponent();
    await flushPromises();

    expect(wrapper.text()).toContain("History One");
    expect(wrapper.text()).toContain("History Two");
    expect(wrapper.text()).toContain("A");
    expect(wrapper.text()).toContain("B");
});

it("copies selected items and shows success", async () => {
    GalaxyApi().GET.mockResolvedValueOnce({
        data: [{ id: "h1", name: "H1" }],
        error: null,
    });

    GalaxyApi().GET.mockResolvedValueOnce({
        data: [{ id: "d1", name: "X", hid: 1, history_content_type: "dataset" }],
        error: null,
    });

    GalaxyApi().POST.mockResolvedValueOnce({
        data: { history_ids: ["h1"] },
        error: null,
    });

    GalaxyApi().GET.mockResolvedValueOnce({
        data: [{ id: "d1", name: "X", hid: 1, history_content_type: "dataset" }],
        error: null,
    });

    const wrapper = mountComponent();
    await flushPromises();

    const checkbox = wrapper.find("input[type='checkbox']");
    await checkbox.setChecked(true);

    const target = wrapper.findAll("span").wrappers.find((n) => n.text() === "H1");
    if (target) {
        await target.trigger("click");
    }

    await wrapper.find("button.btn-primary").trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("1 item copied to 1 history");

    const payload = GalaxyApi().POST.mock.calls[0][1].body;
    expect(payload.source_history).toBe("h1");
    expect(payload.source_content).toEqual([{ id: "d1", type: "dataset" }]);
});

it("shows error when nothing selected", async () => {
    GalaxyApi().GET.mockResolvedValueOnce({
        data: [{ id: "h1", name: "H1" }],
        error: null,
    });

    GalaxyApi().GET.mockResolvedValueOnce({
        data: [],
        error: null,
    });

    const wrapper = mountComponent();
    await flushPromises();

    await wrapper.find("button.btn-primary").trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("Please select Datasets and Collections.");
});

it("handles API error from copy call", async () => {
    GalaxyApi().GET.mockResolvedValueOnce({
        data: [{ id: "h1", name: "H1" }],
        error: null,
    });

    GalaxyApi().GET.mockResolvedValueOnce({
        data: [{ id: "d1", name: "X", hid: 1, history_content_type: "dataset" }],
        error: null,
    });

    GalaxyApi().POST.mockResolvedValueOnce({
        data: null,
        error: { err_msg: "Copy failed" },
    });

    const wrapper = mountComponent();
    await flushPromises();

    const checkbox = wrapper.find("input[type='checkbox']");
    await checkbox.setChecked(true);

    const target = wrapper.findAll("span").wrappers.find((n) => n.text() === "H1");
    if (target) {
        await target.trigger("click");
    }

    await wrapper.find("button.btn-primary").trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("Copy failed");
});

it("toggleAll selects and unselects all", async () => {
    GalaxyApi().GET.mockResolvedValueOnce({
        data: [{ id: "h1", name: "H1" }],
        error: null,
    });

    GalaxyApi().GET.mockResolvedValueOnce({
        data: [
            { id: "d1", name: "X", hid: 1, history_content_type: "dataset" },
            { id: "d2", name: "Y", hid: 2, history_content_type: "dataset" },
        ],
        error: null,
    });

    const wrapper = mountComponent();
    await flushPromises();
    await wrapper.vm.$nextTick();

    const buttons = wrapper.findAll("button.btn-outline-primary");

    await buttons.at(0).trigger("click");
    await flushPromises();
    await wrapper.vm.$nextTick();

    const afterSelectAll = wrapper.vm.$data.sourceContentSelection || wrapper.vm.sourceContentSelection || {};
    expect(afterSelectAll["dataset|d1"]).toBe(true);
    expect(afterSelectAll["dataset|d2"]).toBe(true);

    await buttons.at(1).trigger("click");
    await flushPromises();
    await wrapper.vm.$nextTick();

    const afterUnselectAll = wrapper.vm.$data.sourceContentSelection || wrapper.vm.sourceContentSelection || {};
    expect(afterUnselectAll["dataset|d1"]).toBe(false);
    expect(afterUnselectAll["dataset|d2"]).toBe(false);
});
