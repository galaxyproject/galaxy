import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import type { Router } from "vue-router";

import { createMemoryRouter } from "./test-utils";

import GButton from "./GButton.vue";

const localVue = getLocalVue(true);

function mountGButton(props: object, router?: Router) {
    return mount(GButton, { props, global: router ? withPlugins(localVue, router) : localVue });
}

describe("GButton.vue titles", () => {
    it("uses the regular title when enabled", () => {
        const button = mountGButton({ title: "Click me" }).get("button");

        expect(button.attributes("title")).toBe("Click me");
        expect(button.attributes("data-title")).toBe("Click me");
    });

    it("uses the disabled title when disabled", () => {
        const button = mountGButton({
            disabled: true,
            title: "Click me",
            disabledTitle: "Cannot click right now",
        }).get("button");

        expect(button.attributes("title")).toBe("Cannot click right now");
        expect(button.attributes("data-title")).toBe("Cannot click right now");
    });

    it("falls back to the regular title when disabled without a disabled title", () => {
        const button = mountGButton({ disabled: true, title: "Click me" }).get("button");

        expect(button.attributes("title")).toBe("Click me");
        expect(button.attributes("data-title")).toBe("Click me");
    });

    // A styled tooltip replaces the native title. RouterLink runs in Vue 3 mode, where a
    // `false` attribute renders as the string "false" instead of being dropped.
    it("leaves the native title off a router link with a tooltip", () => {
        const wrapper = mountGButton(
            { to: "/pages/create", title: "Create a page", tooltip: true },
            createMemoryRouter(),
        );

        expect(wrapper.get("a").attributes("title")).toBeUndefined();
    });
});

describe("GButton.vue disabled", () => {
    // A disabled button must stay hoverable so the (disabled) title can surface its
    // tooltip. We mark it disabled via aria-disabled and a JS click guard rather than
    // the native `disabled` attribute (which would suppress hover events).
    it("remains hoverable when disabled", () => {
        const button = mountGButton({ disabled: true, disabledTitle: "Nope" }).get("button");

        expect(button.attributes("aria-disabled")).toBe("true");
        expect(button.attributes("disabled")).toBeUndefined();
    });

    it("does not emit click when disabled", async () => {
        const wrapper = mountGButton({ disabled: true, disabledTitle: "Nope" });

        await wrapper.get("button").trigger("click");

        expect(wrapper.emitted("click")).toBeUndefined();
    });

    it("emits click when enabled", async () => {
        const wrapper = mountGButton({ title: "Click me" });

        await wrapper.get("button").trigger("click");

        expect(wrapper.emitted("click")).toHaveLength(1);
    });
});

describe("GButton.vue loading", () => {
    it("shows a spinner and marks itself busy while loading", () => {
        const button = mountGButton({ loading: true }).get("button");

        expect(button.attributes("aria-busy")).toBe("true");
        expect(button.find('[data-icon="spinner"]').exists()).toBe(true);
    });

    it("ignores clicks while loading", async () => {
        const wrapper = mountGButton({ loading: true });

        await wrapper.get("button").trigger("click");

        expect(wrapper.emitted("click")).toBeUndefined();
    });

    it("renders a loading router-link button as a plain button so it cannot navigate", () => {
        const wrapper = mountGButton({ to: "/pages/create", loading: true }, createMemoryRouter());

        expect(wrapper.element.tagName).toBe("BUTTON");
    });

    it("drops the spinner and busy state and takes clicks again once loading ends", async () => {
        const wrapper = mountGButton({ loading: true });
        await wrapper.setProps({ loading: false });
        const button = wrapper.get("button");

        expect(button.attributes("aria-busy")).toBeUndefined();
        expect(button.find('[data-icon="spinner"]').exists()).toBe(false);

        await button.trigger("click");
        expect(wrapper.emitted("click")).toHaveLength(1);
    });

    // Loading is a wait, not an unavailable action, so the button keeps its colour.
    it("does not look or announce itself as disabled while loading", () => {
        const button = mountGButton({ loading: true }).get("button");

        expect(button.classes()).not.toContain("g-disabled");
        expect(button.attributes("aria-disabled")).toBeUndefined();
    });
});

