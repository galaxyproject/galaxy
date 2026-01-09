import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia } from "pinia";
import { beforeEach, expect, it } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import { useHistoryStore } from "@/stores/historyStore";

import DatasetCopy from "./DatasetCopy.vue";

const { server, http } = useServerMock();
const localVue = getLocalVue();
const pinia = createPinia();

beforeEach(() => {
    server.resetHandlers();
});

function mountComponent() {
    const wrapper = mount(DatasetCopy, {
        global: localVue,
        directives: { localize: () => {} },
        stubs: { RouterLink: { template: "<a><slot /></a>" } },
        pinia,
    });
    const historyStore = useHistoryStore();
    historyStore.setCurrentHistoryId("h1");
    return wrapper;
}

async function setupBase(histories, contents) {
    server.use(
        http.get("/api/histories", ({ response }) => response(200).json(histories)),
        http.get("/api/histories/{history_id}", ({ params, response }) =>
            response(200).json({ id: params.history_id, name: "H1" }),
        ),
        http.get("/api/histories/{history_id}/contents", ({ response }) => response(200).json(contents)),
    );
    const wrapper = mountComponent();
    await flushPromises();
    const checkbox = wrapper.find("input[type='checkbox']");
    await checkbox.setChecked(true);
    return wrapper;
}

it("loads histories and contents on mount", async () => {
    server.use(
        http.get("/api/histories", ({ response }) =>
            response(200).json([
                { id: "h1", name: "History One" },
                { id: "h2", name: "History Two" },
            ]),
        ),
        http.get("/api/histories/{history_id}", ({ params, response }) =>
            response(200).json({ id: params.history_id, name: `History ${params.history_id}` }),
        ),
        http.get("/api/histories/{history_id}/contents", ({ response }) =>
            response(200).json([
                { id: "d1", name: "A", hid: 1, history_content_type: "dataset" },
                { id: "d2", name: "B", hid: 2, history_content_type: "collection" },
            ]),
        ),
    );
    const wrapper = mountComponent();
    await flushPromises();
    expect(wrapper.text()).toContain("History One");
    expect(wrapper.text()).toContain("History Two");
    expect(wrapper.text()).toContain("A");
    expect(wrapper.text()).toContain("B");
});

it("copies selected items and shows success", async () => {
    server.use(
        http.get("/api/histories", ({ response }) => response(200).json([{ id: "h1", name: "H1" }])),
        http.get("/api/histories/{history_id}", ({ params, response }) =>
            response(200).json({ id: params.history_id, name: "H1" }),
        ),
        http.get("/api/histories/{history_id}/contents", ({ response }) =>
            response(200).json([{ id: "d1", name: "X", hid: 1, history_content_type: "dataset" }]),
        ),
        http.post("/api/histories/{history_id}/copy_contents", async ({ request, response }) => {
            const body = await request.json();
            if (body.source_content.length > 0) {
                return response(200).json({ history_ids: ["h1"] });
            }
            return response(400).json({ err_msg: "No data" });
        }),
    );
    const wrapper = mountComponent();
    await flushPromises();
    const checkbox = wrapper.find("input[type='checkbox']");
    await checkbox.setChecked(true);
    await wrapper.find("button.btn-primary").trigger("click");
    await flushPromises();
    expect(wrapper.text()).toMatch(/1 item[s]? copied/);
});

it("shows error when nothing selected", async () => {
    server.use(
        http.get("/api/histories", ({ response }) => response(200).json([{ id: "h1", name: "H1" }])),
        http.get("/api/histories/{history_id}", ({ params, response }) =>
            response(200).json({ id: params.history_id, name: "H1" }),
        ),
        http.get("/api/histories/{history_id}/contents", ({ response }) => response(200).json([])),
    );
    const wrapper = mountComponent();
    await flushPromises();
    await wrapper.find("button.btn-primary").trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("Please select datasets and collections.");
});

it("handles API error from copy call", async () => {
    server.use(
        http.get("/api/histories", ({ response }) => response(200).json([{ id: "h1", name: "H1" }])),
        http.get("/api/histories/{history_id}", ({ params, response }) =>
            response(200).json({ id: params.history_id, name: "H1" }),
        ),
        http.get("/api/histories/{history_id}/contents", ({ response }) =>
            response(200).json([{ id: "d1", name: "X", hid: 1, history_content_type: "dataset" }]),
        ),
        http.post("/api/histories/{history_id}/copy_contents", ({ response }) =>
            response(500).json({ err_msg: "Copy failed" }),
        ),
    );
    const wrapper = mountComponent();
    await flushPromises();
    const checkbox = wrapper.find("input[type='checkbox']");
    await checkbox.setChecked(true);
    await wrapper.find("button.btn-primary").trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("Copy failed");
});

