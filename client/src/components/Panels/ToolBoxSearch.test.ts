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

function withFavoriteEdamOperationTool(list: Tool[]) {
    return list.map((tool) =>
        tool.id === "liftOver1" ? ({ ...tool, edam_operations: ["operation_2409"] } as Tool) : tool,
    );
}

const SIGNED_IN_USER = {
    id: "user-id",
    username: "test-user",
    email: "test@example.org",
    isAnonymous: false,
} as any;

interface MountToolBoxOptions {
    /** Override the tool list used to populate `toolStore.toolsById` (default: `toolsList`). */
    tools?: Tool[];
    /** Override `toolStore.toolSections` (default: `{ default: toolsListInPanel }`). */
    toolSections?: Record<string, Record<string, Tool | ToolSection>>;
    /** Override `userStore.currentUser` — anonymous by default. */
    currentUser?: any;
    /** Override `userStore.currentPreferences.favorites` (default: `{ tools: [] }`). */
    favorites?: any;
    /** Set `userStore.recentTools` if provided. */
    recentTools?: string[];
    /** Override the active panel view (default: `"my_panel"`). */
    currentPanelView?: string;
    /** Install spies / extra store setup before `mount`. Runs after the defaults are applied. */
    setupStores?: (toolStore: ReturnType<typeof useToolStore>, userStore: ReturnType<typeof useUserStore>) => void;
}

function mountToolBox(options: MountToolBoxOptions = {}) {
    const pinia = createPinia();
    setActivePinia(pinia);

    const toolStore = useToolStore();
    vi.spyOn(toolStore, "fetchToolTagsMapping").mockResolvedValue();
    toolStore.toolsById = toToolsById(options.tools ?? toolsList);
    toolStore.toolSections = options.toolSections ?? { default: toolsListInPanel };
    toolStore.defaultPanelView = "default";
    toolStore.currentPanelView = options.currentPanelView ?? "my_panel";

    const userStore = useUserStore();
    if (options.currentUser !== undefined) {
        userStore.currentUser = options.currentUser;
    }
    userStore.currentPreferences = { favorites: options.favorites ?? { tools: [] } };
    if (options.recentTools !== undefined) {
        userStore.recentTools = options.recentTools;
    }

    options.setupStores?.(toolStore, userStore);

    const wrapper = mount(ToolBox as object, {
        pinia,
        localVue,
        router,
        propsData: {
            favoritesDefault: true,
            useSearchWorker: false,
        },
    });

    return { wrapper, toolStore, userStore };
}

