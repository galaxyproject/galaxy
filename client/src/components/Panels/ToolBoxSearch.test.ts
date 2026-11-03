import { composeStories } from "@storybook/vue3-vite";
import { type StoryOf, useStoryMount } from "@tests/vitest/stories";
import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { type ToolSection, useToolStore } from "@/stores/toolStore";
import { useUserStore } from "@/stores/userStore";

import { TOOLBOX_PANEL as toolsListInPanel, TOOLBOX_TOOLS as toolsList } from "./test_fixtures";
import * as ToolBoxStories from "./ToolBox.stories";

import ToolInstallationRequestForm from "../Tool/ToolInstallationRequestForm.vue";
import ToolBox from "./ToolBox.vue";

const stories = composeStories(ToolBoxStories);
const mountStory = useStoryMount();
const EXPECTED_LABELS = ["Recent tools", "Favorites"];

type SetupStores = (toolStore: ReturnType<typeof useToolStore>, userStore: ReturnType<typeof useUserStore>) => void;

async function mountToolBox(story: StoryOf<typeof stories>, setupStores?: SetupStores) {
    const root = mountStory(story);
    // The real configuration and viewer hash gate rendering and store initialization.
    const wrapper = await vi.waitFor(() => root.getComponent(ToolBox));
    const toolStore = useToolStore();
    const userStore = useUserStore();
    setupStores?.(toolStore, userStore);
    await flushPromises();
    return { wrapper, toolStore, userStore };
}

beforeEach(() => {
    vi.useFakeTimers();
});

afterEach(() => {
    vi.clearAllTimers();
    vi.useRealTimers();
    vi.restoreAllMocks();
});

