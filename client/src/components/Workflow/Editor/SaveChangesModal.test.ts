import { getLocalVue } from "@tests/vitest/helpers";
import { mount, type Wrapper } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import type Vue from "vue";

import SaveChangesModal from "./SaveChangesModal.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import GModal from "@/components/BaseComponents/GModal.vue";

const localVue = getLocalVue();

const CANCEL = 0;
const DONT_SAVE = 1;
const SAVE = 2;

function footerButtons(wrapper: Wrapper<Vue>) {
    return wrapper.find(".save-changes-modal-button-container").findAllComponents(GButton).wrappers;
}

function buttonsDisabled(wrapper: Wrapper<Vue>) {
    return footerButtons(wrapper).map((button) => button.props("disabled"));
}

describe("Workflow editor SaveChangesModal", () => {
    let wrapper: Wrapper<Vue>;

    beforeEach(() => {
        wrapper = mount(SaveChangesModal as object, {
            localVue,
            propsData: {
                showModal: true,
                navUrl: "/workflows/list",
                appendVersion: false,
            },
        }) as Wrapper<Vue>;
    });

    afterEach(() => {
        wrapper.destroy();
    });

    it("hands the parent the proceed choice", async () => {
        await footerButtons(wrapper).at(SAVE)!.vm.$emit("click");
        expect(wrapper.emitted()["on-proceed"]![0]).toEqual(["/workflows/list", true, false, false]);

        await footerButtons(wrapper).at(DONT_SAVE)!.vm.$emit("click");
        expect(wrapper.emitted()["on-proceed"]![1]).toEqual(["/workflows/list", false, true, false]);
    });

    it("Cancel closes without proceeding", async () => {
        await footerButtons(wrapper).at(CANCEL)!.vm.$emit("click");

        expect(wrapper.emitted()["update:show-modal"]![0]).toEqual([false]);
        expect(wrapper.emitted()["on-proceed"]).toBeUndefined();
    });

    it("disables its buttons while the parent acts on the choice", async () => {
        expect(buttonsDisabled(wrapper)).toEqual([false, false, false]);

        await footerButtons(wrapper).at(SAVE)!.vm.$emit("click");

        expect(buttonsDisabled(wrapper)).toEqual([true, true, true]);
    });

    it("re-enables its buttons every time it is shown again", async () => {
        // The parent keeps this instance alive, so a proceed that ends without navigating --
        // a failed save, a rejected push -- would otherwise leave every button disabled.
        await footerButtons(wrapper).at(SAVE)!.vm.$emit("click");
        expect(buttonsDisabled(wrapper)).toEqual([true, true, true]);

        await wrapper.setProps({ showModal: false });
        await wrapper.setProps({ showModal: true });

        expect(wrapper.findComponent(GModal).props("show")).toBe(true);
        expect(buttonsDisabled(wrapper)).toEqual([false, false, false]);
    });
});
