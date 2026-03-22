import { getLocalVue, injectTestRouter } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import toolsListUntyped from "@/components/ToolsView/testData/toolsList.json";
import toolsListInPanelUntyped from "@/components/ToolsView/testData/toolsListInPanel.json";
import { setMockConfig } from "@/composables/__mocks__/config";
import { type Tool, type ToolSection, useToolStore } from "@/stores/toolStore";
import { useUserStore } from "@/stores/userStore";

import ToolBox from "./ToolBox.vue";

vi.mock("@/composables/config");

setMockConfig({
    toolbox_auto_sort: true,
});

const toolsList = toolsListUntyped as unknown as Tool[];
const toolsListInPanel = toolsListInPanelUntyped as unknown as Record<string, Tool | ToolSection>;
const EXPECTED_LABELS = ["Recent tools", "Favorites"];

const localVue = getLocalVue();
const router = injectTestRouter(localVue);

function toToolsById(list: Tool[]) {
    return list.reduce(
        (acc, tool) => {
            acc[tool.id] = tool;
            return acc;
        },
        {} as Record<string, Tool>,
    );
}

function withoutToolTags(list: Tool[]) {
    return list.map(({ tool_tags, ...tool }) => tool as Tool);
}

function withFavoriteEdamOperationTool(list: Tool[]) {
    return list.map((tool) =>
        tool.id === "liftOver1" ? ({ ...tool, edam_operations: ["operation_2409"] } as Tool) : tool,
    );
}

