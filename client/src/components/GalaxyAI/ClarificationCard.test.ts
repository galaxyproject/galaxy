import { nth } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import ClarificationCard from "./ClarificationCard.vue";

function mountCard(props: Partial<InstanceType<typeof ClarificationCard>["$props"]> = {}) {
    return mount(ClarificationCard, {
        props: {
            question: "Do you want a tool recommendation or a tutorial?",
            options: ["Tool recommendation", "Tutorial"],
            ...props,
        },
    });
}

describe("ClarificationCard", () => {
    enableAutoUnmount(afterEach);

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
        const wrapper = mountCard({ options: [] });
        expect(wrapper.get(".clarification-question").text()).toBe("Do you want a tool recommendation or a tutorial?");
        expect(wrapper.findAll(".clarification-options button").length).toBe(0);
    });
});
