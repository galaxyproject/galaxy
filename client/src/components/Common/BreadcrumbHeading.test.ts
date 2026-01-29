import { getLocalVue } from "@tests/jest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { nextTick } from "vue";
import VueRouter from "vue-router";

import type { BreadcrumbItem } from "@/components/Common/index";

import BreadcrumbHeading from "./BreadcrumbHeading.vue";

const ACTIVE_CLASS = ".breadcrumb-heading-header-active";
const INACTIVE_CLASS = ".breadcrumb-heading-header-inactive";
const BETA_CLASS = ".breadcrumb-heading-header-beta";

const localVue = getLocalVue();

localVue.use(VueRouter);

async function mountComponent(items: BreadcrumbItem[] = [], routePath: string = "/home", slotContent: string = "") {
    const router = new VueRouter();

    router.push(routePath);

    const wrapper = mount(BreadcrumbHeading as object, {
        localVue,
        router,
        propsData: {
            items,
        },
        slots: {
            default: slotContent,
        },
    });

    await flushPromises();

    return wrapper;
}

describe("BreadcrumbHeading.vue", () => {
    it("renders a single breadcrumb item without link when no 'to' property", async () => {
        const items = [{ title: "Home" }];

        const wrapper = await mountComponent(items);

        expect(wrapper.find(INACTIVE_CLASS).text()).toBe(items[0]?.title);
        expect(wrapper.findAll("a")).toHaveLength(0);
    });

    it("renders a single breadcrumb item as inactive when current route matches and without separator", async () => {
        const items = [{ title: "Home", to: "/home" }];

        const wrapper = await mountComponent(items);

        expect(wrapper.find(INACTIVE_CLASS).text()).toBe(items[0]?.title);
        expect(wrapper.findAll("a")).toHaveLength(0);

        const wrapperContent = wrapper.text();

        expect(wrapperContent).not.toContain(" / ");
    });

    it("renders a single breadcrumb item as link when not on current route", async () => {
        const items = [{ title: "Test Title", to: "/test" }];

        const wrapper = await mountComponent(items, "/different-route");

        await flushPromises();
        await nextTick();

        const link = wrapper.find("a");

        expect(link.exists()).toBe(true);
        expect(link.text()).toBe(items[0]?.title);
        expect(link.classes()).toContain(ACTIVE_CLASS.replace(".", ""));
    });

    it("renders multiple breadcrumb items with separators", async () => {
        const items = [
            { title: "Home", to: "/" },
            { title: "Test Title", to: "/test" },
            { title: "Current Page", to: "/current" },
        ];

        const wrapper = await mountComponent(items, "/current");

        const links = wrapper.findAll("a");
        expect(links).toHaveLength(2);

        expect(wrapper.find(INACTIVE_CLASS).text()).toBe(items[2]?.title);

        const wrapperContent = wrapper.text();
        const separatorCount = (wrapperContent.match(/ \/ /g) || []).length;

        expect(separatorCount).toBe(2);
    });

    it("renders superText when provided", async () => {
        const items = [{ title: "Beta Feature", superText: "BETA" }];
        const wrapper = await mountComponent(items);

        const superText = wrapper.find(BETA_CLASS);

        expect(superText.exists()).toBe(true);
        expect(superText.text()).toBe("BETA");
    });

    it("renders slot content", async () => {
        const items = [{ title: "Home" }];
        const slotContent = '<div class="test-slot">Additional content</div>';

        const wrapper = await mountComponent(items, "/home", slotContent);

        expect(wrapper.html()).toContain("Additional content");
    });
});
