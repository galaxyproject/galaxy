import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, nth, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils";
import { disposePinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, onTestFinished, vi } from "vitest";
import { nextTick, ref } from "vue";

import { useServerMock } from "@/api/client/__mocks__";
import { defaultActivities } from "@/stores/activitySetup";
import { useActivityStore } from "@/stores/activityStore";
import { useUnprivilegedToolStore } from "@/stores/unprivilegedToolStore";
import { ensureDefined } from "@/utils/assertions";

import ActivitySettings from "./ActivitySettings.vue";

const mockConfig = ref({});

vi.mock("@/composables/config", () => ({
    useConfig: vi.fn(() => ({
        config: mockConfig,
        isConfigLoaded: true,
    })),
}));

const { server, http } = useServerMock();
const activityItemSelector = ".activity-settings-item";
const localVue = getLocalVue();

function createOwnedPinia() {
    const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
    onTestFinished(() => {
        disposePinia(pinia);
        setActivePinia(undefined);
    });
    return pinia;
}

function mountActivitySettings(activityBarId, pinia) {
    return mount(ActivitySettings, {
        global: {
            ...withPlugins(localVue, pinia),
            stubs: { FontAwesomeIcon: { template: "<div></div>" } },
        },
        props: { query: "", activityBarId },
    });
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
    await wrapper.setProps({ query });
    const filtered = wrapper.findAll(activityItemSelector);
    expect(filtered.length).toBe(result);
}

describe("ActivitySettings", () => {
    enableAutoUnmount(afterEach);
    let activityStore;
    let wrapper;

    beforeEach(async () => {
        const originalConfig = mockConfig.value;
        onTestFinished(() => {
            mockConfig.value = originalConfig;
        });
        mockConfig.value = { interactivetools_enable: true, llm_api_configured: true };
        const pinia = createOwnedPinia();
        // Mock the response of the API call
        server.use(
            http.get("/api/unprivileged_tools", ({ response }) => {
                return response("4XX").json({ err_code: 400, err_msg: "permission problem" }, { status: 403 });
            }),
        );
        activityStore = useActivityStore("test-activity-bar");
        wrapper = mountActivitySettings("test-activity-bar", pinia);
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
            const pinia = createOwnedPinia();
            useUnprivilegedToolStore().canUseUnprivilegedTools = canUseUnprivilegedTools;
            const store = useActivityStore("test-activity-bar-gates");
            const settings = mountActivitySettings("test-activity-bar-gates", pinia);
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
