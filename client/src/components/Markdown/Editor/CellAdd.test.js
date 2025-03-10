import { mount } from "@vue/test-utils";
import { BAlert } from "bootstrap-vue";

import CellAdd from "./CellAdd.vue";
import CellButton from "./CellButton.vue";
import CellOption from "./CellOption.vue";
import DelayedInput from "@/components/Common/DelayedInput.vue";
import Popper from "@/components/Popper/Popper.vue";

jest.mock("./templates", () => ({
    cellTemplates: [
        {
            name: "Category 1",
            templates: [
                { title: "Option A", description: "Desc A", cell: { id: 1 } },
                { title: "Option B", description: "Desc B", cell: { id: 2 } },
            ],
        },
        {
            name: "Category 2",
            templates: [{ title: "Option C", description: "Desc C", cell: { id: 3 } }],
        },
    ],
}));

const createContainer = (tag = "div") => {
    const container = document.createElement(tag);
    document.body.appendChild(container);
    return container;
};

const mountTarget = () => {
    return mount(CellAdd, {
        attachTo: createContainer(),
        global: {
            components: { BAlert, CellButton, CellOption, DelayedInput, Popper },
        },
    });
};

describe("CellAdd.vue", () => {
    it("renders correctly", async () => {
        const wrapper = mountTarget();
        expect(wrapper.exists()).toBe(true);
        expect(wrapper.findComponent(CellButton).exists()).toBe(true);
    });

    it("opens the popper when clicking the button", async () => {
        const wrapper = mountTarget();
        await wrapper.findComponent(CellButton).trigger("click");
        await wrapper.vm.$nextTick();
        expect(wrapper.findComponent(Popper).exists()).toBe(true);
    });

    it("filters templates based on search input", async () => {
        const wrapper = mountTarget();
        await wrapper.vm.$nextTick();
        wrapper.findComponent(DelayedInput).vm.$emit("change", "option a");
        await wrapper.vm.$nextTick();
        const categories = wrapper.findAll(".cell-add-categories");
        expect(categories).toHaveLength(1);
        expect(categories.at(0).find(".text-info").text()).toBe("Category 1");
        expect(categories.at(0).find(".cell-option").text()).toContain("Option A");
    });

    it("shows 'No results found' when no templates match search", async () => {
        const wrapper = mountTarget();
        await wrapper.vm.$nextTick();
        wrapper.findComponent(DelayedInput).vm.$emit("change", "nonexistent");
        await wrapper.vm.$nextTick();
        expect(wrapper.findComponent(BAlert).exists()).toBe(true);
        expect(wrapper.findComponent(BAlert).text()).toContain('No results found for "nonexistent".');
    });

    it("emits a 'click' event when a cell option is selected", async () => {
        const wrapper = mountTarget();
        await wrapper.findComponent(CellButton).trigger("click");
        await wrapper.vm.$nextTick();
        const option = wrapper.findComponent(CellOption);
        await option.trigger("click");
        expect(wrapper.emitted("click")).toBeTruthy();
        expect(wrapper.emitted("click")?.[0][0]).toMatchObject({
            configure: false,
            toggle: true,
            id: expect.any(Number),
        });
    });
});