function withFavoriteEdamTopicTool(list: Tool[]) {
    return list.map((tool) => (tool.id === "liftOver1" ? ({ ...tool, edam_topics: ["topic_0091"] } as Tool) : tool));
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

        const wrapper = mount(ToolBox as object, {
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

        const wrapper = mount(ToolBox as object, {
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

        const wrapper = mount(ToolBox as object, {
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

        const wrapper = mount(ToolBox as object, {
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
        await favoritesLabel?.trigger("click");
        await flushPromises();

        expect(wrapper.find('[data-tool-id="__FILTER_FAILED_DATASETS__"]').exists()).toBe(false);
        expect(wrapper.find('[data-tool-id="__FILTER_EMPTY_DATASETS__"]').exists()).toBe(true);
    });

    it("shows recent tools before favorites and allows clearing", async () => {
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

        const wrapper = mount(ToolBox as object, {
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
        expect(labels).toEqual(EXPECTED_LABELS);

        const toolIds = wrapper.findAll("a[data-tool-id]").wrappers.map((item) => item.attributes("data-tool-id"));
        expect(toolIds).toEqual(["__ZIP_COLLECTION__", "__FILTER_EMPTY_DATASETS__", "__FILTER_FAILED_DATASETS__"]);
        expect(wrapper.find('.tool-favorite-button[data-tool-id="__ZIP_COLLECTION__"]').exists()).toBe(true);

        await wrapper.find('[data-description="clear-recent-tools"]').trigger("click");
        await flushPromises();

        expect(wrapper.find('[data-description="clear-recent-tools"]').exists()).toBe(false);
        expect(wrapper.find('[data-tool-id="__ZIP_COLLECTION__"]').exists()).toBe(false);
    });

    it("shows one section per favorite tag in stored order and hides empty tag sections", async () => {
        const pinia = createPinia();
        setActivePinia(pinia);

        const toolStore = useToolStore();
        toolStore.toolsById = toToolsById(toolsList);
        toolStore.toolSections = { default: toolsListInPanel };
        toolStore.defaultPanelView = "default";
        toolStore.currentPanelView = "my_panel";

        const userStore = useUserStore();
        userStore.currentUser = {
            id: "user-id",
            username: "test-user",
            email: "test@example.org",
            isAnonymous: false,
        } as any;
        userStore.currentPreferences = {
            favorites: {
                tools: ["__FILTER_FAILED_DATASETS__"],
                tags: ["genome_coordinates", "data_cleanup", "missing_tag"],
            },
        };
        userStore.recentTools = ["__ZIP_COLLECTION__"];
        vi.spyOn(userStore, "removeFavoriteTag").mockImplementation(async (tag: string) => {
            userStore.currentPreferences = {
                favorites: {
                    tools: userStore.currentPreferences?.favorites.tools ?? [],
                    tags: (userStore.currentPreferences?.favorites.tags ?? []).filter((currentTag) => currentTag !== tag),
                },
            };
        });

        const wrapper = mount(ToolBox as object, {
            pinia,
            localVue,
            router,
            propsData: {
                favoritesDefault: true,
                useSearchWorker: false,
            },
        });

        await flushPromises();

        const tagSectionNames = wrapper.findAll(".toolSectionTitle .name").wrappers.map((item) => item.text().trim());
        expect(tagSectionNames).toEqual(["genome_coordinates", "data_cleanup"]);
        expect(wrapper.text()).not.toContain("missing_tag");

        const genomeCoordinatesSection = wrapper
            .findAll(".toolSectionTitle")
            .wrappers.find((item) => item.text().includes("genome_coordinates"));
        expect(genomeCoordinatesSection).toBeTruthy();
        expect(genomeCoordinatesSection?.find(".favorite-tag-section-icon").exists()).toBe(true);
        expect(genomeCoordinatesSection?.find(".favorite-tag-section-icon-open").exists()).toBe(false);
        await genomeCoordinatesSection?.find(".title-link").trigger("click");
        await flushPromises();
        expect(genomeCoordinatesSection?.find(".favorite-tag-section-icon-open").exists()).toBe(true);
        expect(wrapper.find('[data-tool-id="liftOver1"]').exists()).toBe(true);

        const dataCleanupSection = wrapper
            .findAll(".toolSectionTitle")
            .wrappers.find((item) => item.text().includes("data_cleanup"));
        expect(dataCleanupSection).toBeTruthy();
        await dataCleanupSection?.find(".title-link").trigger("click");
        await flushPromises();
        expect(wrapper.find('[data-tool-id="__FILTER_EMPTY_DATASETS__"]').exists()).toBe(true);

        expect(wrapper.findAll(".toolSectionTitle .name svg").length).toBeGreaterThan(0);

        const removeFavoriteTagButton = genomeCoordinatesSection?.find('[data-description="favorite-tag-section-button"]');
        expect(removeFavoriteTagButton?.exists()).toBe(true);
        await removeFavoriteTagButton?.trigger("click");
        await flushPromises();

        expect(userStore.removeFavoriteTag).toHaveBeenCalledWith("genome_coordinates");
        expect(
            wrapper
                .findAll(".toolSectionTitle")
                .wrappers.some((item) => item.text().includes("genome_coordinates")),
        ).toBe(false);
    });

    it("renders top-level favorites in the stored mixed-type order", async () => {
        const pinia = createPinia();
        setActivePinia(pinia);

        const toolStore = useToolStore();
        toolStore.toolsById = toToolsById(toolsList);
        toolStore.toolSections = { default: toolsListInPanel };
        toolStore.defaultPanelView = "default";
        toolStore.currentPanelView = "my_panel";

        const userStore = useUserStore();
        userStore.currentUser = {
            id: "user-id",
            username: "test-user",
            email: "test@example.org",
            isAnonymous: false,
        } as any;
        userStore.currentPreferences = {
            favorites: {
                tools: ["__FILTER_FAILED_DATASETS__"],
                tags: ["genome_coordinates"],
                order: [
                    { object_type: "tags", object_id: "genome_coordinates" },
                    { object_type: "tools", object_id: "__FILTER_FAILED_DATASETS__" },
                ],
            },
        };

        const wrapper = mount(ToolBox as object, {
            pinia,
            localVue,
            router,
            propsData: {
                favoritesDefault: true,
                useSearchWorker: false,
            },
        });

        await flushPromises();

        const menuText = wrapper.find(".toolMenu").text();
        expect(menuText.indexOf("genome_coordinates")).toBeGreaterThan(-1);
        expect(menuText.indexOf("Filter failed")).toBeGreaterThan(-1);
        expect(menuText.indexOf("genome_coordinates")).toBeLessThan(menuText.indexOf("Filter failed"));
        expect(wrapper.findAll('[data-description="favorite-top-level-drag-target"]').length).toBe(2);
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

        const wrapper = mount(ToolBox as object, {
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
        await favoritesLabel?.trigger("click");
        await flushPromises();

        expect(wrapper.find('[data-tool-id="__FILTER_FAILED_DATASETS__"]').exists()).toBe(false);
        expect(wrapper.find('[data-tool-id="__ZIP_COLLECTION__"]').exists()).toBe(true);
        expect(
            wrapper
                .findAll(".toolSectionTitle .name")
                .wrappers.some((item) => item.text().trim() === "genome_coordinates"),
        ).toBe(false);

        const recentLabel = wrapper
            .findAll(".tool-panel-label")
            .wrappers.find((item) => item.text().includes("Recent tools"));
        expect(recentLabel).toBeTruthy();
        await recentLabel?.trigger("click");
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

        const wrapper = mount(ToolBox as object, {
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
        expect(labels).toEqual(EXPECTED_LABELS);
    });

    it("does not show empty favorites copy when only favorite tags exist", async () => {
        const pinia = createPinia();
        setActivePinia(pinia);

        const toolStore = useToolStore();
        toolStore.toolsById = toToolsById(toolsList);
        toolStore.toolSections = { default: toolsListInPanel };
        toolStore.defaultPanelView = "default";
        toolStore.currentPanelView = "my_panel";

        const userStore = useUserStore();
        userStore.currentPreferences = { favorites: { tools: [], tags: ["data_cleanup"] } };

        const wrapper = mount(ToolBox as object, {
            pinia,
            localVue,
            router,
            propsData: {
                favoritesDefault: true,
                useSearchWorker: false,
            },
        });

        await flushPromises();

        expect(wrapper.find(".tool-panel-empty").exists()).toBe(false);
        expect(
            wrapper
                .findAll(".toolSectionTitle .name")
                .wrappers.some((item) => item.text().trim() === "data_cleanup"),
        ).toBe(true);
    });

    it("shows one section per favorite EDAM operation and allows removing it from My Tools", async () => {
        const pinia = createPinia();
        setActivePinia(pinia);

        const toolStore = useToolStore();
        toolStore.toolsById = toToolsById(withFavoriteEdamOperationTool(toolsList));
        toolStore.toolSections = {
            default: toolsListInPanel,
            "ontology:edam_operations": {
                operation_2409: {
                    model_class: "ToolSection",
                    id: "operation_2409",
                    name: "Data handling",
                    tools: ["liftOver1"],
                },
            },
        };
        toolStore.defaultPanelView = "default";
        toolStore.currentPanelView = "my_panel";

        const userStore = useUserStore();
        userStore.currentUser = {
            id: "user-id",
            username: "test-user",
            email: "test@example.org",
            isAnonymous: false,
        } as any;
        userStore.currentPreferences = { favorites: { tools: [], tags: [], edam_operations: ["operation_2409"] } };
        vi.spyOn(userStore, "removeFavoriteEdamOperation").mockImplementation(async (operationId: string) => {
            userStore.currentPreferences = {
                favorites: {
                    tools: userStore.currentPreferences?.favorites.tools ?? [],
                    tags: userStore.currentPreferences?.favorites.tags ?? [],
                    edam_operations: (userStore.currentPreferences?.favorites.edam_operations ?? []).filter(
                        (currentOperation) => currentOperation !== operationId,
                    ),
                },
            };
        });

        const wrapper = mount(ToolBox as object, {
            pinia,
            localVue,
            router,
            propsData: {
                favoritesDefault: true,
                useSearchWorker: false,
            },
        });

        await flushPromises();

        const operationSection = wrapper
            .findAll(".toolSectionTitle")
            .wrappers.find((item) => item.text().includes("Data handling"));
        expect(operationSection).toBeTruthy();
        expect(operationSection?.find(".favorite-edam-operation-section-icon").exists()).toBe(true);

        await operationSection?.find(".title-link").trigger("click");
        await flushPromises();
        expect(wrapper.find('[data-tool-id="liftOver1"]').exists()).toBe(true);

        const removeButton = operationSection?.find('[data-description="favorite-edam-operation-section-button"]');
        expect(removeButton?.exists()).toBe(true);
        await removeButton?.trigger("click");
        await flushPromises();

        expect(userStore.removeFavoriteEdamOperation).toHaveBeenCalledWith("operation_2409");
        expect(wrapper.text()).not.toContain("Data handling");
    });

    it("shows one section per favorite EDAM topic and allows removing it from My Tools", async () => {
        const pinia = createPinia();
        setActivePinia(pinia);

        const toolStore = useToolStore();
        toolStore.toolsById = toToolsById(withFavoriteEdamTopicTool(toolsList));
        toolStore.toolSections = {
            default: toolsListInPanel,
            "ontology:edam_topics": {
                topic_0091: {
                    model_class: "ToolSection",
                    id: "topic_0091",
                    name: "Data formats",
                    tools: ["liftOver1"],
                },
            },
        };
        toolStore.defaultPanelView = "default";
        toolStore.currentPanelView = "my_panel";

        const userStore = useUserStore();
        userStore.currentUser = {
            id: "user-id",
            username: "test-user",
            email: "test@example.org",
            isAnonymous: false,
        } as any;
        userStore.currentPreferences = { favorites: { tools: [], tags: [], edam_operations: [], edam_topics: ["topic_0091"] } };
        vi.spyOn(userStore, "removeFavoriteEdamTopic").mockImplementation(async (topicId: string) => {
            userStore.currentPreferences = {
                favorites: {
                    tools: userStore.currentPreferences?.favorites.tools ?? [],
                    tags: userStore.currentPreferences?.favorites.tags ?? [],
                    edam_operations: userStore.currentPreferences?.favorites.edam_operations ?? [],
                    edam_topics: (userStore.currentPreferences?.favorites.edam_topics ?? []).filter(
                        (currentTopic) => currentTopic !== topicId,
                    ),
                },
            };
        });

        const wrapper = mount(ToolBox as object, {
            pinia,
            localVue,
            router,
            propsData: {
                favoritesDefault: true,
                useSearchWorker: false,
            },
        });

        await flushPromises();

        const topicSection = wrapper.findAll(".toolSectionTitle").wrappers.find((item) => item.text().includes("Data formats"));
        expect(topicSection).toBeTruthy();
        expect(topicSection?.find(".favorite-edam-topic-section-icon").exists()).toBe(true);

        await topicSection?.find(".title-link").trigger("click");
        await flushPromises();
        expect(wrapper.find('[data-tool-id="liftOver1"]').exists()).toBe(true);

        const removeButton = topicSection?.find('[data-description="favorite-edam-topic-section-button"]');
        expect(removeButton?.exists()).toBe(true);
        await removeButton?.trigger("click");
        await flushPromises();

        expect(userStore.removeFavoriteEdamTopic).toHaveBeenCalledWith("topic_0091");
        expect(wrapper.text()).not.toContain("Data formats");
    });

    it("loads tag-enriched tools in My Tools when favorite tags exist and the catalog is tag-free", async () => {
        const pinia = createPinia();
        setActivePinia(pinia);

        const toolStore = useToolStore();
        toolStore.toolsById = toToolsById(withoutToolTags(toolsList));
        toolStore.toolSections = { default: toolsListInPanel };
        toolStore.defaultPanelView = "default";
        toolStore.currentPanelView = "my_panel";

        const fetchToolsMock = vi.spyOn(toolStore, "fetchTools").mockResolvedValue();

        const userStore = useUserStore();
        userStore.currentPreferences = { favorites: { tools: [], tags: ["data_cleanup"] } };

        mount(ToolBox as object, {
            pinia,
            localVue,
            router,
            propsData: {
                favoritesDefault: true,
                useSearchWorker: false,
            },
        });

        await flushPromises();

        expect(fetchToolsMock).toHaveBeenCalledWith(undefined, { includeToolTags: true });
    });

    it("does not load tag-enriched tools in My Tools when no favorite tags exist", async () => {
        const pinia = createPinia();
        setActivePinia(pinia);

        const toolStore = useToolStore();
        toolStore.toolsById = toToolsById(withoutToolTags(toolsList));
        toolStore.toolSections = { default: toolsListInPanel };
        toolStore.defaultPanelView = "default";
        toolStore.currentPanelView = "my_panel";

        const fetchToolsMock = vi.spyOn(toolStore, "fetchTools").mockResolvedValue();

        const userStore = useUserStore();
        userStore.currentPreferences = { favorites: { tools: [], tags: [] } };

        mount(ToolBox as object, {
            pinia,
            localVue,
            router,
            propsData: {
                favoritesDefault: true,
                useSearchWorker: false,
            },
        });

        await flushPromises();

        expect(fetchToolsMock).not.toHaveBeenCalled();
    });
});