describe("ToolBox search", () => {
    beforeEach(() => {
        vi.useFakeTimers();
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it("searches across toolbox when favorites are the default view and clears the query with Escape", async () => {
        const { wrapper } = mountToolBox({ favorites: { tools: ["liftOver1"] } });
        await flushPromises();

        expect(wrapper.find('[data-tool-id="liftOver1"]').exists()).toBe(true);

        const input = wrapper.find("input.search-query");
        await input.setValue("Zip");
        vi.advanceTimersByTime(250);
        await flushPromises();

        expect(wrapper.find('[data-tool-id="__ZIP_COLLECTION__"]').exists()).toBe(true);

        await input.trigger("keydown", { key: "Escape" });
        await flushPromises();

        expect((input.element as HTMLInputElement).value).toBe("");
        expect(wrapper.find('[data-tool-id="liftOver1"]').exists()).toBe(true);
    });

    it("shows empty favorites copy in My panel when no favorites are set", async () => {
        const { wrapper } = mountToolBox();
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
        const { wrapper } = mountToolBox({ favorites: { tools: ["__FILTER_FAILED_DATASETS__"] } });
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

    it("treats #favorites as a filter token for both explicit AND and shorthand searches", async () => {
        const { wrapper } = mountToolBox({
            favorites: { tools: ["__FILTER_FAILED_DATASETS__", "__ZIP_COLLECTION__"] },
        });
        await flushPromises();

        const input = wrapper.find("input.search-query");

        await input.setValue("#favorites AND Filter");
        vi.advanceTimersByTime(250);
        await flushPromises();

        let toolIds = wrapper.findAll("a[data-tool-id]").wrappers.map((item) => item.attributes("data-tool-id"));
        expect(toolIds).toEqual(["__FILTER_FAILED_DATASETS__"]);

        await input.setValue("#favorites Filter");
        vi.advanceTimersByTime(250);
        await flushPromises();

        toolIds = wrapper.findAll("a[data-tool-id]").wrappers.map((item) => item.attributes("data-tool-id"));
        expect(toolIds).toEqual(["__FILTER_FAILED_DATASETS__"]);

        await input.setValue("#favorites");
        vi.advanceTimersByTime(250);
        await flushPromises();

        toolIds = wrapper.findAll("a[data-tool-id]").wrappers.map((item) => item.attributes("data-tool-id"));
        expect(toolIds).toEqual(["__FILTER_FAILED_DATASETS__", "__ZIP_COLLECTION__"]);
    });

    it("collapses favorite results during search in My panel", async () => {
        const { wrapper } = mountToolBox({ favorites: { tools: ["__FILTER_FAILED_DATASETS__"] } });
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
        const { wrapper } = mountToolBox({
            favorites: { tools: ["__FILTER_FAILED_DATASETS__"] },
            recentTools: ["__ZIP_COLLECTION__", "__FILTER_EMPTY_DATASETS__"],
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
        const { wrapper, userStore } = mountToolBox({
            currentUser: SIGNED_IN_USER,
            favorites: {
                tools: ["__FILTER_FAILED_DATASETS__"],
                tags: ["genome_coordinates", "data_cleanup", "missing_tag"],
            },
            recentTools: ["__ZIP_COLLECTION__"],
            setupStores: (_toolStore, userStore) => {
                vi.spyOn(userStore, "removeFavoriteTag").mockImplementation(async (tag: string) => {
                    userStore.currentPreferences = {
                        favorites: {
                            tools: userStore.currentPreferences?.favorites.tools ?? [],
                            tags: (userStore.currentPreferences?.favorites.tags ?? []).filter(
                                (currentTag) => currentTag !== tag,
                            ),
                        },
                    };
                });
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

        const removeFavoriteTagButton = genomeCoordinatesSection?.find(
            '[data-description="favorite-tag-section-button"]',
        );
        expect(removeFavoriteTagButton?.exists()).toBe(true);
        await removeFavoriteTagButton?.trigger("click");
        await flushPromises();

        expect(userStore.removeFavoriteTag).toHaveBeenCalledWith("genome_coordinates");
        expect(
            wrapper.findAll(".toolSectionTitle").wrappers.some((item) => item.text().includes("genome_coordinates")),
        ).toBe(false);
    });

    it("renders top-level favorites in the stored mixed-type order", async () => {
        const { wrapper } = mountToolBox({
            currentUser: SIGNED_IN_USER,
            favorites: {
                tools: ["__FILTER_FAILED_DATASETS__"],
                tags: ["genome_coordinates"],
                order: [
                    { object_type: "tags", object_id: "genome_coordinates" },
                    { object_type: "tools", object_id: "__FILTER_FAILED_DATASETS__" },
                ],
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
        const { wrapper } = mountToolBox({
            favorites: { tools: ["__FILTER_FAILED_DATASETS__"] },
            recentTools: ["__ZIP_COLLECTION__"],
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
        const { wrapper } = mountToolBox({ recentTools: ["__ZIP_COLLECTION__"] });
        await flushPromises();

        const emptyState = wrapper.find(".tool-panel-empty");
        expect(emptyState.exists()).toBe(true);
        expect(emptyState.text()).toContain("You haven't favorited any tools yet.");
        const labels = wrapper.findAll(".tool-panel-label").wrappers.map((item) => item.text());
        expect(labels).toEqual(EXPECTED_LABELS);
    });

    it("shows one section per favorite EDAM operation and allows removing it from My Tools", async () => {
        const { wrapper, userStore } = mountToolBox({
            tools: withFavoriteEdamOperationTool(toolsList),
            toolSections: {
                default: toolsListInPanel,
                "ontology:edam_operations": {
                    operation_2409: {
                        model_class: "ToolSection",
                        id: "operation_2409",
                        name: "Data handling",
                        tools: ["liftOver1"],
                    },
                },
            },
            currentUser: SIGNED_IN_USER,
            favorites: { tools: [], tags: [], edam_operations: ["operation_2409"] },
            setupStores: (_toolStore, userStore) => {
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

    // Favorite EDAM topics use the same dispatch path as favorite EDAM
    // operations (`useToolPanelFavorites` returns parallel arrays consumed by
    // the same `favoriteEdam{Operation,Topic}Sections` computeds in
    // `MyToolsLanding.vue`). The operation case above already covers the
    // section-rendering and remove-button wiring; an analogous topic test
    // would only re-exercise the same code with a different enum value.

    // The lazy-load gate that decides *whether* to call `fetchToolTagsMapping`
    // is verified end-to-end via the favorite-tag rendering tests above (which
    // depend on a populated tag mapping) and via
    // ToolPanel.test.ts > "does not request tool tags during default tool
    // panel startup" (the negative case). An additional spy-only test here
    // would duplicate the gate check without exercising user-visible behavior.
});
