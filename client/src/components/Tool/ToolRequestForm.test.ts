import "@/composables/__mocks__/filter";

import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, suppressExpectedErrorMessages } from "@tests/vitest/helpers";
import { mount, type Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ToolRequestForm from "./ToolRequestForm.vue";
import GModal from "@/components/BaseComponents/GModal.vue";

const { mockSubmitUserNotification } = vi.hoisted(() => ({
    mockSubmitUserNotification: vi.fn(),
}));

vi.mock("@/api/notifications", () => ({
    submitUserNotification: mockSubmitUserNotification,
}));

const localVue = getLocalVue(true);

async function mountForm(show = true): Promise<Wrapper<Vue>> {
    suppressExpectedErrorMessages(["Invalid prop: type check failed for prop"]);

    const pinia = createTestingPinia({ createSpy: vi.fn });
    const wrapper = mount(ToolRequestForm as object, {
        localVue,
        propsData: { show },
        pinia,
        attachTo: document.body,
    });
    await flushPromises();
    return wrapper;
}

/** Fill the two required fields: tool_name and description. */
async function fillRequiredFields(wrapper: Wrapper<Vue>, overrides: Record<string, string> = {}) {
    await wrapper.find("#tool-request-name").setValue(overrides["tool_name"] ?? "FastQC");
    await wrapper
        .find("#tool-request-description")
        .setValue(overrides["description"] ?? "Quality control for sequencing data");
    await flushPromises();
}

describe("ToolRequestForm", () => {
    beforeEach(() => {
        mockSubmitUserNotification.mockReset();
        vi.restoreAllMocks();
    });

    it("show=false means modal is not open, show=true means modal is open", async () => {
        const wrapper = await mountForm(false);

        expect(wrapper.findComponent(GModal).props("show")).toBe(false);

        await wrapper.setProps({ show: true });
        await flushPromises();

        expect(wrapper.findComponent(GModal).props("show")).toBe(true);
    });

    it("renders form inputs inside the modal", async () => {
        const wrapper = await mountForm(true);
        expect(wrapper.find("#tool-request-name").exists()).toBe(true);
        expect(wrapper.find("#tool-request-description").exists()).toBe(true);
        expect(wrapper.find("#tool-request-url").exists()).toBe(true);
        expect(wrapper.find("#tool-request-additional-remarks").exists()).toBe(true);
        // Removed fields
        expect(wrapper.find("#tool-request-requester-affiliation").exists()).toBe(false);
        // Name and email are filled server-side; no fields for them in the form
        expect(wrapper.find("#tool-request-requester-name").exists()).toBe(false);
        expect(wrapper.find("#tool-request-requester-email").exists()).toBe(false);
    });

    it("ok button is disabled when required fields are empty", async () => {
        const wrapper = await mountForm(true);
        const modal = wrapper.findComponent(GModal);
        expect(modal.props("okDisabled")).toBe(true);
    });

    it("ok button is enabled when required fields are filled", async () => {
        const wrapper = await mountForm(true);
        await fillRequiredFields(wrapper);
        const modal = wrapper.findComponent(GModal);
        expect(modal.props("okDisabled")).toBe(false);
    });

    it("submits correct payload on ok", async () => {
        mockSubmitUserNotification.mockResolvedValueOnce("notif-id-123");
        const wrapper = await mountForm(true);
        await wrapper.find("#tool-request-name").setValue("FastQC");
        await wrapper.find("#tool-request-url").setValue("https://github.com/s-andrews/FastQC");
        await wrapper.find("#tool-request-description").setValue("Quality control for sequencing data");
        await wrapper.find("#tool-request-domain").setValue("Genomics");
        await wrapper.find("#tool-request-version").setValue("0.12.1");
        await wrapper.find("#tool-request-additional-remarks").setValue("Optional extra info");
        await flushPromises();

        wrapper.findComponent(GModal).vm.$emit("ok");
        await flushPromises();

        expect(mockSubmitUserNotification).toHaveBeenCalledOnce();
        const payload = mockSubmitUserNotification.mock.calls[0]?.[0] as Record<string, unknown>;
        expect(payload).toMatchObject({
            tool_names: ["FastQC"],
            tool_url: "https://github.com/s-andrews/FastQC",
            description: "Quality control for sequencing data",
            scientific_domain: "Genomics",
            requested_version: "0.12.1",
            additional_remarks: "Optional extra info",
        });
        // Requester email comes from the server (authenticated user), not the form
        expect(payload).not.toHaveProperty("requester_email");
        // Removed fields no longer sent
        expect(payload).not.toHaveProperty("requester_name");
        expect(payload).not.toHaveProperty("requester_affiliation");
        expect(payload).not.toHaveProperty("conda_available");
        expect(payload).not.toHaveProperty("test_data_available");
    });

    it("rejects non-https URL and does not submit", async () => {
        const wrapper = await mountForm(true);
        await fillRequiredFields(wrapper);
        await wrapper.find("#tool-request-url").setValue("http://example.com/tool");
        wrapper.findComponent(GModal).vm.$emit("ok");
        await flushPromises();
        expect(mockSubmitUserNotification).not.toHaveBeenCalled();
        expect(wrapper.text()).toContain("https://");
    });

    it("shows success alert after successful submission", async () => {
        mockSubmitUserNotification.mockResolvedValueOnce("notif-id-123");
        const wrapper = await mountForm(true);
        await fillRequiredFields(wrapper);
        wrapper.findComponent(GModal).vm.$emit("ok");
        await flushPromises();
        expect(wrapper.find(".alert-success").exists()).toBe(true);
        expect(wrapper.text()).toContain("submitted");
    });

    it("shows error alert when submission fails", async () => {
        mockSubmitUserNotification.mockRejectedValue(new Error("Network error"));
        const wrapper = await mountForm(true);
        await fillRequiredFields(wrapper);
        wrapper.findComponent(GModal).vm.$emit("ok");
        await flushPromises();
        expect(wrapper.find(".alert-danger").exists()).toBe(true);
    });

    it("does not call API when required fields are missing", async () => {
        const wrapper = await mountForm(true);
        // Only fill tool_name, leave description empty
        await wrapper.find("#tool-request-name").setValue("Samtools");
        await flushPromises();
        wrapper.findComponent(GModal).vm.$emit("ok");
        await flushPromises();
        expect(mockSubmitUserNotification).not.toHaveBeenCalled();
    });

    it("emits update:show=false when cancel event fires on modal", async () => {
        const wrapper = await mountForm(true);
        wrapper.findComponent(GModal).vm.$emit("cancel");
        await flushPromises();
        expect(wrapper.emitted("update:show")).toBeTruthy();
        expect((wrapper.emitted("update:show") as boolean[][])[0]).toEqual([false]);
    });
});
