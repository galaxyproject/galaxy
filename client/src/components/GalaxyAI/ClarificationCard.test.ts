import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import ClarificationCard from "./ClarificationCard.vue";

function mountCard(props: Record<string, unknown> = {}) {
    return mount(ClarificationCard as any, {
        propsData: {
            question: "Do you want a tool recommendation or a tutorial?",
            options: ["Tool recommendation", "Tutorial"],
            ...props,
        },
    });
}

describe("ClarificationCard", () => {
    it("renders the question", () => {
        const wrapper = mountCard();
        expect(wrapper.find(".clarification-question").text()).toBe("Do you want a tool recommendation or a tutorial?");
    });

    it("renders one button per option", () => {
        const wrapper = mountCard();
        const buttons = wrapper.findAll(".clarification-options button");
        expect(buttons.length).toBe(2);
        expect(buttons.at(0)!.text()).toBe("Tool recommendation");
        expect(buttons.at(1)!.text()).toBe("Tutorial");
    });

    it("emits select-option with the option text on click", async () => {
        const wrapper = mountCard();
        await wrapper.findAll(".clarification-options button").at(1)!.trigger("click");
        expect(wrapper.emitted("select-option")).toEqual([["Tutorial"]]);
    });

    it("renders the question with no options and no buttons", () => {
        const wrapper = mountCard({ options: [] });
        expect(wrapper.find(".clarification-question").text()).toBe("Do you want a tool recommendation or a tutorial?");
        expect(wrapper.findAll(".clarification-options button").length).toBe(0);
    });
});
