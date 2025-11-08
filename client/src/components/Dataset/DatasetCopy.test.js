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
        stubs: { RouterLink: { template: "<a><slot /></a>" } },
    });
}

async function setupBase(histories, contents) {
    GalaxyApi().GET.mockResolvedValueOnce({ data: histories, error: null });
    GalaxyApi().GET.mockResolvedValueOnce({ data: contents, error: null });
    const wrapper = mountComponent();
    await flushPromises();
    const checkbox = wrapper.find("input[type='checkbox']");
    await checkbox.setChecked(true);
    return wrapper;
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

    await wrapper.find("button.btn-primary").trigger("click");
    await flushPromises();

    expect(wrapper.text()).toMatch(/1 item[s]? copied/);
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

    const buttons = wrapper.findAll("button.btn-outline-primary");

    await buttons.at(0).trigger("click");
    await flushPromises();
    await wrapper.vm.$nextTick();

    let sel = wrapper.vm.sourceContentSelection?.value;
    if (!sel) {
        sel = wrapper.vm.sourceContentSelection;
    } // handle non-ref binding
    expect(sel["dataset|d1"]).toBe(true);
    expect(sel["dataset|d2"]).toBe(true);

    await buttons.at(1).trigger("click");
    await flushPromises();
    await wrapper.vm.$nextTick();

    sel = wrapper.vm.sourceContentSelection?.value || wrapper.vm.sourceContentSelection;
    expect(sel["dataset|d1"]).toBe(false);
    expect(sel["dataset|d2"]).toBe(false);
});

it("shows success for single existing target", async () => {
    const histories = [{ id: "h1", name: "H1" }];
    const contents = [{ id: "d1", name: "X", hid: 1, history_content_type: "dataset" }];
    GalaxyApi().POST.mockResolvedValueOnce({ data: { history_ids: ["h1"] }, error: null });
    GalaxyApi().GET.mockResolvedValueOnce({ data: contents, error: null });

    const wrapper = await setupBase(histories, contents);
    await wrapper.find("button.btn-primary").trigger("click");
    await flushPromises();

    expect(wrapper.text()).toMatch(/1 item[s]? copied to/);
    expect(wrapper.text()).toContain("1 history");
});

it("shows success for multiple target histories", async () => {
    const histories = [
        { id: "h1", name: "H1" },
        { id: "h2", name: "H2" },
    ];
    const contents = [{ id: "d1", name: "X", hid: 1, history_content_type: "dataset" }];
    GalaxyApi().POST.mockResolvedValueOnce({ data: { history_ids: ["h1", "h2"] }, error: null });
    GalaxyApi().GET.mockResolvedValueOnce({ data: contents, error: null });

    const wrapper = await setupBase(histories, contents);
    wrapper.vm.targetMultiSelections = { h1: true, h2: true };
    await wrapper.vm.$nextTick();

    await wrapper.find("button.btn-primary").trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("2 histories");
});

it("shows success for new history creation", async () => {
    const histories = [{ id: "h1", name: "H1" }];
    const contents = [{ id: "d1", name: "X", hid: 1, history_content_type: "dataset" }];
    GalaxyApi().POST.mockResolvedValueOnce({ data: { history_ids: ["h2"] }, error: null });
    GalaxyApi().GET.mockResolvedValueOnce({ data: contents, error: null });

    const wrapper = await setupBase(histories, contents);
    await wrapper.find("input[data-description='copy history name']").setValue("New History");
    await wrapper.find("button.btn-primary").trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("1 item copied to");
    expect(wrapper.text()).toContain("New History");
});
