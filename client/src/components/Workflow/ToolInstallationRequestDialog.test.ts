import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ToolInstallationRequestDialog from "./ToolInstallationRequestDialog.vue";
import GAlert from "@/components/BaseComponents/GAlert.vue";
import GModal from "@/components/BaseComponents/GModal.vue";

const { mockSubmitToolInstallationRequest } = vi.hoisted(() => ({
    mockSubmitToolInstallationRequest: vi.fn(),
}));

vi.mock("@/api/notifications", () => ({
    submitToolInstallationRequest: mockSubmitToolInstallationRequest,
}));

function mountDialog() {
    return mount(ToolInstallationRequestDialog as object, {
        props: { show: true, missingToolIds: ["toolshed.g2.bx.psu.edu/repos/devteam/bwa/bwa/0.7.17"] },
        global: getLocalVue(),
        attachTo: document.body,
    });
}

describe("ToolInstallationRequestDialog", () => {
    beforeEach(() => {
        mockSubmitToolInstallationRequest.mockReset();
    });

    it("shows a failed request as a dismissible alert inside the dialog", async () => {
        mockSubmitToolInstallationRequest.mockRejectedValueOnce(new Error("Server error"));
        const wrapper = mountDialog();

        wrapper.findComponent(GModal).vm.$emit("ok");
        await flushPromises();

        expect(wrapper.findComponent(GAlert).exists()).toBe(true);
        const alert = wrapper.findComponent(GModal).find(".alert-danger");
        expect(alert.attributes("role")).toBe("alert");
        expect(alert.text()).toContain("Server error");
        expect(wrapper.emitted("update:show")).not.toContainEqual([false]);

        await alert.find("button[aria-label='Close']").trigger("click");
        expect(wrapper.find(".alert-danger").exists()).toBe(false);
        wrapper.unmount();
    });

    it("closes the dialog once the request is sent", async () => {
        mockSubmitToolInstallationRequest.mockResolvedValueOnce(undefined);
        const wrapper = mountDialog();

        wrapper.findComponent(GModal).vm.$emit("ok");
        await flushPromises();

        expect(wrapper.find(".alert-danger").exists()).toBe(false);
        expect(wrapper.emitted("submitted")).toHaveLength(1);
        expect(wrapper.emitted("update:show")?.at(-1)).toEqual([false]);
        wrapper.unmount();
    });
});
