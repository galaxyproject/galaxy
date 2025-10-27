import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia, defineStore, setActivePinia } from "pinia";
import { beforeEach, expect, it, vi } from "vitest";
import { ref } from "vue";

import { fetchPlugin, fetchPluginHistoryItems } from "@/api/plugins";

import VisualizationCreate from "./VisualizationCreate.vue";
import FormCardSticky from "@/components/Form/FormCardSticky.vue";

const PLUGIN = {
    name: "scatterplot",
    description: "A great scatterplot plugin.",
    html: "Scatterplot Plugin",
    logo: "/logo.png",
    help: "Some help text",
    tags: ["tag1", "tag2"],
};

vi.mock("vue-router", () => ({
    useRouter: () => ({
        push: vi.fn(),
    }),
}));

vi.mock("@/api/plugins", () => ({
    fetchPlugin: vi.fn(() =>
        Promise.resolve({
            params: { dataset_id: { required: true } },
            ...PLUGIN,
        }),
    ),
    fetchPluginHistoryItems: vi.fn(() => Promise.resolve({ hdas: [] })),
}));

let mockedStore;
vi.mock("@/stores/historyStore", () => ({
    useHistoryStore: () => mockedStore,
}));

const localVue = getLocalVue();

beforeEach(() => {
    vi.clearAllMocks();
    setActivePinia(createPinia());
    const useFakeHistoryStore = defineStore("history", {
        state: () => ({
            currentHistoryId: ref("fake-history-id"),
        }),
    });
    mockedStore = useFakeHistoryStore();

    // prevent tooltip from throwing warning
    const el = document.createElement("div");
    el.id = "vis-create-ext";
    document.body.appendChild(el);

    // Reset default mock implementations
    vi.mocked(fetchPlugin).mockResolvedValue({
        params: { dataset_id: { required: true } },
        ...PLUGIN,
    });
    vi.mocked(fetchPluginHistoryItems).mockResolvedValue({ hdas: [] });
});

it("renders plugin info after load", async () => {
    const wrapper = mount(VisualizationCreate, {
        localVue,
        propsData: {
            visualization: "scatterplot",
        },
    });
    await flushPromises();
    await wrapper.vm.$nextTick();
    const sticky = wrapper.findComponent(FormCardSticky);
    expect(sticky.exists()).toBe(true);
    expect(sticky.props("description")).toBe("A great scatterplot plugin.");
    expect(sticky.props("logo")).toBe("/logo.png");
    expect(sticky.props("name")).toBe("Scatterplot Plugin");
    expect(wrapper.text()).toContain("Help");
    expect(wrapper.text()).toContain("tag1");
    expect(wrapper.text()).toContain("tag2");
});

it("adds hid to dataset names when fetching history items", async () => {
    vi.mocked(fetchPluginHistoryItems).mockResolvedValueOnce({
        hdas: [
            { id: "dataset1", hid: 101, name: "First Dataset" },
            { id: "dataset2", hid: 102, name: "Second Dataset" },
        ],
    });
    const wrapper = mount(VisualizationCreate, {
        localVue,
        propsData: {
            visualization: "scatterplot",
        },
    });
    await flushPromises();
    const results = await wrapper.vm.doQuery();
    expect(results).toEqual([
        { id: "dataset1", name: "101: First Dataset" },
        { id: "dataset2", name: "102: Second Dataset" },
    ]);
});

it("displays create new visualization option if dataset is not required", async () => {
    vi.mocked(fetchPlugin).mockResolvedValueOnce(PLUGIN);
    const wrapper = mount(VisualizationCreate, {
        propsData: {
            visualization: "scatterplot",
        },
    });
    await flushPromises();
    const results = await wrapper.vm.doQuery();
    expect(results).toEqual([{ id: "", name: "Open visualization..." }]);
});