describe("ToolBox search", () => {
    it("searches across toolbox when favorites are the default view and clears the query with Escape", async () => {
        const { wrapper } = await mountToolBox(stories.FavoriteGenomeTool);
        await flushPromises();

        expect(wrapper.find('[data-tool-id="liftOver1"]').exists()).toBe(true);

        const input = wrapper.get("input.search-query");
        await searchFor(wrapper, "Zip");

        expect(wrapper.find('[data-tool-id="__ZIP_COLLECTION__"]').exists()).toBe(true);

        await input.trigger("keydown", { key: "Escape" });
        await flushPromises();

        expect((input.element as HTMLInputElement).value).toBe("");
        expect(wrapper.find('[data-tool-id="liftOver1"]').exists()).toBe(true);
    });

    it("shows empty favorites copy in My panel when no favorites are set", async () => {
        const { wrapper } = await mountToolBox(stories.NoFavorites);
        await flushPromises();

        const emptyState = wrapper.find(".tool-panel-empty");
        expect(emptyState.exists()).toBe(true);
        expect(emptyState.text()).toContain("You haven't favorited any tools yet.");
        expect(emptyState.text()).toContain(`${toolsList.length} community curated tools.`);
        const discoverButton = emptyState.find('[data-description="discover-tools"]');
        expect(discoverButton.exists()).toBe(true);
        expect(discoverButton.text()).toBe("Discover Tools");

        const labels = wrapper.findAll(".tool-panel-label").map((item) => item.text());
        expect(labels).toEqual(["Favorites"]);
    });

    it("separates favorite results and shows favorite button for non-favorites during search", async () => {
        const { wrapper } = await mountToolBox(stories.FavoriteAndOtherFilters);
        await flushPromises();

        await searchFor(wrapper, "Filter");

        const labels = wrapper.findAll(".tool-panel-label").map((item) => item.text());
        expect(labels).toEqual(["Favorites", "Search results"]);

        const toolIds = wrapper.findAll("a[data-tool-id]").map((item) => item.attributes("data-tool-id"));
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
        const { wrapper } = await mountToolBox(stories.FavoriteCollections);
        await flushPromises();

        await searchFor(wrapper, "#favorites AND Filter");

        let toolIds = wrapper.findAll("a[data-tool-id]").map((item) => item.attributes("data-tool-id"));
        expect(toolIds).toEqual(["__FILTER_FAILED_DATASETS__"]);

        await searchFor(wrapper, "#favorites Filter");

        toolIds = wrapper.findAll("a[data-tool-id]").map((item) => item.attributes("data-tool-id"));
        expect(toolIds).toEqual(["__FILTER_FAILED_DATASETS__"]);

        await searchFor(wrapper, "#favorites");

        toolIds = wrapper.findAll("a[data-tool-id]").map((item) => item.attributes("data-tool-id"));
        expect(toolIds).toEqual(["__FILTER_FAILED_DATASETS__", "__ZIP_COLLECTION__"]);
    });

    it("keeps a favorited older tool version in #favorites and plain searches", async () => {
        const latestZipVersion = {
            ...toolsList.find((tool) => tool.id === "__ZIP_COLLECTION__")!,
            id: "toolshed.example.org/repos/dev/zip_collection/zip/1.0",
            version: "1.0",
        };
        const olderZipVersion = {
            ...latestZipVersion,
            id: "toolshed.example.org/repos/dev/zip_collection/zip/0.9",
            version: "0.9",
        };
        const { wrapper } = await mountToolBox(stories.NoFavorites, (toolStore, userStore) => {
            toolStore.toolsById = Object.fromEntries(
                [...toolsList, latestZipVersion, olderZipVersion].map((tool) => [tool.id, tool]),
            );
            toolStore.toolSections = {
                default: {
                    ...toolsListInPanel,
                    collection_operations: {
                        ...(toolsListInPanel.collection_operations as ToolSection),
                        tools: [latestZipVersion.id, olderZipVersion.id],
                    },
                },
            };
            userStore.currentPreferences = { favorites: { tools: [olderZipVersion.id] } };
        });
        await flushPromises();

        const input = wrapper.find("input.search-query");
        await input.setValue("#favorites Zip");
        vi.advanceTimersByTime(250);
        await flushPromises();

        const toolIds = wrapper.findAll("a[data-tool-id]").map((item) => item.attributes("data-tool-id"));
        expect(toolIds).toEqual([olderZipVersion.id]);

        await input.setValue("Zip");
        vi.advanceTimersByTime(250);
        await flushPromises();

        const plainToolIds = wrapper.findAll("a[data-tool-id]").map((item) => item.attributes("data-tool-id"));
        expect(plainToolIds).toContain(olderZipVersion.id);
        expect(plainToolIds).not.toContain(latestZipVersion.id);
    });

    it("updates the shown tool version in a plain search when favorites change", async () => {
        const latestZipVersion = {
            ...toolsList.find((tool) => tool.id === "__ZIP_COLLECTION__")!,
            id: "toolshed.example.org/repos/dev/zip_collection/zip/1.0",
            version: "1.0",
        };
        const olderZipVersion = {
            ...latestZipVersion,
            id: "toolshed.example.org/repos/dev/zip_collection/zip/0.9",
            version: "0.9",
        };
        const { wrapper, userStore } = await mountToolBox(stories.NoFavorites, (toolStore, userStore) => {
            toolStore.toolsById = Object.fromEntries(
                [...toolsList, latestZipVersion, olderZipVersion].map((tool) => [tool.id, tool]),
            );
            toolStore.toolSections = {
                default: {
                    ...toolsListInPanel,
                    collection_operations: {
                        ...(toolsListInPanel.collection_operations as ToolSection),
                        tools: [latestZipVersion.id, olderZipVersion.id],
                    },
                },
            };
            userStore.currentPreferences = { favorites: { tools: [] } };
        });
        await flushPromises();

        const input = wrapper.find("input.search-query");
        await input.setValue("Zip");
        vi.advanceTimersByTime(250);
        await flushPromises();

        const shownToolIds = () => wrapper.findAll("a[data-tool-id]").map((item) => item.attributes("data-tool-id"));
        expect(shownToolIds()).toContain(latestZipVersion.id);
        expect(shownToolIds()).not.toContain(olderZipVersion.id);

        userStore.currentPreferences = { favorites: { tools: [olderZipVersion.id] } };
        await flushPromises();

        expect(shownToolIds()).toContain(olderZipVersion.id);
        expect(shownToolIds()).not.toContain(latestZipVersion.id);

        userStore.currentPreferences = { favorites: { tools: [] } };
        await flushPromises();

        expect(shownToolIds()).toContain(latestZipVersion.id);
        expect(shownToolIds()).not.toContain(olderZipVersion.id);
    });

    it("collapses favorite results during search in My panel", async () => {
        const { wrapper } = await mountToolBox(stories.FavoriteAndOtherFilters);
        await flushPromises();

        await searchFor(wrapper, "Filter");

        expect(wrapper.find('[data-tool-id="__FILTER_FAILED_DATASETS__"]').exists()).toBe(true);
        expect(wrapper.find('[data-tool-id="__FILTER_EMPTY_DATASETS__"]').exists()).toBe(true);

        const favoritesLabel = wrapper.findAll(".tool-panel-label").find((item) => item.text().includes("Favorites"));
        expect(favoritesLabel).toBeTruthy();
        await favoritesLabel?.trigger("click");
        await flushPromises();

        expect(wrapper.find('[data-tool-id="__FILTER_FAILED_DATASETS__"]').exists()).toBe(false);
        expect(wrapper.find('[data-tool-id="__FILTER_EMPTY_DATASETS__"]').exists()).toBe(true);
    });

    it("shows recent tools before favorites and allows clearing", async () => {
        const { wrapper } = await mountToolBox(stories.RecentAndFavoriteCollections);
        await flushPromises();

        const labels = wrapper.findAll(".tool-panel-label").map((item) => item.text());
        expect(labels).toEqual(EXPECTED_LABELS);

        const toolIds = wrapper.findAll("a[data-tool-id]").map((item) => item.attributes("data-tool-id"));
        expect(toolIds).toEqual(["__ZIP_COLLECTION__", "__FILTER_EMPTY_DATASETS__", "__FILTER_FAILED_DATASETS__"]);
        expect(wrapper.find('.tool-favorite-button[data-tool-id="__ZIP_COLLECTION__"]').exists()).toBe(true);

        await wrapper.get('[data-description="clear-recent-tools"]').trigger("click");
        await flushPromises();

        expect(wrapper.find('[data-description="clear-recent-tools"]').exists()).toBe(false);
        expect(wrapper.find('[data-tool-id="__ZIP_COLLECTION__"]').exists()).toBe(false);
    });

    it("shows each recent tool once and ignores unknown IDs when recent tools contain duplicate or non-panel versions", async () => {
        const latestZipVersion = {
            ...toolsList.find((tool) => tool.id === "__ZIP_COLLECTION__")!,
            id: "toolshed.example.org/repos/dev/zip_collection/zip/1.0",
            version: "1.0",
        };
        const olderZipVersion = {
            ...latestZipVersion,
            id: "toolshed.example.org/repos/dev/zip_collection/zip/0.9",
            version: "0.9",
        };
        const { wrapper } = await mountToolBox(stories.RecentInstalledVersions, (toolStore, userStore) => {
            // Preserve the original invented version IDs only in this unit contract case.
            toolStore.toolsById = Object.fromEntries(
                [...toolsList, latestZipVersion, olderZipVersion].map((tool) => [tool.id, tool]),
            );
            toolStore.toolSections = {
                default: {
                    ...toolsListInPanel,
                    collection_operations: {
                        ...(toolsListInPanel.collection_operations as ToolSection),
                        tools: [latestZipVersion.id, "__FILTER_EMPTY_DATASETS__"],
                    },
                },
            };
            userStore.recentTools = [
                olderZipVersion.id,
                latestZipVersion.id,
                "__FILTER_EMPTY_DATASETS__",
                "unknown-recent-tool",
            ];
        });
        await flushPromises();

        const toolIds = wrapper.findAll("a[data-tool-id]").map((item) => item.attributes("data-tool-id"));
        expect(toolIds).toEqual([latestZipVersion.id, "__FILTER_EMPTY_DATASETS__"]);
    });

    it("shows one section per favorite tag in stored order and hides empty tag sections", async () => {
        const { wrapper, userStore } = await mountToolBox(stories.FavoriteTags);
        await flushPromises();

        const tagSectionNames = wrapper.findAll(".toolSectionTitle .name").map((item) => item.text().trim());
        expect(tagSectionNames).toEqual(["genome_coordinates", "data_cleanup"]);
        expect(wrapper.text()).not.toContain("missing_tag");

        const genomeCoordinatesSection = wrapper
            .findAll(".toolSectionTitle")
            .find((item) => item.text().includes("genome_coordinates"));
        expect(genomeCoordinatesSection).toBeTruthy();
        expect(genomeCoordinatesSection?.find(".favorite-tag-section-icon").exists()).toBe(true);
        expect(genomeCoordinatesSection?.find(".favorite-tag-section-icon-open").exists()).toBe(false);
        await genomeCoordinatesSection?.find(".title-link").trigger("click");
        await flushPromises();
        expect(genomeCoordinatesSection?.find(".favorite-tag-section-icon-open").exists()).toBe(true);
        expect(wrapper.find('[data-tool-id="liftOver1"]').exists()).toBe(true);

        const dataCleanupSection = wrapper
            .findAll(".toolSectionTitle")
            .find((item) => item.text().includes("data_cleanup"));
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
        expect(wrapper.findAll(".toolSectionTitle").some((item) => item.text().includes("genome_coordinates"))).toBe(
            false,
        );
    });

    it("does not include tagged tool versions that are outside the default panel", async () => {
        const oldVersion = {
            ...toolsList.find((tool) => tool.id === "__FILTER_EMPTY_DATASETS__")!,
            id: "__FILTER_EMPTY_DATASETS_OLD__",
            name: "Old Filter empty",
            version: "0.9.0",
        };
        const { wrapper } = await mountToolBox(stories.FavoriteCleanupTag, (toolStore) => {
            // A synthetic obsolete built-in ID remains a unit-only panel-membership case.
            toolStore.toolsById = Object.fromEntries([...toolsList, oldVersion].map((tool) => [tool.id, tool]));
        });
        await flushPromises();

        const dataCleanupSection = wrapper
            .findAll(".toolSectionTitle")
            .find((item) => item.text().includes("data_cleanup"));
        expect(dataCleanupSection).toBeTruthy();
        await dataCleanupSection?.find(".title-link").trigger("click");
        await flushPromises();

        expect(wrapper.find('[data-tool-id="__FILTER_EMPTY_DATASETS__"]').exists()).toBe(true);
        expect(wrapper.find('[data-tool-id="__FILTER_EMPTY_DATASETS_OLD__"]').exists()).toBe(false);
        expect(wrapper.text()).not.toContain("Old Filter empty");
    });

    it("renders top-level favorites in the stored mixed-type order", async () => {
        const { wrapper } = await mountToolBox(stories.OrderedTagAndToolFavorites);
        await flushPromises();

        const menuText = wrapper.find(".toolMenu").text();
        expect(menuText.indexOf("genome_coordinates")).toBeGreaterThan(-1);
        expect(menuText.indexOf("Filter failed")).toBeGreaterThan(-1);
        expect(menuText.indexOf("genome_coordinates")).toBeLessThan(menuText.indexOf("Filter failed"));
        expect(wrapper.findAll('[data-description="favorite-top-level-drag-target"]').length).toBe(2);
    });

    it("collapses favorites and recent tools sections on label click", async () => {
        const { wrapper } = await mountToolBox(stories.RecentCollectionAndFavoriteFilter);
        await flushPromises();

        expect(wrapper.find('[data-tool-id="__FILTER_FAILED_DATASETS__"]').exists()).toBe(true);
        expect(wrapper.find('[data-tool-id="__ZIP_COLLECTION__"]').exists()).toBe(true);

        const favoritesLabel = wrapper.findAll(".tool-panel-label").find((item) => item.text().includes("Favorites"));
        expect(favoritesLabel).toBeTruthy();
        await favoritesLabel?.trigger("click");
        await flushPromises();

        expect(wrapper.find('[data-tool-id="__FILTER_FAILED_DATASETS__"]').exists()).toBe(false);
        expect(wrapper.find('[data-tool-id="__ZIP_COLLECTION__"]').exists()).toBe(true);
        expect(
            wrapper.findAll(".toolSectionTitle .name").some((item) => item.text().trim() === "genome_coordinates"),
        ).toBe(false);

        const recentLabel = wrapper.findAll(".tool-panel-label").find((item) => item.text().includes("Recent tools"));
        expect(recentLabel).toBeTruthy();
        await recentLabel?.trigger("click");
        await flushPromises();

        expect(wrapper.find('[data-tool-id="__ZIP_COLLECTION__"]').exists()).toBe(false);
    });

    it("does not show empty favorites copy when recent tools exist", async () => {
        const { wrapper } = await mountToolBox(stories.RecentOnly);
        await flushPromises();

        const emptyState = wrapper.find(".tool-panel-empty");
        expect(emptyState.exists()).toBe(true);
        expect(emptyState.text()).toContain("You haven't favorited any tools yet.");
        const labels = wrapper.findAll(".tool-panel-label").map((item) => item.text());
        expect(labels).toEqual(EXPECTED_LABELS);
    });

    it("shows one section per favorite EDAM operation and allows removing it from My Tools", async () => {
        const { wrapper, userStore } = await mountToolBox(stories.FavoriteEdamOperation, (toolStore, userStore) => {
            // Preserve the original annotation contract; the standalone story uses shipped Mapper annotations.
            toolStore.toolsById = Object.fromEntries(
                toolsList.map((tool) => [
                    tool.id,
                    tool.id === "liftOver1" ? { ...tool, edam_operations: ["operation_2409"] } : tool,
                ]),
            );
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
            userStore.currentPreferences = { favorites: { tools: [], tags: [], edam_operations: ["operation_2409"] } };
        });
        await flushPromises();

        const operationSection = wrapper
            .findAll(".toolSectionTitle")
            .find((item) => item.text().includes("Data handling"));
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

/** A default-panel toolbox whose story owns its viewer and configuration. */
async function mountDefaultPanelToolBox(story: StoryOf<typeof stories> = stories.InstallationRequestsAvailable) {
    return (await mountToolBox(story)).wrapper;
}

async function searchFor(wrapper: Awaited<ReturnType<typeof mountToolBox>>["wrapper"], query: string) {
    await wrapper.get("input.search-query").setValue(query);
    vi.advanceTimersByTime(250);
    await flushPromises();
}

const REQUEST_BUTTON = '[data-description="request tool installation button"]';

describe("ToolBox — Request Tool Installation button", () => {
    it("is hidden when search returns results", async () => {
        const wrapper = await mountDefaultPanelToolBox();
        await searchFor(wrapper, "Filter");

        expect(wrapper.find(REQUEST_BUTTON).exists()).toBe(false);
    });

    it("is visible when search returns no results", async () => {
        const wrapper = await mountDefaultPanelToolBox();
        await searchFor(wrapper, "xyznonexistenttool123");

        expect(wrapper.find(".alert-warning").exists()).toBe(true);
        expect(wrapper.find(REQUEST_BUTTON).exists()).toBe(true);
    });

    it("is hidden when enable_tool_installation_request_form config is false", async () => {
        const wrapper = await mountDefaultPanelToolBox(stories.InstallationRequestsDisabled);
        await searchFor(wrapper, "xyznonexistenttool123");

        expect(wrapper.find(".alert-warning").exists()).toBe(true);
        expect(wrapper.find(REQUEST_BUTTON).exists()).toBe(false);
    });

    it("is hidden when the notification system is off, which the request needs", async () => {
        const wrapper = await mountDefaultPanelToolBox(stories.NotificationsDisabled);
        await searchFor(wrapper, "xyznonexistenttool123");

        expect(wrapper.find(".alert-warning").exists()).toBe(true);
        expect(wrapper.find(REQUEST_BUTTON).exists()).toBe(false);
    });

    it("is hidden for anonymous users even when search returns no results", async () => {
        const wrapper = await mountDefaultPanelToolBox(stories.AnonymousDefaultPanel);
        await searchFor(wrapper, "xyznonexistenttool123");

        expect(wrapper.find(".alert-warning").exists()).toBe(true);
        expect(wrapper.find(REQUEST_BUTTON).exists()).toBe(false);
    });

    it("is hidden in workflow mode even when search returns no results", async () => {
        const wrapper = await mountDefaultPanelToolBox(stories.WorkflowToolbox);
        await searchFor(wrapper, "xyznonexistenttool123");

        expect(wrapper.find(".alert-warning").exists()).toBe(true);
        expect(wrapper.find(REQUEST_BUTTON).exists()).toBe(false);
    });

    it("opens the tool installation request form modal when clicked", async () => {
        const wrapper = await mountDefaultPanelToolBox();
        await searchFor(wrapper, "xyznonexistenttool123");

        const button = wrapper.find(REQUEST_BUTTON);
        expect(button.exists()).toBe(true);

        await button.trigger("click");
        await flushPromises();

        const requestForm = wrapper.findComponent(ToolInstallationRequestForm);
        expect(requestForm.props("show")).toBe(true);
    });
});
