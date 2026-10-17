import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import GDropdownItem from "./GDropdownItem.vue";

const localVue = getLocalVue(true);

/** Click the item and report whether the navigation was cancelled. */
async function clickAndCheckDefaultPrevented(props: object) {
    const wrapper = mount(GDropdownItem as object, {
        propsData: props,
        slots: { default: "Item" },
        localVue,
    });
    const event = new MouseEvent("click", { bubbles: true, cancelable: true });
    wrapper.get("a").element.dispatchEvent(event);
    await wrapper.vm.$nextTick();
    return { wrapper, defaultPrevented: event.defaultPrevented };
}

describe("GDropdownItem.vue", () => {
    it("cancels navigation for action items, which fall back to href='#'", async () => {
        const { wrapper, defaultPrevented } = await clickAndCheckDefaultPrevented({});

        expect(wrapper.get("a").attributes("href")).toBe("#");
        expect(defaultPrevented).toBe(true);
        expect(wrapper.emitted("click")).toHaveLength(1);
    });

    it("cancels navigation when href='#' is passed explicitly", async () => {
        const { wrapper, defaultPrevented } = await clickAndCheckDefaultPrevented({ href: "#" });

        expect(defaultPrevented).toBe(true);
        expect(wrapper.emitted("click")).toHaveLength(1);
    });

    it("lets a real href navigate so target='_blank' can open a new tab", async () => {
        const { wrapper, defaultPrevented } = await clickAndCheckDefaultPrevented({
            href: "https://example.org/workflow.ga",
            target: "_blank",
        });

        expect(wrapper.get("a").attributes("target")).toBe("_blank");
        expect(defaultPrevented).toBe(false);
        expect(wrapper.emitted("click")).toHaveLength(1);
    });

    it("cancels navigation and emits nothing when disabled", async () => {
        const { wrapper, defaultPrevented } = await clickAndCheckDefaultPrevented({
            href: "https://example.org/workflow.ga",
            disabled: true,
        });

        expect(defaultPrevented).toBe(true);
        expect(wrapper.emitted("click")).toBeUndefined();
    });
});

describe("GDropdownItem.vue checked", () => {
    function mountItem(props: object) {
        return mount(GDropdownItem as object, {
            props,
            slots: { default: "Item" },
            global: localVue,
        });
    }

    it.each([
        [{ checked: true }, "true"],
        [{ checked: false }, "false"],
        [{ to: "/histories/list", checked: true }, "true"],
        [{ to: "/histories/list", checked: false }, "false"],
    ])("renders %o as a menu checkbox item", (props, ariaChecked) => {
        const item = mountItem(props).get(".dropdown-item");

        expect(item.attributes("role")).toBe("menuitemcheckbox");
        expect(item.attributes("aria-checked")).toBe(ariaChecked);
    });

    it("stays a plain menu item without the checked prop", () => {
        const item = mountItem({}).get(".dropdown-item");

        expect(item.attributes("role")).toBe("menuitem");
        expect(item.attributes("aria-checked")).toBeUndefined();
    });
});
