import "@/composables/__mocks__/filter";

import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, suppressExpectedErrorMessages } from "@tests/vitest/helpers";
import { mount, type Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ToolInstallationRequestForm from "./ToolInstallationRequestForm.vue";
import GModal from "@/components/BaseComponents/GModal.vue";

const { mockSubmitToolInstallationRequest } = vi.hoisted(() => ({
    mockSubmitToolInstallationRequest: vi.fn(),
}));

vi.mock("@/api/notifications", () => ({
    submitToolInstallationRequest: mockSubmitToolInstallationRequest,
}));

const localVue = getLocalVue(true);

async function mountForm(): Promise<Wrapper<Vue>> {
    suppressExpectedErrorMessages(["Invalid prop: type check failed for prop"]);

    const pinia = createTestingPinia({ createSpy: vi.fn });
    const wrapper = mount(ToolInstallationRequestForm as object, {
        localVue,
        propsData: { show: true },
        pinia,
        attachTo: document.body,
    });
    await flushPromises();
    return wrapper;
}

/** Fill the two required fields: tool_name and description. */
async function fillRequiredFields(wrapper: Wrapper<Vue>, overrides: Record<string, string> = {}) {
    await wrapper.find("#tool-installation-request-name").setValue(overrides["tool_name"] ?? "FastQC");
    await wrapper
        .find("#tool-installation-request-description")
        .setValue(overrides["description"] ?? "Quality control for sequencing data");
    await flushPromises();
}

describe("ToolInstallationRequestForm", () => {
    beforeEach(() => {
        mockSubmitToolInstallationRequest.mockReset();
        vi.restoreAllMocks();
    });

    it("ok button follows the required fields", async () => {
        const wrapper = await mountForm();
        const modal = wrapper.findComponent(GModal);
        expect(modal.props("okDisabled")).toBe(true);

        await fillRequiredFields(wrapper);
        expect(modal.props("okDisabled")).toBe(false);
    });

    it("submits correct payload on ok", async () => {
        const wrapper = await mountForm();
        await wrapper.find("#tool-installation-request-name").setValue("FastQC");
        await wrapper.find("#tool-installation-request-url").setValue("https://github.com/s-andrews/FastQC");
        await wrapper.find("#tool-installation-request-description").setValue("Quality control for sequencing data");
        await wrapper.find("#tool-installation-request-domain").setValue("Genomics");
        await wrapper.find("#tool-installation-request-version").setValue("0.12.1");
        await wrapper.find("#tool-installation-request-additional-remarks").setValue("Optional extra info");
        await flushPromises();

        wrapper.findComponent(GModal).vm.$emit("ok");
        await flushPromises();

        expect(mockSubmitToolInstallationRequest).toHaveBeenCalledOnce();
        const payload = mockSubmitToolInstallationRequest.mock.calls[0]?.[0] as Record<string, unknown>;
        expect(payload).toMatchObject({
            tools: [
                {
                    name: "FastQC",
                    tool_url: "https://github.com/s-andrews/FastQC",
                    description: "Quality control for sequencing data",
                    scientific_domain: "Genomics",
                    requested_version: "0.12.1",
                },
            ],
            additional_remarks: "Optional extra info",
        });
    });

    it("rejects a field over its length limit and does not submit", async () => {
        const wrapper = await mountForm();
        await fillRequiredFields(wrapper, { tool_name: "x".repeat(256) });
        wrapper.findComponent(GModal).vm.$emit("ok");
        await flushPromises();
        expect(mockSubmitToolInstallationRequest).not.toHaveBeenCalled();
        expect(wrapper.find(".alert-danger").text()).toContain(
            "Tool Name is too long (256 characters; the maximum is 255).",
        );
    });

    it("rejects non-https URL and does not submit", async () => {
        const wrapper = await mountForm();
        await fillRequiredFields(wrapper);
        await wrapper.find("#tool-installation-request-url").setValue("http://example.com/tool");
        wrapper.findComponent(GModal).vm.$emit("ok");
        await flushPromises();
        expect(mockSubmitToolInstallationRequest).not.toHaveBeenCalled();
        expect(wrapper.text()).toContain("https://");
    });

    it("accepts an upper-case https scheme and submits the URL as typed", async () => {
        const wrapper = await mountForm();
        await fillRequiredFields(wrapper);
        await wrapper.find("#tool-installation-request-url").setValue("HTTPS://Example.com/Tool");
        wrapper.findComponent(GModal).vm.$emit("ok");
        await flushPromises();
        expect(mockSubmitToolInstallationRequest).toHaveBeenCalledOnce();
        const payload = mockSubmitToolInstallationRequest.mock.calls[0]?.[0] as { tools: { tool_url?: string }[] };
        expect(payload.tools[0]?.tool_url).toBe("HTTPS://Example.com/Tool");
    });

    it("clears a previous attempt's error banner when a later attempt fails URL validation", async () => {
        mockSubmitToolInstallationRequest.mockRejectedValueOnce(new Error("Network error"));
        const wrapper = await mountForm();
        await fillRequiredFields(wrapper);
        wrapper.findComponent(GModal).vm.$emit("ok");
        await flushPromises();
        expect(wrapper.find(".alert-danger").exists()).toBe(true);

        await wrapper.find("#tool-installation-request-url").setValue("http://example.com/tool");
        wrapper.findComponent(GModal).vm.$emit("ok");
        await flushPromises();

        // Only the inline URL error explains this attempt; the stale banner is gone.
        expect(wrapper.find(".alert-danger").exists()).toBe(false);
        expect(wrapper.text()).toContain("Only https:// URLs are allowed.");
        expect(mockSubmitToolInstallationRequest).toHaveBeenCalledOnce();
    });

    it("labels the cancel button 'Close' only once the request was submitted", async () => {
        const wrapper = await mountForm();
        expect(wrapper.findComponent(GModal).props("cancelText")).toBe("Cancel");
        await fillRequiredFields(wrapper);
        wrapper.findComponent(GModal).vm.$emit("ok");
        await flushPromises();
        expect(wrapper.findComponent(GModal).props("cancelText")).toBe("Close");
    });

    it("shows success alert after successful submission", async () => {
        const wrapper = await mountForm();
        await fillRequiredFields(wrapper);
        wrapper.findComponent(GModal).vm.$emit("ok");
        await flushPromises();
        expect(wrapper.find(".alert-success").exists()).toBe(true);
        expect(wrapper.text()).toContain("submitted");
    });

    it("shows error alert when submission fails", async () => {
        mockSubmitToolInstallationRequest.mockRejectedValue(new Error("Network error"));
        const wrapper = await mountForm();
        await fillRequiredFields(wrapper);
        wrapper.findComponent(GModal).vm.$emit("ok");
        await flushPromises();
        expect(wrapper.find(".alert-danger").exists()).toBe(true);
    });
});
