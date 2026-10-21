import { composeStories } from "@storybook/vue3-vite";
import { nth } from "@tests/vitest/helpers";
import { useStoryMount } from "@tests/vitest/stories";
import { flushPromises } from "@vue/test-utils";
import { beforeEach, describe, expect, it, onTestFinished, vi } from "vitest";
import { h, nextTick, ref } from "vue";

import { defaultActivities } from "@/stores/activitySetup";
import { useActivityStore } from "@/stores/activityStore";
import { useUnprivilegedToolStore } from "@/stores/unprivilegedToolStore";
import { ensureDefined } from "@/utils/assertions";

import * as ActivitySettingsStories from "./ActivitySettings.stories";

import ActivitySettings from "./ActivitySettings.vue";

const mockConfig = ref({});

vi.mock("@/composables/config", () => ({
    useConfig: vi.fn(() => ({
        config: mockConfig,
        isConfigLoaded: true,
    })),
}));

const queryControls = new WeakMap();
let nextQuery;
const stories = composeStories(ActivitySettingsStories, {
    render: (args) => ({
        setup() {
            const query = nextQuery;
            return () => h(ActivitySettings, { ...args, query: query.value });
        },
    }),
});
const mountStory = useStoryMount();
const activityItemSelector = ".activity-settings-item";

async function mountActivitySettings(activityBarId, story = stories.BuiltInActivities) {
    nextQuery = ref("");
    const query = nextQuery;
    const root = mountStory(story, {
        props: { query: "", activityBarId },
        // Preserve the original synthetic icon-attribute contract only in units.
        // Standalone stories use actual built-in icons and dataset bookmarks.
        global: { stubs: { FontAwesomeIcon: { template: "<div></div>" } } },
    });
    await vi.waitFor(() => root.getComponent(ActivitySettings));
    const wrapper = root.getComponent(ActivitySettings);
    queryControls.set(wrapper, query);
    return wrapper;
}

function testActivity(id, newOptions = {}) {
    const defaultOptions = {
        id: `activity-test-${id}`,
        description: "activity-test-description",
        icon: "activity-test-icon",
        mutable: true,
        optional: true,
        title: "activity-test-title",
        to: null,
        tooltip: "activity-test-tooltip",
        visible: true,
    };
    return { ...defaultOptions, ...newOptions };
}

function activityTitle(id) {
    return ensureDefined(defaultActivities.find((activity) => activity.id === id)).title;
}

async function testSearch(wrapper, query, result) {
    // Update the mounted child through its parent without remounting story decorators.
    ensureDefined(queryControls.get(wrapper)).value = query;
    await nextTick();
    const filtered = wrapper.findAll(activityItemSelector);
    expect(filtered.length).toBe(result);
}

