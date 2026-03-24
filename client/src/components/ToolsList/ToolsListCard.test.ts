import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { setActivePinia } from "pinia";
import { describe, expect, it, vi } from "vitest";

import { useToolStore } from "@/stores/toolStore";
import { useUserStore } from "@/stores/userStore";

import ToolsListCard from "./ToolsListCard.vue";

vi.mock("./useToolsListCardActions", () => ({
    useToolsListCardActions: () => ({
        favoriteToolAction: {
            label: "Favorite Tool",
            title: "Add to Favorites",
            handler: vi.fn(),
        },
        toolsListCardPrimaryActions: [],
        toolsListCardSecondaryActions: [],
        openUploadIfNeeded: vi.fn(),
    }),
}));

const localVue = getLocalVue();

function mountCard(options?: {
    currentUser?: any;
    favorites?: { tools: string[]; tags: string[]; edam_operations: string[]; edam_topics: string[] };
}) {
    const pinia = createTestingPinia({ createSpy: vi.fn });
    setActivePinia(pinia);
    const toolStore = useToolStore();
    const userStore = useUserStore();
    toolStore.toolSections = {
        "ontology:edam_operations": {
            operation_2409: {
                model_class: "ToolSection",
                id: "operation_2409",
                name: "Data handling",
                tools: ["__FILTER_FAILED_DATASETS__"],
            },
        },
        "ontology:edam_topics": {
            topic_0091: {
                model_class: "ToolSection",
                id: "topic_0091",
                name: "Data formats",
                tools: ["__FILTER_FAILED_DATASETS__"],
            },
        },
    };
    userStore.currentUser =
        options?.currentUser ??
        ({
            id: "anonymous",
            isAnonymous: true,
        } as any);
    userStore.currentPreferences = {
        favorites: options?.favorites ?? { tools: [], tags: [], edam_operations: [], edam_topics: [] },
    };

    return {
        pinia,
        wrapper: mount(ToolsListCard as object, {
            localVue,
            pinia,
            propsData: {
                id: "__FILTER_FAILED_DATASETS__",
                name: "Filter failed",
                edamOperations: ["operation_2409"],
                edamTopics: ["topic_0091"],
                toolTags: ["collection_ops", "data_cleanup"],
                workflowCompatible: true,
                local: true,
                fetching: false,
            },
        }),
    };
}

describe("ToolsListCard", () => {
    it("renders tool tags and emits an exact tag filter when a tag is clicked", async () => {
        const { wrapper } = mountCard();

        const tags = wrapper.findAll(".curated-tag");
        expect(tags).toHaveLength(2);
        expect(tags.at(0)?.text()).toContain("collection_ops");
        expect(tags.at(1)?.text()).toContain("data_cleanup");

        await tags.at(0)?.find(".g-link").trigger("click");

        expect(wrapper.emitted("apply-filter")).toEqual([["tag", "collection_ops"]]);
    });

    it("adds and removes favorite tags for signed-in users", async () => {
        const { wrapper } = mountCard({
            currentUser: {
                id: "user-id",
                username: "test-user",
                email: "test@example.org",
                isAnonymous: false,
            },
            favorites: { tools: [], tags: ["collection_ops"], edam_operations: ["operation_2409"], edam_topics: [] },
        });
        const userStore = useUserStore();

        const favoriteButtons = wrapper.findAll(".inline-tag-button");
        await favoriteButtons.at(0)?.trigger("click");
        await favoriteButtons.at(1)?.trigger("click");

        expect(userStore.removeFavoriteTag).toHaveBeenCalledWith("collection_ops");
        expect(userStore.addFavoriteTag).toHaveBeenCalledWith("data_cleanup");
    });

    it("adds and removes favorite EDAM operations for signed-in users", async () => {
        const { wrapper } = mountCard({
            currentUser: {
                id: "user-id",
                username: "test-user",
                email: "test@example.org",
                isAnonymous: false,
            },
            favorites: { tools: [], tags: [], edam_operations: ["operation_2409"], edam_topics: [] },
        });
        const userStore = useUserStore();

        const ontologyButton = wrapper.find(".inline-ontology-button");
        expect(wrapper.text()).toContain("Data handling");
        await ontologyButton.trigger("click");

        expect(userStore.removeFavoriteEdamOperation).toHaveBeenCalledWith("operation_2409");
    });

    it("adds and removes favorite EDAM topics for signed-in users", async () => {
        const { wrapper } = mountCard({
            currentUser: {
                id: "user-id",
                username: "test-user",
                email: "test@example.org",
                isAnonymous: false,
            },
            favorites: { tools: [], tags: [], edam_operations: [], edam_topics: ["topic_0091"] },
        });
        const userStore = useUserStore();

        const topicButton = wrapper.find('[data-description="favorite-edam-topic-button"]');
        expect(wrapper.text()).toContain("Data formats");
        await topicButton.trigger("click");

        expect(userStore.removeFavoriteEdamTopic).toHaveBeenCalledWith("topic_0091");
    });

    it("shows a login affordance for anonymous users", async () => {
        const { wrapper } = mountCard();

        const favoriteButton = wrapper.find(".inline-tag-button");
        expect(favoriteButton.attributes("aria-disabled")).toBe("true");
        expect(favoriteButton.attributes("title")).toBe("Login or Register to Favorite Tags");

        const ontologyButton = wrapper.find(".inline-ontology-button");
        expect(ontologyButton.attributes("aria-disabled")).toBe("true");
        expect(ontologyButton.attributes("title")).toBe("Login or Register to Favorite EDAM Operations");

        const topicButton = wrapper.find('[data-description="favorite-edam-topic-button"]');
        expect(topicButton.attributes("aria-disabled")).toBe("true");
        expect(topicButton.attributes("title")).toBe("Login or Register to Favorite EDAM Topics");
    });

    it("renders multi-word curated tags for tools with spaced ids", async () => {
        const pinia = createTestingPinia({ createSpy: vi.fn });
        setActivePinia(pinia);
        const userStore = useUserStore();
        userStore.currentUser = {
            id: "anonymous",
            isAnonymous: true,
        } as any;
        userStore.currentPreferences = {
            favorites: { tools: [], tags: [], edam_operations: [], edam_topics: [] },
        };

        const wrapper = mount(ToolsListCard as object, {
            localVue,
            pinia,
            propsData: {
                id: "Remove beginning1",
                name: "Remove beginning",
                edamOperations: [],
                edamTopics: [],
                toolTags: ["Text Manipulation"],
                workflowCompatible: true,
                local: true,
                fetching: false,
            },
        });

        const tags = wrapper.findAll(".curated-tag");
        expect(tags).toHaveLength(1);
        expect(tags.at(0)?.text()).toContain("Text Manipulation");
    });
});