describe("GButton.vue click propagation", () => {
    // A native disabled button dispatches no click at all, so nothing reaches clickable
    // ancestors. GButton renders `aria-disabled` instead of the native attribute, so the
    // guard in `onClick` has to stop the event itself.
    function mountInClickableParent(buttonProps: object) {
        const onParentClick = vi.fn();

        const wrapper = mount(
            {
                components: { GButton },
                props: ["buttonProps"],
                template: `<div @click="onParentClick"><GButton v-bind="buttonProps">Click me</GButton></div>`,
                methods: { onParentClick },
            },
            { props: { buttonProps }, global: localVue },
        );

        return { onParentClick, button: wrapper.getComponent(GButton) };
    }

    it("does not bubble a click to clickable ancestors when disabled", async () => {
        const { onParentClick, button } = mountInClickableParent({ disabled: true, disabledTitle: "Nope" });

        await button.get("button").trigger("click");

        expect(button.emitted("click")).toBeUndefined();
        expect(onParentClick).not.toHaveBeenCalled();
    });

    it("bubbles a click to clickable ancestors when enabled", async () => {
        const { onParentClick, button } = mountInClickableParent({});

        await button.get("button").trigger("click");

        expect(button.emitted("click")).toHaveLength(1);
        expect(onParentClick).toHaveBeenCalledTimes(1);
    });
});

describe("GButton.vue click per root element", () => {
    // A router link gets the click listener on its rendered anchor by fallthrough,
    // alongside RouterLink's own navigation handler; the plain roots bind the same
    // single listener directly.
    it.each([
        { root: "router-link", element: "a", props: { to: "/pages/create" }, withRouter: true },
        { root: "plain button", element: "button", props: {}, withRouter: false },
        { root: "plain anchor", element: "a", props: { href: "https://example.org" }, withRouter: false },
    ])("emits click exactly once from a $root root", async ({ element, props, withRouter }) => {
        const wrapper = mountGButton(props, withRouter ? createMemoryRouter() : undefined);

        await wrapper.get(element).trigger("click");

        expect(wrapper.emitted("click")).toHaveLength(1);
    });
});

describe("GButton.vue disabled navigation", () => {
    // A disabled button with a `to` prop must not navigate: an empty `to` is not a
    // reliable no-op in vue-router, so a disabled GButton renders as a plain button
    // instead and has no navigation behaviour to suppress.
    it("renders an enabled router-link button as an anchor", () => {
        const wrapper = mountGButton({ to: "/pages/create" }, createMemoryRouter());

        expect(wrapper.element.tagName).toBe("A");
    });

    it("renders a disabled router-link button as a plain button", () => {
        const wrapper = mountGButton(
            { to: "/pages/create", disabled: true, disabledTitle: "Nope" },
            createMemoryRouter(),
        );

        expect(wrapper.element.tagName).toBe("BUTTON");
    });

    it("does not navigate when a disabled router-link button is clicked", async () => {
        const router = createMemoryRouter({ paths: ["/start", "/pages/create"] });
        await router.push("/start?keep=me");
        const wrapper = mountGButton({ to: "/pages/create", disabled: true }, router);

        await wrapper.trigger("click");

        expect(router.currentRoute.value.fullPath).toBe("/start?keep=me");
    });
});

describe("GButton.vue link targets", () => {
    // Galaxy can be served under a URL prefix, so a router link's href has to come from
    // the router, which knows the base -- open-in-new-tab and copy-link use it as is.
    it("renders a router link's href with the router base", () => {
        const wrapper = mountGButton({ to: "/pages/create" }, createMemoryRouter({ base: "/galaxypf/" }));

        expect(wrapper.get("a").attributes("href")).toBe("/galaxypf/pages/create");
    });

    it("renders a plain anchor's href as given", () => {
        const wrapper = mountGButton({ href: "https://example.org/data.txt" });

        expect(wrapper.get("a").attributes("href")).toBe("https://example.org/data.txt");
    });

    it("renders no href when disabled", () => {
        const wrapper = mountGButton({ href: "https://example.org/data.txt", disabled: true });

        expect(wrapper.get("button").attributes("href")).toBeUndefined();
    });
});
