import { flushPromises, mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import { h, withDirectives } from "vue";
import { createMemoryHistory, createRouter } from "vue-router";

import { vGTooltip } from "../directives/vGTooltip";

import GBadge from "./GBadge.vue";

function makeRouter() {
    return createRouter({
        history: createMemoryHistory(),
        routes: [{ path: "/:any(.*)*", component: { template: "<div />" } }],
    });
}

describe("GBadge", () => {
    it("renders a span with the default slot", () => {
        const wrapper = mount(GBadge, { slots: { default: "3 items" } });

        expect(wrapper.element.tagName).toBe("SPAN");
        expect(wrapper.text()).toBe("3 items");
        expect(wrapper.attributes("tabindex")).toBeUndefined();
        expect(wrapper.attributes("role")).toBeUndefined();
    });

    it("defaults to the secondary variant", () => {
        const wrapper = mount(GBadge);

        expect(wrapper.classes()).toEqual(expect.arrayContaining(["g-badge", "g-secondary"]));
        expect(wrapper.classes()).not.toContain("g-outline");
        expect(wrapper.classes()).not.toContain("g-pill");
    });

    it.each(["primary", "success", "danger", "warning", "info", "light", "dark"] as const)(
        "applies the %s variant class",
        (variant) => {
            const wrapper = mount(GBadge, { props: { variant } });

            expect(wrapper.classes()).toContain(`g-${variant}`);
            expect(wrapper.classes()).not.toContain("g-secondary");
        },
    );

    it("splits an outline variant into the outline and colour classes", () => {
        const wrapper = mount(GBadge, { props: { variant: "outline-primary" } });

        expect(wrapper.classes()).toEqual(expect.arrayContaining(["g-outline", "g-primary"]));
    });

    it("adds the pill class", () => {
        const wrapper = mount(GBadge, { props: { pill: true } });

        expect(wrapper.classes()).toContain("g-pill");
    });

    it("passes title, id, data attributes and classes through to the root", () => {
        const wrapper = mount(GBadge, {
            attrs: { title: "Archived", id: "badge-1", "data-description": "archived badge", class: "mx-1" },
        });

        expect(wrapper.attributes("title")).toBe("Archived");
        expect(wrapper.attributes("id")).toBe("badge-1");
        expect(wrapper.attributes("data-description")).toBe("archived badge");
        expect(wrapper.classes()).toEqual(expect.arrayContaining(["g-badge", "mx-1"]));
    });

    it("gives v-g-tooltip on the component its title", () => {
        const wrapper = mount(() =>
            withDirectives(h(GBadge, { title: "Last edited" }), [[vGTooltip, undefined, "", { hover: true }]]),
        );

        expect(wrapper.get<HTMLSpanElement>(".g-badge").element.dataset.gTooltipTitle).toBe("Last edited");
        wrapper.unmount();
    });

    it("renders an anchor for href and keeps target and rel", () => {
        const wrapper = mount(GBadge, {
            props: { href: "https://orcid.org/0000" },
            attrs: { target: "_blank", rel: "noopener" },
        });

        expect(wrapper.element.tagName).toBe("A");
        expect(wrapper.attributes("href")).toBe("https://orcid.org/0000");
        expect(wrapper.attributes("target")).toBe("_blank");
        expect(wrapper.attributes("rel")).toBe("noopener");
    });

    it("renders a router link for to, with the router's own href", async () => {
        const router = makeRouter();
        router.push("/");
        await router.isReady();
        const wrapper = mount(GBadge, {
            props: { to: "/storage/history/abc" },
            global: { plugins: [router] },
        });

        expect(wrapper.element.tagName).toBe("A");
        expect(wrapper.attributes("href")).toBe("/storage/history/abc");

        await wrapper.trigger("click");
        await flushPromises();
        expect(router.currentRoute.value.fullPath).toBe("/storage/history/abc");
    });

    it("prefers to over href", async () => {
        const router = makeRouter();
        const wrapper = mount(GBadge, {
            props: { to: "/workflows/list", href: "https://example.org" },
            global: { plugins: [router] },
        });

        expect(wrapper.attributes("href")).toBe("/workflows/list");
    });

    it("renders a keyboard-reachable button when button is set", () => {
        const wrapper = mount(GBadge, { props: { button: true }, slots: { default: "Newer version" } });

        expect(wrapper.element.tagName).toBe("BUTTON");
        expect(wrapper.attributes("type")).toBe("button");
        expect(wrapper.text()).toBe("Newer version");
    });

    it("calls a click handler once per click on a button badge", async () => {
        const onClick = vi.fn();
        const wrapper = mount(GBadge, { props: { button: true }, attrs: { onClick } });

        await wrapper.trigger("click");

        expect(onClick).toHaveBeenCalledTimes(1);
        expect(onClick.mock.calls[0]![0]).toBeInstanceOf(MouseEvent);
    });

    it("calls a click handler once per click on a span badge", async () => {
        const onClick = vi.fn();
        const wrapper = mount(GBadge, { attrs: { onClick } });

        await wrapper.trigger("click");

        expect(onClick).toHaveBeenCalledTimes(1);
    });
});
