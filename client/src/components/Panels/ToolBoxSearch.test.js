import { getLocalVue, injectTestRouter } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import toolsList from "@/components/ToolsView/testData/toolsList.json";
import toolsListInPanel from "@/components/ToolsView/testData/toolsListInPanel.json";
import { setMockConfig } from "@/composables/__mocks__/config";
import { useToolStore } from "@/stores/toolStore";
import { useUserStore } from "@/stores/userStore";

import ToolBox from "./ToolBox.vue";

vi.mock("@/composables/config");

setMockConfig({
    toolbox_auto_sort: true,
});

const localVue = getLocalVue();
const router = injectTestRouter(localVue);

function toToolsById(list) {
    return list.reduce((acc, tool) => {
        acc[tool.id] = tool;
        return acc;
    }, {});
}

describe("ToolBox search", () => {
    beforeEach(() => {
        vi.useFakeTimers();
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it("searches across toolbox when favorites are the default view", async () => {
        const pinia = createPinia();
        setActivePinia(pinia);

        const toolStore = useToolStore();
        toolStore.toolsById = toToolsById(toolsList);
        toolStore.toolSections = { default: toolsListInPanel };
        toolStore.defaultPanelView = "default";
        toolStore.currentPanelView = "my_panel";

        const userStore = useUserStore();
        userStore.currentPreferences = { favorites: { tools: ["liftOver1"] } };

        const wrapper = mount(ToolBox, {
            pinia,
            localVue,
            router,
            propsData: {
                favoritesDefault: true,
                useSearchWorker: false,
            },
        });

        await flushPromises();

        expect(wrapper.find('[data-tool-id="liftOver1"]').exists()).toBe(true);

        const input = wrapper.find("input.search-query");
        await input.setValue("Zip");
        vi.advanceTimersByTime(250);
        await flushPromises();

        expect(wrapper.find('[data-tool-id="__ZIP_COLLECTION__"]').exists()).toBe(true);
    });

    it("shows empty favorites copy in My panel when no favorites are set", async () => {
        const pinia = createPinia();
        setActivePinia(pinia);

        const toolStore = useToolStore();
        toolStore.toolsById = toToolsById(toolsList);
        toolStore.toolSections = { default: toolsListInPanel };
        toolStore.defaultPanelView = "default";
        toolStore.currentPanelView = "my_panel";

        const userStore = useUserStore();
        userStore.currentPreferences = { favorites: { tools: [] } };

        const wrapper = mount(ToolBox, {
            pinia,
            localVue,
            router,
            propsData: {
                favoritesDefault: true,
                useSearchWorker: false,
            },
        });

        await flushPromises();

        const emptyState = wrapper.find(".tool-panel-empty");
        expect(emptyState.exists()).toBe(true);
        expect(emptyState.text()).toContain("You haven't favorited any tools yet.");
        expect(emptyState.text()).toContain(`${toolsList.length} community curated tools.`);
        const discoverButton = emptyState.find('[data-description="discover-tools"]');
        expect(discoverButton.exists()).toBe(true);
        expect(discoverButton.text()).toBe("Discover Tools");

        const labels = wrapper.findAll(".tool-panel-label").wrappers.map((item) => item.text());
        expect(labels).toEqual(["Favorites"]);
    });

    it("separates favorite results and shows favorite button for non-favorites during search", async () => {
        const pinia = createPinia();
        setActivePinia(pinia);

        const toolStore = useToolStore();
        toolStore.toolsById = toToolsById(toolsList);
        toolStore.toolSections = { default: toolsListInPanel };
        toolStore.defaultPanelView = "default";
        toolStore.currentPanelView = "my_panel";

        const userStore = useUserStore();
        userStore.currentPreferences = { favorites: { tools: ["__FILTER_FAILED_DATASETS__"] } };

        const wrapper = mount(ToolBox, {
            pinia,
            localVue,
            router,
            propsData: {
                favoritesDefault: true,
                useSearchWorker: false,
            },
        });

        await flushPromises();

        const input = wrapper.find("input.search-query");
        await input.setValue("Filter");
        vi.advanceTimersByTime(250);
        await flushPromises();

        const labels = wrapper.findAll(".tool-panel-label").wrappers.map((item) => item.text());
        expect(labels).toEqual(["Favorites", "Search results"]);

        const toolIds = wrapper.findAll("a[data-tool-id]").wrappers.map((item) => item.attributes("data-tool-id"));
        expect(toolIds).toEqual(["__FILTER_FAILED_DATASETS__", "__FILTER_EMPTY_DATASETS__"]);

        expect(wrapper.find('.tool-favorite-button[data-tool-id="__FILTER_EMPTY_DATASETS__"]').exists()).toBe(true);
        expect(wrapper.find('.tool-favorite-button-hover[data-tool-id="__FILTER_EMPTY_DATASETS__"]').exists()).toBe(
            false,
        );
        expect(wrapper.find('.tool-favorite-button[data-tool-id="__FILTER_FAILED_DATASETS__"]').exists()).toBe(true);
        expect(wrapper.find('.tool-favorite-button-hover[data-tool-id="__FILTER_FAILED_DATASETS__"]').exists()).toBe(
            true,
        );
    });

    it("collapses favorite results during search in My panel", async () => {
        const pinia = createPinia();
        setActivePinia(pinia);

        const toolStore = useToolStore();
        toolStore.toolsById = toToolsById(toolsList);
        toolStore.toolSections = { default: toolsListInPanel };
        toolStore.defaultPanelView = "default";
        toolStore.currentPanelView = "my_panel";

        const userStore = useUserStore();
        userStore.currentPreferences = { favorites: { tools: ["__FILTER_FAILED_DATASETS__"] } };

        const wrapper = mount(ToolBox, {
            pinia,
            localVue,
            router,
            propsData: {
                favoritesDefault: true,
                useSearchWorker: false,
            },
        });

        await flushPromises();

        const input = wrapper.find("input.search-query");
        await input.setValue("Filter");
        vi.advanceTimersByTime(250);
        await flushPromises();

        expect(wrapper.find('[data-tool-id="__FILTER_FAILED_DATASETS__"]').exists()).toBe(true);
        expect(wrapper.find('[data-tool-id="__FILTER_EMPTY_DATASETS__"]').exists()).toBe(true);

        const favoritesLabel = wrapper
            .findAll(".tool-panel-label")
            .wrappers.find((item) => item.text().includes("Favorites"));
        expect(favoritesLabel).toBeTruthy();
        await favoritesLabel.trigger("click");
        await flushPromises();

        expect(wrapper.find('[data-tool-id="__FILTER_FAILED_DATASETS__"]').exists()).toBe(false);
        expect(wrapper.find('[data-tool-id="__FILTER_EMPTY_DATASETS__"]').exists()).toBe(true);
    });

    it("shows recent tools under favorites and allows clearing", async () => {
        const pinia = createPinia();
        setActivePinia(pinia);

        const toolStore = useToolStore();
        toolStore.toolsById = toToolsById(toolsList);
        toolStore.toolSections = { default: toolsListInPanel };
        toolStore.defaultPanelView = "default";
        toolStore.currentPanelView = "my_panel";

        const userStore = useUserStore();
        userStore.currentPreferences = { favorites: { tools: ["__FILTER_FAILED_DATASETS__"] } };
        userStore.recentTools = ["__ZIP_COLLECTION__", "__FILTER_EMPTY_DATASETS__"];

        const wrapper = mount(ToolBox, {
            pinia,
            localVue,
            router,
            propsData: {
                favoritesDefault: true,
                useSearchWorker: false,
            },
        });

        await flushPromises();

        const labels = wrapper.findAll(".tool-panel-label").wrappers.map((item) => item.text());
        expect(labels).toEqual(["Favorites", "Recent tools"]);

        const toolIds = wrapper.findAll("a[data-tool-id]").wrappers.map((item) => item.attributes("data-tool-id"));
        expect(toolIds).toEqual(["__FILTER_FAILED_DATASETS__", "__ZIP_COLLECTION__", "__FILTER_EMPTY_DATASETS__"]);
        expect(wrapper.find('.tool-favorite-button[data-tool-id="__ZIP_COLLECTION__"]').exists()).toBe(true);

        await wrapper.find('[data-description="clear-recent-tools"]').trigger("click");
        await flushPromises();

        expect(wrapper.find('[data-description="clear-recent-tools"]').exists()).toBe(false);
        expect(wrapper.find('[data-tool-id="__ZIP_COLLECTION__"]').exists()).toBe(false);
    });

    it("collapses favorites and recent tools sections on label click", async () => {
        const pinia = createPinia();
        setActivePinia(pinia);

        const toolStore = useToolStore();
        toolStore.toolsById = toToolsById(toolsList);
        toolStore.toolSections = { default: toolsListInPanel };
        toolStore.defaultPanelView = "default";
        toolStore.currentPanelView = "my_panel";

        const userStore = useUserStore();
        userStore.currentPreferences = { favorites: { tools: ["__FILTER_FAILED_DATASETS__"] } };
        userStore.recentTools = ["__ZIP_COLLECTION__"];

        const wrapper = mount(ToolBox, {
            pinia,
            localVue,
            router,
            propsData: {
                favoritesDefault: true,
                useSearchWorker: false,
            },
        });

        await flushPromises();

        expect(wrapper.find('[data-tool-id="__FILTER_FAILED_DATASETS__"]').exists()).toBe(true);
        expect(wrapper.find('[data-tool-id="__ZIP_COLLECTION__"]').exists()).toBe(true);

        const favoritesLabel = wrapper
            .findAll(".tool-panel-label")
            .wrappers.find((item) => item.text().includes("Favorites"));
        expect(favoritesLabel).toBeTruthy();
        await favoritesLabel.trigger("click");
        await flushPromises();

        expect(wrapper.find('[data-tool-id="__FILTER_FAILED_DATASETS__"]').exists()).toBe(false);
        expect(wrapper.find('[data-tool-id="__ZIP_COLLECTION__"]').exists()).toBe(true);

        const recentLabel = wrapper
            .findAll(".tool-panel-label")
            .wrappers.find((item) => item.text().includes("Recent tools"));
        expect(recentLabel).toBeTruthy();
        await recentLabel.trigger("click");
        await flushPromises();

        expect(wrapper.find('[data-tool-id="__ZIP_COLLECTION__"]').exists()).toBe(false);
    });

    it("does not show empty favorites copy when recent tools exist", async () => {
        const pinia = createPinia();
        setActivePinia(pinia);

        const toolStore = useToolStore();
        toolStore.toolsById = toToolsById(toolsList);
        toolStore.toolSections = { default: toolsListInPanel };
        toolStore.defaultPanelView = "default";
        toolStore.currentPanelView = "my_panel";

        const userStore = useUserStore();
        userStore.currentPreferences = { favorites: { tools: [] } };
        userStore.recentTools = ["__ZIP_COLLECTION__"];

        const wrapper = mount(ToolBox, {
            pinia,
            localVue,
            router,
            propsData: {
                favoritesDefault: true,
                useSearchWorker: false,
            },
        });

        await flushPromises();

        const emptyState = wrapper.find(".tool-panel-empty");
        expect(emptyState.exists()).toBe(true);
        expect(emptyState.text()).toContain("You haven't favorited any tools yet.");
        const labels = wrapper.findAll(".tool-panel-label").wrappers.map((item) => item.text());
        expect(labels).toEqual(["Favorites", "Recent tools"]);
    });
});
