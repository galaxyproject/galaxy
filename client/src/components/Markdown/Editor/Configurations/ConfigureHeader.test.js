import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";

import ConfigureHeader from "./ConfigureHeader.vue";
import CellButton from "@/components/Markdown/Editor/CellButton.vue";


function mountComponent(props = {}) {
    const globalConfig = getLocalVue();
    return mount(ConfigureHeader, {
        props: { hasChanged: undefined, ...props },
        global: {
            ...globalConfig.global,
            stubs: {
                BModal: {
                    template: "<div><slot></slot><slot name='modal-header'></slot><slot name='modal-footer'></slot></div>",
                    props: ["visible"],
                },
                BButton: {
                    template: "<button @click=\"$emit('click')\"><slot /></button>",
                },
                FontAwesomeIcon: true,
                Heading: {
                    template: "<div><slot /></div>",
                },
            },
        },
    });
}

describe("ConfigureHeader.vue", () => {
    it("renders headings and instructions", () => {
        const wrapper = mountComponent({ hasChanged: false });
        expect(wrapper.text()).toContain("Attach Data");
        expect(wrapper.text()).toContain("Fill in the fields below to map required inputs to this cell.");
    });

    it("renders Apply Changes and Cancel buttons when hasChanged is defined", () => {
        const wrapper = mountComponent({ hasChanged: false });
        const buttons = wrapper.findAllComponents(CellButton);
        expect(buttons.length).toBe(2);
        expect(buttons[0].props("title")).toBe("Apply Changes");
        expect(buttons[1].props("title")).toBe("Cancel");
    });

    it("always renders Cancel button", () => {
        const wrapper = mountComponent({ hasChanged: undefined });
        const buttons = wrapper.findAllComponents(CellButton);
        const cancelBtn = buttons[buttons.length - 1];
        expect(cancelBtn.exists()).toBe(true);
        expect(cancelBtn.props("title")).toBe("Cancel");
    });

    it("emits ok when Apply Changes is clicked", async () => {
        const wrapper = mountComponent({ hasChanged: true });
        const applyBtn = wrapper.findAllComponents(CellButton)[0];
        await applyBtn.trigger("click");
        expect(wrapper.emitted("ok")).toBeTruthy();
    });

    it("emits cancel immediately if hasChanged is false", async () => {
        const wrapper = mountComponent({ hasChanged: false });
        const cancelBtn = wrapper.findAllComponents(CellButton)[1];
        await cancelBtn.trigger("click");
        expect(wrapper.emitted("cancel")).toBeTruthy();
    });

    it("shows modal if hasChanged is true and Cancel is clicked", async () => {
        const wrapper = mountComponent({ hasChanged: true });
        const cancelBtn = wrapper.findAllComponents(CellButton)[1];
        await cancelBtn.trigger("click");
        expect(wrapper.vm.showModal).toBe(true);
    });

    it("emits cancel from modal Discard Changes button", async () => {
        const wrapper = mountComponent({ hasChanged: true });
        wrapper.vm.showModal = true;
        await wrapper.vm.$nextTick();
        const buttons = wrapper.findAll("button");
        const discardBtn = buttons.find((b) => b.text().includes("Discard Changes"));
        await discardBtn.trigger("click");
        expect(wrapper.emitted("cancel")).toBeTruthy();
    });

    it("emits ok from modal Apply Changes button", async () => {
        const wrapper = mountComponent({ hasChanged: true });
        wrapper.vm.showModal = true;
        await wrapper.vm.$nextTick();
        const buttons = wrapper.findAll("button");
        const applyBtn = buttons.find((b) => b.text().includes("Apply Changes"));
        await applyBtn.trigger("click");
        expect(wrapper.emitted("ok")).toBeTruthy();
    });
});