describe("ActivitySettings", () => {
    let activityStore;
    let wrapper;

    beforeEach(async () => {
        const originalConfig = mockConfig.value;
        onTestFinished(() => {
            mockConfig.value = originalConfig;
        });
        mockConfig.value = { interactivetools_enable: true, llm_api_configured: true };
        wrapper = await mountActivitySettings("test-activity-bar");
        activityStore = useActivityStore("test-activity-bar");
        await activityStore.sync();
    });

    it("availability of built-in activities", async () => {
        const items = wrapper.findAll(activityItemSelector);
        const nOptional = defaultActivities.filter((x) => x.optional).length - 1; // 403 for unprivileged_tools excludes user-defined-tools activity
        expect(items.length).toBe(nOptional);
    });

    it("visible and optional activity", async () => {
        activityStore.setAll([testActivity("1")]);
        await nextTick();
        const items = wrapper.findAll(activityItemSelector);
        expect(items.length).toBe(1);
        const checkbox = nth(items, 0).find("[data-title='Hide in Activity Bar']");
        expect(checkbox.exists()).toBeTruthy();
        const icon = wrapper.find("[icon='activity-test-icon']");
        expect(icon.exists()).toBeTruthy();
        expect(nth(activityStore.getAll(), 0).visible).toBeTruthy();
        await nth(items, 0).get("[data-title='Hide in Activity Bar']").trigger("click");
        await wrapper.vm.$nextTick();
        expect(nth(activityStore.getAll(), 0).visible).toBeFalsy();
    });

    it("non-visible but optional activity", async () => {
        activityStore.setAll([
            testActivity("1", {
                optional: true,
                visible: false,
            }),
        ]);
        await wrapper.vm.$nextTick();
        const items = wrapper.findAll(activityItemSelector);
        expect(items.length).toBe(1);
        const checkbox = nth(items, 0).find("[data-title='Show in Activity Bar']");
        expect(checkbox.exists()).toBeTruthy();
        expect(nth(activityStore.getAll(), 0).visible).toBeFalsy();
        await nth(items, 0).get("[data-title='Show in Activity Bar']").trigger("click");
        await wrapper.vm.$nextTick();
        const visibleCheckbox = nth(items, 0).find("[data-title='Hide in Activity Bar']");
        expect(visibleCheckbox.exists()).toBeTruthy();
        expect(nth(activityStore.getAll(), 0).visible).toBeTruthy();
    });

    it("removable", async () => {
        activityStore.setAll([testActivity("1")]);
        await wrapper.vm.$nextTick();
        const items = wrapper.findAll(activityItemSelector);
        expect(items.length).toBe(1);
        const trash = nth(items, 0).find("[data-description='delete activity']");
        expect(trash.exists()).toBeTruthy();
        expect(activityStore.getAll().length).toBe(1);
        await nth(items, 0).get("[data-description='delete activity']").trigger("click");
        await wrapper.vm.$nextTick();
        expect(activityStore.getAll().length).toBe(0);
    });

    it("non-removable", async () => {
        activityStore.setAll([
            testActivity("1", {
                mutable: false,
            }),
        ]);
        await wrapper.vm.$nextTick();
        const items = wrapper.findAll(activityItemSelector);
        expect(items.length).toBe(1);
        const trash = nth(items, 0).find("[data-icon='trash']");
        expect(trash.exists()).toBeFalsy();
    });

    it("filter activities by title and description", async () => {
        activityStore.setAll([
            testActivity("1"),
            testActivity("2", { title: "something else" }),
            testActivity("3", { title: "SOMETHING different" }),
            testActivity("4", { description: "SOMEthing odd" }),
        ]);
        await wrapper.vm.$nextTick();
        const items = wrapper.findAll(activityItemSelector);
        expect(items.length).toBe(4);
        await testSearch(wrapper, "else", 1);
        await testSearch(wrapper, "someTHING", 3);
        await testSearch(wrapper, "odd", 1);
    });

    describe("built-in activity availability", () => {
        function renderedTitles(settings) {
            return settings.findAll(`${activityItemSelector} .font-weight-bold`).map((title) => title.text());
        }

        async function mountSettings(config, { canUseUnprivilegedTools }) {
            mockConfig.value = config;
            const settings = await mountActivitySettings(
                "test-activity-bar-gates",
                canUseUnprivilegedTools ? stories.CustomToolsPermitted : stories.BuiltInActivities,
            );
            useUnprivilegedToolStore().canUseUnprivilegedTools = canUseUnprivilegedTools;
            const store = useActivityStore("test-activity-bar-gates");
            await store.sync();
            await flushPromises();
            return { settings, store };
        }

        it("lists only optional activities when user-defined tools are permitted", async () => {
            const { settings } = await mountSettings(
                { interactivetools_enable: true, llm_api_configured: true },
                { canUseUnprivilegedTools: true },
            );
            const titles = renderedTitles(settings);
            expect(titles).toContain(activityTitle("user-defined-tools"));
            expect(titles).not.toContain(activityTitle("upload"));
            expect(titles).not.toContain(activityTitle("tools"));
        });

        it("updates config-gated activities when configuration arrives without changing saved visibility", async () => {
            const { settings, store } = await mountSettings(null, { canUseUnprivilegedTools: false });
            const interactiveTools = ensureDefined(
                store.getAll().find((activity) => activity.id === "interactivetools"),
            );
            interactiveTools.visible = false;
            await nextTick();
            expect(renderedTitles(settings)).not.toContain(activityTitle("interactivetools"));
            expect(renderedTitles(settings)).not.toContain(activityTitle("galaxyai"));

            mockConfig.value = { interactivetools_enable: true, llm_api_configured: false };
            await nextTick();
            expect(renderedTitles(settings)).toContain(activityTitle("interactivetools"));
            expect(renderedTitles(settings)).not.toContain(activityTitle("galaxyai"));
            expect(interactiveTools.visible).toBe(false);

            mockConfig.value = { interactivetools_enable: false, llm_api_configured: true };
            await nextTick();
            expect(renderedTitles(settings)).not.toContain(activityTitle("interactivetools"));
            expect(renderedTitles(settings)).toContain(activityTitle("galaxyai"));
            expect(interactiveTools.visible).toBe(false);
        });

        it("updates Custom Tools when permission changes while keeping always-on activities out", async () => {
            const { settings } = await mountSettings(
                { interactivetools_enable: true, llm_api_configured: true },
                { canUseUnprivilegedTools: false },
            );
            const permissions = useUnprivilegedToolStore();
            expect(renderedTitles(settings)).not.toContain(activityTitle("user-defined-tools"));

            permissions.canUseUnprivilegedTools = true;
            await nextTick();
            expect(renderedTitles(settings)).toContain(activityTitle("user-defined-tools"));
            expect(renderedTitles(settings)).not.toContain(activityTitle("upload"));
            expect(renderedTitles(settings)).not.toContain(activityTitle("tools"));

            permissions.canUseUnprivilegedTools = false;
            await nextTick();
            expect(renderedTitles(settings)).not.toContain(activityTitle("user-defined-tools"));
            expect(renderedTitles(settings)).toContain(activityTitle("histories"));
        });

        it("hides interactive tools and GalaxyAI where the instance does not offer them", async () => {
            const { settings } = await mountSettings({}, { canUseUnprivilegedTools: true });
            const titles = renderedTitles(settings);
            expect(titles).not.toContain(activityTitle("interactivetools"));
            expect(titles).not.toContain(activityTitle("galaxyai"));
            expect(titles).toContain(activityTitle("user-defined-tools"));
        });
    });
});
