import { createTestingPinia } from "@pinia/testing";
import { getFakeAnonymousUser, getFakeRegisteredUser } from "@tests/test-data";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import { setActivePinia } from "pinia";
import { afterEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";

import type { AnyUser } from "@/api";
import { sanitizeHtml } from "@/directives/sanitizeHtml";
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
const mountPoints: HTMLElement[] = [];

afterEach(() => {
    // Unmounting removes the card's relocated popovers; remove only our own host elements.
    mountPoints.splice(0).forEach((mountPoint) => mountPoint.remove());
    vi.restoreAllMocks();
});
// Vitest runs afterEach hooks in reverse registration order.
enableAutoUnmount(afterEach);

type CardProps = InstanceType<typeof ToolsListCard>["$props"];
type Favorites = NonNullable<ReturnType<typeof useUserStore>["currentPreferences"]>["favorites"];

function mountCard(options?: {
    attachTo?: HTMLElement;
    currentUser?: AnyUser;
    favorites?: Favorites;
    props?: Partial<CardProps>;
}) {
    const pinia = createTestingPinia({ createSpy: vi.fn });
    setActivePinia(pinia);
    const toolStore = useToolStore();
    const userStore = useUserStore();
    // userStore is a setup-syntax store, so @pinia/testing's automatic action
    // spying (which relies on the options-API `actions` map) doesn't apply --
    // spy on the actions this file asserts against explicitly.
    vi.spyOn(userStore, "removeFavoriteTag");
    vi.spyOn(userStore, "addFavoriteTag");
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
    userStore.currentUser = options?.currentUser ?? getFakeAnonymousUser();
    userStore.currentPreferences = {
        favorites: options?.favorites ?? { tools: [], tags: [], edam_operations: [], edam_topics: [] },
    };

    return {
        userStore,
        wrapper: mount(ToolsListCard, {
            attachTo: options?.attachTo,
            global: withPlugins(localVue, pinia),
            props: {
                id: "__FILTER_FAILED_DATASETS__",
                name: "Filter failed",
                edamOperations: ["operation_2409"],
                edamTopics: ["topic_0091"],
                toolTags: ["collection_ops", "data_cleanup"],
                workflowCompatible: true,
                local: true,
                fetching: false,
                ...options?.props,
            },
        }),
    };
}

describe("ToolsListCard", () => {
    it("renders Markdown tool help", async () => {
        const { wrapper } = mountCard({
            props: {
                help: "**Important** tool help",
                helpFormat: "markdown",
            },
        });

        await wrapper.get('[data-description="tools list toggle tool help"]').trigger("click");

        const help = wrapper.get('[data-description="tools list tool help"]');
        expect(help.get("strong").text()).toBe("Important");
        expect(help.text()).not.toContain("**Important**");
    });

    it("names the icon-only button that opens the version popover", () => {
        const { wrapper } = mountCard({ props: { version: "1.0.0" } });

        expect(wrapper.get("#tools-list-__FILTER_FAILED_DATASETS__").attributes("aria-label")).toBe("Tool info");
    });

    it("keeps the version popover open when its keyboard-focused button is activated", async () => {
        const mountPoint = document.createElement("div");
        document.body.appendChild(mountPoint);
        mountPoints.push(mountPoint);
        const { wrapper } = mountCard({ attachTo: mountPoint, props: { version: "1.0.0" } });
        await nextTick();
        await nextTick();
        const button = wrapper.get("#tools-list-__FILTER_FAILED_DATASETS__");
        // The card relocates its popover to the body; its trigger identifies the owned popover.
        const popoverId = button.attributes("aria-describedby");
        expect(popoverId).toBeTruthy();
        const popover = document.getElementById(popoverId!);
        expect(popover).not.toBeNull();
        const isShown = () => popover!.style.display !== "none";

        (button.element as HTMLElement).focus();
        await nextTick();
        expect(isShown()).toBe(true);

        await button.trigger("click");
        expect(isShown()).toBe(true);
    });

    it("renders tool tags and emits an exact tag filter when a tag is clicked", async () => {
        const { wrapper } = mountCard();

        const tags = wrapper.findAll(".curated-tag");
        expect(tags).toHaveLength(2);
        expect(tags[0]!.text()).toContain("collection_ops");
        expect(tags[1]!.text()).toContain("data_cleanup");

        await tags[0]!.get(".g-link").trigger("click");

        expect(wrapper.emitted("apply-filter")).toEqual([["tag", "collection_ops"]]);
    });

    const SIGNED_IN_USER = getFakeRegisteredUser({
        id: "user-id",
        username: "test-user",
        email: "test@example.org",
    });

    it("adds and removes favorite tags for signed-in users", async () => {
        const { wrapper, userStore } = mountCard({
            currentUser: SIGNED_IN_USER,
            favorites: { tools: [], tags: ["collection_ops"], edam_operations: ["operation_2409"], edam_topics: [] },
        });
        const favoriteButtons = wrapper.findAll(".inline-tag-button");
        expect(favoriteButtons).toHaveLength(2);
        await favoriteButtons[0]!.trigger("click");
        await favoriteButtons[1]!.trigger("click");

        expect(userStore.removeFavoriteTag).toHaveBeenCalledWith("collection_ops");
        expect(userStore.addFavoriteTag).toHaveBeenCalledWith("data_cleanup");
    });

    // EDAM operations and topics share their entire dispatch path (`useToolsListCardActions`),
    // so verify one button per dispatch target with a parameterized test rather
    // than repeating the setup.
    it.each([
        {
            label: "EDAM operations",
            favorites: { tools: [], tags: [], edam_operations: ["operation_2409"], edam_topics: [] },
            selector: ".inline-ontology-button",
            visibleSectionLabel: "Data handling",
            action: "removeFavoriteEdamOperation" as const,
            actionArg: "operation_2409",
        },
        {
            label: "EDAM topics",
            favorites: { tools: [], tags: [], edam_operations: [], edam_topics: ["topic_0091"] },
            selector: '[data-description="favorite-edam-topic-button"]',
            visibleSectionLabel: "Data formats",
            action: "removeFavoriteEdamTopic" as const,
            actionArg: "topic_0091",
        },
    ])(
        "removes a favorite $label entry for signed-in users",
        async ({ favorites, selector, visibleSectionLabel, action, actionArg }) => {
            const { wrapper, userStore } = mountCard({ currentUser: SIGNED_IN_USER, favorites });
            expect(wrapper.text()).toContain(visibleSectionLabel);
            await wrapper.get(selector).trigger("click");
            expect(userStore[action]).toHaveBeenCalledWith(actionArg);
        },
    );

    it("shows a login affordance for anonymous users", () => {
        const { wrapper } = mountCard();

        const favoriteButton = wrapper.get(".inline-tag-button");
        expect(favoriteButton.attributes("aria-disabled")).toBe("true");
        expect(favoriteButton.attributes("title")).toBe("Login or Register to Favorite Tags");

        const ontologyButton = wrapper.get(".inline-ontology-button");
        expect(ontologyButton.attributes("aria-disabled")).toBe("true");
        expect(ontologyButton.attributes("title")).toBe("Login or Register to Favorite EDAM Operations");

        const topicButton = wrapper.get('[data-description="favorite-edam-topic-button"]');
        expect(topicButton.attributes("aria-disabled")).toBe("true");
        expect(topicButton.attributes("title")).toBe("Login or Register to Favorite EDAM Topics");
    });

    it("renders multi-word curated tags for tools with spaced ids", () => {
        const { wrapper } = mountCard({
            props: {
                id: "Remove beginning1",
                name: "Remove beginning",
                edamOperations: [],
                edamTopics: [],
                toolTags: ["Text Manipulation"],
            },
        });

        const tags = wrapper.findAll(".curated-tag");
        expect(tags).toHaveLength(1);
        expect(tags[0]!.text()).toContain("Text Manipulation");
    });

    it("renders the help summary through v-sanitize-html", () => {
        vi.mocked(sanitizeHtml).mockClear();
        const summary = "Filters <em>failed</em> datasets";
        const { wrapper } = mountCard({ props: { summary } });
        expect(sanitizeHtml).toHaveBeenCalledWith(summary, "default");
        expect(wrapper.get("em").text()).toBe("failed");
    });
});
