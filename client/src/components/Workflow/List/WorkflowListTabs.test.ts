import { createTestingPinia } from "@pinia/testing";
import { getFakeRegisteredUser } from "@tests/test-data";
import { getLocalVue, suppressBootstrapVueWarnings } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import VueRouter from "vue-router";

import type { AnyUser } from "@/api";
import { useUserStore } from "@/stores/userStore";

import WorkflowListTabs from "./WorkflowListTabs.vue";
import LoginRequired from "@/components/Common/LoginRequired.vue";

// `@tests/vitest/mockConfig` hands back a plain boolean for `isConfigLoaded`,
// but this component reads `isConfigLoaded.value` inside a computed, so the
// mock has to expose real refs.
const configState = vi.hoisted(() => ({
    curatedSource: "iwc",
    isConfigLoaded: true,
}));

vi.mock("@/composables/config", async () => {
    const { computed } = await import("vue");
    return {
        useConfig: () => ({
            config: computed(() => ({ curated_workflows_source: configState.curatedSource })),
            isConfigLoaded: computed(() => configState.isConfigLoaded),
        }),
    };
});

const localVue = getLocalVue();
localVue.use(VueRouter);
const router = new VueRouter();

const REGISTERED_USER = getFakeRegisteredUser();
const ANONYMOUS_USER = {
    isAnonymous: true,
    total_disk_usage: 0,
    nice_total_disk_usage: "0 bytes",
} as AnyUser;

type WorkflowListTab = "curated" | "my" | "shared_with_me" | "published";

interface MountOptions {
    anonymous?: boolean;
    curatedSource?: string;
    configLoaded?: boolean;
}

async function mountTabs(active: WorkflowListTab, options: MountOptions = {}) {
    const { anonymous = false, curatedSource = "iwc", configLoaded = true } = options;

    configState.curatedSource = curatedSource;
    configState.isConfigLoaded = configLoaded;

    const pinia = createTestingPinia({ createSpy: vi.fn });
    setActivePinia(pinia);

    const userStore = useUserStore();
    userStore.currentUser = anonymous ? ANONYMOUS_USER : REGISTERED_USER;

    const wrapper = mount(WorkflowListTabs as object, {
        localVue,
        pinia,
        router,
        propsData: { active },
    });

    await flushPromises();

    return wrapper;
}

function tabIds(wrapper: Awaited<ReturnType<typeof mountTabs>>) {
    return wrapper.findAll("li.nav-item").wrappers.map((tab) => tab.attributes("id"));
}

describe("WorkflowListTabs", () => {
    beforeEach(() => {
        suppressBootstrapVueWarnings();
        vi.clearAllMocks();
    });

    it("renders the four tabs with curated first", async () => {
        const wrapper = await mountTabs("curated");

        expect(tabIds(wrapper)).toEqual(["curated", "my", "shared-with-me", "published"]);
    });

    // These ids are Selenium selectors (navigation.yml) and LoginRequired popper
    // targets, so they are part of the component's contract, not incidental markup.
    it("preserves the pre-existing tab element ids and their anchors", async () => {
        const wrapper = await mountTabs("my");

        for (const id of ["my", "shared-with-me", "published"]) {
            const tab = wrapper.find(`#${id}`);
            expect(tab.exists()).toBe(true);
            expect(tab.find("a").exists()).toBe(true);
        }
    });

    it("links each tab to its route", async () => {
        const wrapper = await mountTabs("curated");

        const hrefs = wrapper.findAll("li.nav-item a").wrappers.map((link) => link.attributes("href"));
        expect(hrefs).toEqual([
            "/workflows/list_curated",
            "/workflows/list",
            "/workflows/list_shared_with_me",
            "/workflows/list_published",
        ]);
    });

    it("marks only the active tab as active", async () => {
        const wrapper = await mountTabs("published");

        expect(wrapper.find("#published a").classes()).toContain("active");
        expect(wrapper.find("#curated a").classes()).not.toContain("active");
        expect(wrapper.find("#my a").classes()).not.toContain("active");
    });

    it("disables the user scoped tabs for anonymous users", async () => {
        const wrapper = await mountTabs("curated", { anonymous: true });

        expect(wrapper.find("#my a").attributes("aria-disabled")).toBe("true");
        expect(wrapper.find("#shared-with-me a").attributes("aria-disabled")).toBe("true");
        expect(wrapper.find("#curated a").attributes("aria-disabled")).toBeUndefined();
        expect(wrapper.find("#published a").attributes("aria-disabled")).toBeUndefined();

        expect(wrapper.findAllComponents(LoginRequired)).toHaveLength(2);
    });

    it("enables every tab for registered users", async () => {
        const wrapper = await mountTabs("my");

        for (const id of ["curated", "my", "shared-with-me", "published"]) {
            expect(wrapper.find(`#${id} a`).attributes("aria-disabled")).toBeUndefined();
        }

        expect(wrapper.findAllComponents(LoginRequired)).toHaveLength(0);
    });

    it("shows the curated tab for the local source too", async () => {
        const wrapper = await mountTabs("published", { curatedSource: "local" });

        expect(tabIds(wrapper)).toEqual(["curated", "my", "shared-with-me", "published"]);
    });

    it("hides the curated tab when the curated source is off", async () => {
        const wrapper = await mountTabs("published", { curatedSource: "off" });

        expect(tabIds(wrapper)).toEqual(["my", "shared-with-me", "published"]);
        expect(wrapper.find("#curated").exists()).toBe(false);
    });

    it("hides the curated tab until the configuration has loaded", async () => {
        const wrapper = await mountTabs("published", { configLoaded: false });

        expect(wrapper.find("#curated").exists()).toBe(false);
    });
});
