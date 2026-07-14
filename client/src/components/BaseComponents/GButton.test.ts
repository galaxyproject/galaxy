import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import VueRouter from "vue-router";

import GButton from "./GButton.vue";

const localVue = getLocalVue(true);
localVue.use(VueRouter);

function mountGButton(props: object) {
    return mount(GButton as object, { propsData: props, localVue });
}

describe("GButton.vue", () => {
    it("uses the regular title when enabled", () => {
        const wrapper = mountGButton({ title: "Click me" });
        const button = wrapper.get("button");

        expect(button.attributes("title")).toBe("Click me");
        expect(button.attributes("data-title")).toBe("Click me");
    });

    it("uses the disabled title when disabled", () => {
        const wrapper = mountGButton({
            disabled: true,
            title: "Click me",
            disabledTitle: "Cannot click right now",
        });
        const button = wrapper.get("button");

        expect(button.attributes("title")).toBe("Cannot click right now");
        expect(button.attributes("data-title")).toBe("Cannot click right now");
    });

    it("falls back to the regular title when disabled without a disabled title", () => {
        const wrapper = mountGButton({ disabled: true, title: "Click me" });
        const button = wrapper.get("button");

        expect(button.attributes("title")).toBe("Click me");
    });

    // A disabled button must stay hoverable so the (disabled) title can surface its
    // tooltip. We mark it disabled via aria-disabled and a JS click guard rather than
    // the native `disabled` attribute (which would suppress hover events).
    it("remains hoverable when disabled", () => {
        const wrapper = mountGButton({ disabled: true, disabledTitle: "Nope" });
        const button = wrapper.get("button");

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

describe("GButton.vue disabled navigation", () => {
    // A disabled button with a `to` prop must not navigate. The component-level @click
    // guard does not run for a RouterLink (Vue 2 treats @click on a component as a
    // component listener, not a native one), and an empty `to` is not a reliable no-op
    // in vue-router -- so a disabled GButton renders as a plain button instead.
    it("renders an enabled router-link button as an anchor", () => {
        const router = new VueRouter({ mode: "abstract", routes: [{ path: "/" }, { path: "/pages/create" }] });
        const wrapper = mount(GButton as object, {
            propsData: { to: "/pages/create" },
            localVue,
            router,
        });

        expect(wrapper.element.tagName).toBe("A");
    });

    it("renders a disabled router-link button as a plain button", () => {
        const router = new VueRouter({ mode: "abstract", routes: [{ path: "/" }, { path: "/pages/create" }] });
        const wrapper = mount(GButton as object, {
            propsData: { to: "/pages/create", disabled: true, disabledTitle: "Nope" },
            localVue,
            router,
        });

        expect(wrapper.element.tagName).toBe("BUTTON");
    });

    it("does not navigate when a disabled router-link button is clicked", async () => {
        const router = new VueRouter({ mode: "abstract", routes: [{ path: "/start" }, { path: "/pages/create" }] });
        await router.push("/start?keep=me");
        const routeBeforeClick = router.currentRoute.fullPath;
        const wrapper = mount(GButton as object, {
            propsData: { to: "/pages/create", disabled: true },
            localVue,
            router,
        });

        await wrapper.trigger("click");

        expect(router.currentRoute.fullPath).toBe(routeBeforeClick);
    });
});
