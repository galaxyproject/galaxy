import { composeStories } from "@storybook/vue3-vite";
import { nth } from "@tests/vitest/helpers";
import { useStoryMount } from "@tests/vitest/stories";
import flushPromises from "flush-promises";
import { describe, expect, it, vi } from "vitest";

import { sanitizeHtml } from "@/directives/sanitizeHtml";

import { CORE_TOURS, RNA_SEQ_TOUR } from "./test_fixtures";
import * as TourListStories from "./TourList.stories";

const { CoreTours, FormattedDescription } = composeStories(TourListStories);
const mountStory = useStoryMount();

const SELECTORS = {
    TOUR_LINK: "[data-description='tour link']",
};

async function mountTourList(story) {
    const wrapper = mountStory(story);
    await flushPromises();
    return wrapper;
}

describe("TourList", () => {
    it("renders a link to each tour", async () => {
        const wrapper = await mountTourList(CoreTours);

        const links = wrapper.findAll(SELECTORS.TOUR_LINK);
        expect(links.length).toBe(CORE_TOURS.length);
        CORE_TOURS.forEach((tour, index) => {
            expect(nth(links, index).text()).toContain(tour.name);
            expect(nth(links, index).attributes("href")).toBe(`/tours/${tour.id}`);
        });
    });

    it("renders tour descriptions through v-sanitize-html", async () => {
        vi.mocked(sanitizeHtml).mockClear();

        const wrapper = await mountTourList(FormattedDescription);

        expect(sanitizeHtml).toHaveBeenCalledWith(RNA_SEQ_TOUR.description, "default");
        expect(wrapper.find("b").text()).toBe("HISAT2");
    });
});
