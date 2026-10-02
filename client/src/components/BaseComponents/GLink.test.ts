import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";

import GLink from "./GLink.vue";

const localVue = getLocalVue(true);

const RouteStub = { render: () => null };

describe("GLink.vue link targets", () => {
    // Galaxy can be served under a URL prefix, so a router link's href has to come from
    // the router, which knows the base -- open-in-new-tab and copy-link use it as is.
    it("renders a router link's href with the router base", () => {
        const router = createRouter({
            history: createMemoryHistory("/galaxypf/"),
            routes: ["/", "/pages/create"].map((path) => ({ path, component: RouteStub })),
        });
        const wrapper = mount(GLink as object, { propsData: { to: "/pages/create" }, localVue, router });

        expect(wrapper.get("a").attributes("href")).toBe("/galaxypf/pages/create");
    });

    it("renders a plain anchor's href as given", () => {
        const wrapper = mount(GLink as object, { propsData: { href: "https://example.org/data.txt" }, localVue });

        expect(wrapper.get("a").attributes("href")).toBe("https://example.org/data.txt");
    });

    it("renders no href when disabled", () => {
        const wrapper = mount(GLink as object, {
            propsData: { href: "https://example.org/data.txt", disabled: true },
            localVue,
        });

        expect(wrapper.get("button").attributes("href")).toBeUndefined();
    });
});
