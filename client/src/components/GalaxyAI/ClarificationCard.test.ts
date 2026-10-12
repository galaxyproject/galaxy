import { composeStories } from "@storybook/vue3-vite";
import { nth } from "@tests/vitest/helpers";
import { useStoryMount } from "@tests/vitest/stories";
import { describe, expect, it } from "vitest";

import * as ClarificationCardStories from "./ClarificationCard.stories";

import ClarificationCard from "./ClarificationCard.vue";

const stories = composeStories(ClarificationCardStories);
const mountStory = useStoryMount();

function mountCard(story = stories.QuickReplyChoices) {
    return mountStory(story).getComponent(ClarificationCard);
}

describe("ClarificationCard", () => {
    it("renders the question", () => {
        const wrapper = mountCard();
        expect(wrapper.get(".clarification-question").text()).toBe("Do you want a tool recommendation or a tutorial?");
    });

    it("renders one button per option", () => {
        const wrapper = mountCard();
        const buttons = wrapper.findAll(".clarification-options button");
        expect(buttons.length).toBe(2);
        expect(nth(buttons, 0).text()).toBe("Tool recommendation");
        expect(nth(buttons, 1).text()).toBe("Tutorial");
    });

    it("emits select-option with the option text on click", async () => {
        const wrapper = mountCard();
        await nth(wrapper.findAll(".clarification-options button"), 1).trigger("click");
        expect(wrapper.emitted("select-option")).toEqual([["Tutorial"]]);
    });

    it("renders the question with no options and no buttons", () => {
        const wrapper = mountCard(stories.FreeTextAnswer);
        expect(wrapper.get(".clarification-question").text()).toBe("Do you want a tool recommendation or a tutorial?");
        expect(wrapper.findAll(".clarification-options button").length).toBe(0);
    });
});
