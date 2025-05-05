import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia, defineStore, setActivePinia } from "pinia";
import { getLocalVue } from "tests/jest/helpers";
import { ref } from "vue";

import { fetchPluginHistoryItems } from "@/api/plugins";

import VisualizationCreate from "./VisualizationCreate.vue";
import FormCardSticky from "@/components/Form/FormCardSticky.vue";

jest.mock("vue-router/composables", () => ({
    useRouter: () => ({
        push: jest.fn(),
    }),
}));

jest.mock("@/api/plugins", () => ({
    fetchPlugin: jest.fn(() =>
        Promise.resolve({
            name: "scatterplot",
            description: "A great scatterplot plugin.",
            html: "Scatterplot Plugin",
            logo: "/logo.png",
            help: "Some help text",
            tags: ["tag1", "tag2"],
        })
    ),
    fetchPluginHistoryItems: jest.fn(() => Promise.resolve({ hdas: [] })),
}));

jest.mock("./utilities", () => ({
    getTestExtensions: jest.fn(() => ["txt"]),
    getTestUrls: jest.fn(() => [{ name: "Example", url: "https://example.com/data.txt" }]),
}));

let mockedStore;
jest.mock("@/stores/historyStore", () => ({
    useHistoryStore: () => mockedStore,
}));

const localVue = getLocalVue();

beforeEach(() => {
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
    fetchPluginHistoryItems.mockResolvedValueOnce({
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
    await wrapper.vm.$nextTick();
    const results = await wrapper.vm.doQuery();
    expect(results).toEqual([
        { id: "dataset1", name: "101: First Dataset" },
        { id: "dataset2", name: "102: Second Dataset" },
    ]);
});
