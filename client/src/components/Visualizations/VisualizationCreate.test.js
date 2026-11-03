import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia, defineStore } from "pinia";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { fetchPlugin, fetchPluginHistoryItems } from "@/api/plugins";
import { sanitizeHtml } from "@/directives/sanitizeHtml";

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

const useFakeHistoryStore = defineStore("history", {
    state: () => ({ currentHistoryId: "fake-history-id" }),
});
let pinia;
let mockedStore;
vi.mock("@/stores/historyStore", () => ({
    useHistoryStore: () => mockedStore,
}));

enableAutoUnmount(afterEach);

async function mountVisualization() {
    const wrapper = mount(VisualizationCreate, {
        global: withPlugins(getLocalVue(), pinia),
        propsData: { visualization: "scatterplot" },
        stubs: { SelectionField: true },
    });
    await flushPromises();
    return wrapper;
}

beforeEach(() => {
    vi.clearAllMocks();
    pinia = createPinia();
    mockedStore = useFakeHistoryStore(pinia);

    // Reset default mock implementations
    vi.mocked(fetchPlugin).mockResolvedValue({
        params: { dataset_id: { required: true } },
        ...PLUGIN,
    });
    vi.mocked(fetchPluginHistoryItems).mockResolvedValue({ hdas: [] });
});

it("renders plugin info after load", async () => {
    const wrapper = await mountVisualization();
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
    const wrapper = await mountVisualization();
    const results = await wrapper.findComponent({ name: "SelectionField" }).props("objectQuery")();
    expect(results).toEqual([
        { id: "dataset1", name: "101: First Dataset" },
        { id: "dataset2", name: "102: Second Dataset" },
    ]);
});

it("displays create new visualization option if dataset is not required", async () => {
    vi.mocked(fetchPlugin).mockResolvedValueOnce(PLUGIN);
    const wrapper = await mountVisualization();
    const results = await wrapper.findComponent({ name: "SelectionField" }).props("objectQuery")();
    expect(results).toEqual([{ id: "", name: "Open visualization..." }]);
});

it("renders plugin help markdown through v-sanitize-html with the links profile", async () => {
    vi.mocked(fetchPlugin).mockResolvedValue({ ...PLUGIN, help: "See [docs](https://example.org) <b>now</b>" });
    vi.mocked(sanitizeHtml).mockClear();
    await mountVisualization();

    const call = vi.mocked(sanitizeHtml).mock.calls.find(([html]) => html?.includes(">docs</a>"));
    expect(call?.[1]).toBe("links");
    expect(call?.[0]).toContain('target="_blank"');
    expect(call?.[0]).toContain("&lt;b&gt;now&lt;/b&gt;");
});
