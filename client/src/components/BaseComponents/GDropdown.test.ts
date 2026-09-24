import { getLocalVue } from "@tests/vitest/helpers";
import { mount, type Wrapper } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import VueRouter from "vue-router";

import GDropdown from "./GDropdown.vue";
import GDropdownItem from "./GDropdownItem.vue";

const localVue = getLocalVue();
localVue.use(VueRouter);

let wrapper: Wrapper<Vue> | undefined;

function mountDropdown(items: string) {
    wrapper = mount(
        {
            components: { GDropdown, GDropdownItem },
            template: `<GDropdown text="Menu">${items}</GDropdown>`,
        } as object,
        { localVue, router: new VueRouter({ mode: "history" }), attachTo: document.body },
    );
    return wrapper;
}

function isMenuOpen(wrapper: Wrapper<Vue>) {
    return wrapper.get(".dropdown-menu").classes().includes("show");
}

async function openMenu(wrapper: Wrapper<Vue>) {
    await wrapper.get(".dropdown-toggle").trigger("click");
    expect(isMenuOpen(wrapper)).toBe(true);
}

afterEach(() => {
    wrapper?.destroy();
    wrapper = undefined;
});

describe("GDropdown.vue", () => {
    describe("menu button semantics", () => {
        it("links the toggle and the menu", () => {
            const wrapper = mountDropdown(`<GDropdownItem>Action</GDropdownItem>`);
            const toggle = wrapper.get(".dropdown-toggle");
            const menu = wrapper.get(".dropdown-menu");

            expect(toggle.attributes("aria-haspopup")).toBe("menu");
            expect(toggle.attributes("aria-controls")).toBe(menu.attributes("id"));
            expect(menu.attributes("role")).toBe("menu");
            expect(menu.attributes("aria-labelledby")).toBe(toggle.attributes("id"));
            expect(wrapper.get(".dropdown-item").attributes("role")).toBe("menuitem");
        });

        it("reflects the open state in aria-expanded", async () => {
            const wrapper = mountDropdown(`<GDropdownItem>Action</GDropdownItem>`);
            const toggle = wrapper.get(".dropdown-toggle");

            expect(toggle.attributes("aria-expanded")).toBe("false");
            await openMenu(wrapper);
            expect(toggle.attributes("aria-expanded")).toBe("true");
        });
    });

    describe("link items", () => {
        it("render real anchors so they can be opened in a new tab", () => {
            const wrapper = mountDropdown(`
                <GDropdownItem to="/histories/list">Histories</GDropdownItem>
                <GDropdownItem href="https://example.org/">External</GDropdownItem>`);

            const [routerItem, hrefItem] = wrapper.findAll("a.dropdown-item").wrappers;
            expect(routerItem?.attributes("href")).toBe("/histories/list");
            expect(hrefItem?.attributes("href")).toBe("https://example.org/");
        });

        it("close the menu when a router-link item is clicked", async () => {
            const wrapper = mountDropdown(`<GDropdownItem to="/histories/list">Histories</GDropdownItem>`);
            await openMenu(wrapper);

            await wrapper.get("a.dropdown-item").trigger("click");

            expect(isMenuOpen(wrapper)).toBe(false);
        });

        it("close the menu when an href item is clicked", async () => {
            const wrapper = mountDropdown(`<GDropdownItem href="https://example.org/">External</GDropdownItem>`);
            await openMenu(wrapper);

            await wrapper.get("a.dropdown-item").trigger("click");

            expect(isMenuOpen(wrapper)).toBe(false);
        });

        it("close the menu when an action item is clicked", async () => {
            const wrapper = mountDropdown(`<GDropdownItem>Action</GDropdownItem>`);
            await openMenu(wrapper);

            await wrapper.get("a.dropdown-item").trigger("click");

            expect(isMenuOpen(wrapper)).toBe(false);
        });
    });
});
