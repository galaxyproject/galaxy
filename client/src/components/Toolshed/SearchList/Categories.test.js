import { composeStories } from "@storybook/vue3-vite";
import { nth } from "@tests/vitest/helpers";
import { useStoryMount } from "@tests/vitest/stories";
import flushPromises from "flush-promises";
import { afterEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";

import { Services } from "../services";
import * as CategoriesStories from "./Categories.stories";

import Categories from "./Categories.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const stories = composeStories(CategoriesStories);
const mountStory = useStoryMount();

describe("Categories", () => {
    afterEach(() => {
        vi.restoreAllMocks();
    });

    it("shows the loading message while categories load", async () => {
        const wrapper = mountStory(stories.LoadingCategories).getComponent(Categories);
        await flushPromises();
        // LoadingSpan isn't stubbed, so check the real component's props directly.
        expect(wrapper.getComponent(LoadingSpan).props("message")).toBe("Loading categories");
    });

    it("renders category names, descriptions and repository counts in order", async () => {
        // The original rendering contract used string repository counts that the Tool
        // Shed never returns. Keep those exact expectations as a unit-only override;
        // the standalone story uses the backend's integer counts and full category model.
        vi.spyOn(Services.prototype, "getCategories").mockResolvedValueOnce([
            { name: "name_0", description: "description_0", repositories: "repositories_0" },
            { name: "name_1", description: "description_1", repositories: "repositories_1" },
        ]);
        const wrapper = mountStory(stories.AvailableCategories).getComponent(Categories);
        await nextTick();
        await vi.waitFor(() => wrapper.get("a"));
        const links = wrapper.findAll("a");
        expect(links.length).toBe(2);

        expect(nth(links, 0).text()).toContain("name_0");
        expect(nth(links, 1).text()).toContain("name_1");

        const rows = wrapper.findAll("tr");
        expect(rows.length).toBe(3);
        const cells = nth(rows, 1).findAll("td");
        expect(nth(cells, 1).text()).toBe("description_0");
        expect(nth(cells, 2).text()).toBe("repositories_0");
    });
});
