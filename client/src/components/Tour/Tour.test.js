import { getLocalVue, nth } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import { sanitizeHtml } from "@/directives/sanitizeHtml";

import TourList from "./TourList.vue";

const { server, http } = useServerMock();

const localVue = getLocalVue();

const SELECTORS = {
    TOUR_LINK: "[data-description='tour link']",
};

async function mountTourList(tours) {
    server.use(http.get("/api/tours", ({ response }) => response(200).json(tours)));
    const wrapper = shallowMount(TourList, { global: localVue });
    await flushPromises();
    return wrapper;
}

describe("TourList", () => {
    it("renders a link for each tour", async () => {
        const wrapper = await mountTourList([
            {
                id: "intro-to-galaxy",
                name: "Intro to Galaxy",
                description: "Learn the basics",
                tags: ["beginner"],
            },
            {
                id: "advanced-analysis",
                name: "Advanced Analysis",
                description: "Deep dive into tools",
                tags: ["advanced"],
            },
        ]);

        const links = wrapper.findAll(SELECTORS.TOUR_LINK);
        expect(links.length).toBe(2);
        expect(nth(links, 0).text()).toContain("Intro to Galaxy");
        expect(nth(links, 1).text()).toContain("Advanced Analysis");
    });

    it("renders tour descriptions through v-sanitize-html", async () => {
        vi.mocked(sanitizeHtml).mockClear();

        const wrapper = await mountTourList([{ id: "t", name: "T", description: "Uses <b>markup</b>", tags: [] }]);

        expect(sanitizeHtml).toHaveBeenCalledWith("Uses <b>markup</b>", "default");
        expect(wrapper.find("b").text()).toBe("markup");
    });
});