it("toggleAll selects and unselects all", async () => {
    server.use(
        http.get("/api/histories", ({ response }) => response(200).json([{ id: "h1", name: "H1" }])),
        http.get("/api/histories/{history_id}", ({ params, response }) =>
            response(200).json({ id: params.history_id, name: "H1" }),
        ),
        http.get("/api/histories/{history_id}/contents", ({ response }) =>
            response(200).json([
                { id: "d1", name: "X", hid: 1, history_content_type: "dataset" },
                { id: "d2", name: "Y", hid: 2, history_content_type: "dataset" },
            ]),
        ),
    );
    const wrapper = mountComponent();
    await flushPromises();
    const buttons = wrapper.findAll("button.btn-outline-primary");
    await buttons.at(0).trigger("click");
    await flushPromises();
    const sel1 = wrapper.vm.sourceContentSelection?.value || wrapper.vm.sourceContentSelection;
    expect(sel1["dataset|d1"]).toBe(true);
    expect(sel1["dataset|d2"]).toBe(true);
    await buttons.at(1).trigger("click");
    await flushPromises();
    const sel2 = wrapper.vm.sourceContentSelection?.value || wrapper.vm.sourceContentSelection;
    expect(sel2["dataset|d1"]).toBe(false);
    expect(sel2["dataset|d2"]).toBe(false);
});

it("shows success for single existing target", async () => {
    server.use(
        http.get("/api/histories", ({ response }) => response(200).json([{ id: "h1", name: "H1" }])),
        http.get("/api/histories/{history_id}", ({ params, response }) =>
            response(200).json({ id: params.history_id, name: "H1" }),
        ),
        http.get("/api/histories/{history_id}/contents", ({ response }) =>
            response(200).json([{ id: "d1", name: "X", hid: 1, history_content_type: "dataset" }]),
        ),
        http.post("/api/histories/{history_id}/copy_contents", ({ response }) =>
            response(200).json({ history_ids: ["h1"] }),
        ),
    );
    const wrapper = mountComponent();
    await flushPromises();
    const checkbox = wrapper.find("input[type='checkbox']");
    await checkbox.setChecked(true);
    await wrapper.find("button.btn-primary").trigger("click");
    await flushPromises();
    expect(wrapper.text()).toMatch(/1 item[s]? copied to/);
    expect(wrapper.text()).toContain("H1");
});

it("shows success for multiple target histories", async () => {
    server.use(
        http.get("/api/histories", ({ response }) =>
            response(200).json([
                { id: "h1", name: "H1" },
                { id: "h2", name: "H2" },
            ]),
        ),
        http.get("/api/histories/{history_id}", ({ params, response }) =>
            response(200).json({ id: params.history_id, name: `History ${params.history_id}` }),
        ),
        http.get("/api/histories/{history_id}/contents", ({ response }) =>
            response(200).json([{ id: "d1", name: "X", hid: 1, history_content_type: "dataset" }]),
        ),
        http.post("/api/histories/{history_id}/copy_contents", ({ response }) =>
            response(200).json({ history_ids: ["h1", "h2"] }),
        ),
    );
    const wrapper = mountComponent();
    await flushPromises();
    const checkbox = wrapper.find("input[type='checkbox']");
    await checkbox.setChecked(true);
    wrapper.vm.targetMultiSelections = { h1: true, h2: true };
    await wrapper.vm.$nextTick();
    await wrapper.find("button.btn-primary").trigger("click");
    await flushPromises();
    expect(wrapper.text()).toMatch(/1 item[s]? copied to/);
    expect(wrapper.text()).toContain("H1");
    expect(wrapper.text()).toContain("H2");
});

it("shows success for new history creation", async () => {
    server.use(
        http.get("/api/histories", ({ response }) => response(200).json([{ id: "h1", name: "H1" }])),
        http.get("/api/histories/{history_id}", ({ params, response }) =>
            response(200).json({ id: params.history_id, name: "H1" }),
        ),
        http.get("/api/histories/{history_id}/contents", ({ response }) =>
            response(200).json([{ id: "d1", name: "X", hid: 1, history_content_type: "dataset" }]),
        ),
        http.post("/api/histories/{history_id}/copy_contents", ({ response }) =>
            response(200).json({ history_ids: ["h2"] }),
        ),
    );
    const wrapper = await setupBase(
        [{ id: "h1", name: "H1" }],
        [{ id: "d1", name: "X", hid: 1, history_content_type: "dataset" }],
    );
    await wrapper.find("input[data-description='copy history name']").setValue("New History");
    await wrapper.find("button.btn-primary").trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("1 item copied to");
    expect(wrapper.text()).toContain("New History");
});
