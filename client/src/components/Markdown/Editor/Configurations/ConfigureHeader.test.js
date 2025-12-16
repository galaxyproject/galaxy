import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ConfigureHeader from "./ConfigureHeader.vue";
import CellButton from "@/components/Markdown/Editor/CellButton.vue";

const mockConfirm = vi.fn();
vi.mock("@/composables/confirmDialog", () => ({
    useConfirmDialog: () => ({
        confirm: mockConfirm,
    }),
}));

const localVue = getLocalVue();

function mountComponent(props = {}) {
    return mount(ConfigureHeader, {
        global: localVue,
        props: { hasChanged: undefined, ...props },
        stubs: {
            BButton: {
                template: "<button @click=\"$emit('click')\"><slot /></button>",
            },
            FontAwesomeIcon: true,
            Heading: {
                template: "<div><slot /></div>",
            },
        },
    });
}

describe("ConfigureHeader.vue", () => {
    beforeEach(() => {
        mockConfirm.mockReset();
    });

    it("renders headings and instructions", () => {
        const wrapper = mountComponent({ hasChanged: false });
        expect(wrapper.text()).toContain("Attach Data");
        expect(wrapper.text()).toContain("Fill in the fields below to map required inputs to this cell.");
    });

    it("renders Apply Changes and Cancel buttons when hasChanged is defined", () => {
        const wrapper = mountComponent({ hasChanged: false });
        const buttons = wrapper.findAllComponents(CellButton);
        expect(buttons.length).toBe(2);
        expect(buttons.at(0).props("title")).toBe("Apply Changes");
        expect(buttons.at(1).props("title")).toBe("Cancel");
    });

    it("always renders Cancel button", () => {
        const wrapper = mountComponent({ hasChanged: undefined });
        const buttons = wrapper.findAllComponents(CellButton);
        const cancelBtn = buttons.at(buttons.length - 1);
        expect(cancelBtn.exists()).toBe(true);
        expect(cancelBtn.props("title")).toBe("Cancel");
    });

    it("emits ok when Apply Changes is clicked", async () => {
        const wrapper = mountComponent({ hasChanged: true });
        const applyBtn = wrapper.findAllComponents(CellButton).at(0);
        await applyBtn.trigger("click");
        expect(wrapper.emitted("ok")).toBeTruthy();
    });

    it("emits cancel immediately if hasChanged is false", async () => {
        const wrapper = mountComponent({ hasChanged: false });
        const cancelBtn = wrapper.findAllComponents(CellButton).at(1);
        await cancelBtn.trigger("click");
        expect(wrapper.emitted("cancel")).toBeTruthy();
    });

    it("shows confirmDialog if hasChanged is true and Cancel is clicked", async () => {
        const wrapper = mountComponent({ hasChanged: true });
        const cancelBtn = wrapper.findAllComponents(CellButton).at(1);
        await cancelBtn.trigger("click");
        expect(mockConfirm).toHaveBeenCalled();
    });

    it("emits ok when confirmDialog returns true (user chose Apply Changes)", async () => {
        // Simulate user choosing "Apply Changes" in the confirm dialog
        mockConfirm.mockResolvedValue(true);

        const wrapper = mountComponent({ hasChanged: true });
        const cancelBtn = wrapper.findAllComponents(CellButton).at(1);
        await cancelBtn.trigger("click");
        expect(wrapper.emitted("ok")).toBeTruthy();
        expect(wrapper.emitted("cancel")).toBeFalsy();
    });

    it("emits cancel when confirmDialog returns false (user chose Discard Changes)", async () => {
        // Simulate user choosing "Discard Changes" in the confirm dialog
        mockConfirm.mockResolvedValue(false);

        const wrapper = mountComponent({ hasChanged: true });
        const cancelBtn = wrapper.findAllComponents(CellButton).at(1);
        await cancelBtn.trigger("click");
        expect(wrapper.emitted("cancel")).toBeTruthy();
        expect(wrapper.emitted("ok")).toBeFalsy();
    });

    it("emits nothing when confirmDialog returns null (user dismissed without choosing)", async () => {
        // Simulate user dismissing the confirm dialog without making a choice
        mockConfirm.mockResolvedValue(null);

        const wrapper = mountComponent({ hasChanged: true });
        const cancelBtn = wrapper.findAllComponents(CellButton).at(1);
        await cancelBtn.trigger("click");
        expect(wrapper.emitted("ok")).toBeFalsy();
        expect(wrapper.emitted("cancel")).toBeFalsy();
    });
});
