import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import SubworkflowUpgradeScopeModal from "./SubworkflowUpgradeScopeModal.vue";

const localVue = getLocalVue();

function mountModal(sharedWorkflowNames = ["Shared workflow"]) {
    return mount(SubworkflowUpgradeScopeModal as object, {
        propsData: { show: true, sharedWorkflowNames },
        localVue,
    });
}

function buttonWith(wrapper: ReturnType<typeof mountModal>, text: string) {
    return wrapper.findAll("button").filter((button) => button.text().includes(text));
}

describe("SubworkflowUpgradeScopeModal", () => {
    it("names the workflows that would be changed", () => {
        expect(mountModal(["Alpha", "Beta"]).text()).toContain("Alpha, Beta");
    });

    it("answers before it closes, so a caller waiting on the answer does not read the close as a dismissal", async () => {
        const wrapper = mountModal();
        await buttonWith(wrapper, "Only in this workflow").at(0).trigger("click");

        const events = Object.keys(wrapper.emitted());
        expect(events).toContain("confirm");
        expect(events).toContain("update:show");
        // vue-test-utils records emissions in order, so compare when each was seen
        const confirmOrder = wrapper.emitted("confirm")![0];
        expect(confirmOrder).toEqual([true]);
        expect(wrapper.emitted("update:show")![0]).toEqual([false]);
        expect(events.indexOf("confirm")).toBeLessThan(events.indexOf("update:show"));
    });

    it("distinguishes keeping the change here from updating the shared workflow", async () => {
        const priv = mountModal();
        await buttonWith(priv, "Only in this workflow").at(0).trigger("click");
        expect(priv.emitted("confirm")![0]).toEqual([true]);

        const shared = mountModal();
        await buttonWith(shared, "Also update").at(0).trigger("click");
        expect(shared.emitted("confirm")![0]).toEqual([false]);
    });
});
