import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount, type Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { setMockConfig } from "@/composables/__mocks__/config";
import { useUserStore } from "@/stores/userStore";

import WorkflowMissingToolsRequest from "./WorkflowMissingToolsRequest.vue";
import GModal from "@/components/BaseComponents/GModal.vue";

vi.mock("@/composables/config");

const { mockSubmitUserNotification } = vi.hoisted(() => ({
    mockSubmitUserNotification: vi.fn(),
}));

vi.mock("@/api/notifications", () => ({
    submitUserNotification: mockSubmitUserNotification,
}));

const localVue = getLocalVue(true);

const MISSING_TOOL_IDS = [
    "toolshed.g2.bx.psu.edu/repos/devteam/bwa/bwa/0.7.17",
    "toolshed.g2.bx.psu.edu/repos/devteam/samtools/samtools/1.13",
];

const REGISTERED_USER = {
    id: "user1",
    username: "testuser",
    email: "testuser@galaxy.test",
    is_admin: false,
    isAnonymous: false,
    total_disk_usage: 0,
    nice_total_disk_usage: "0 bytes",
    quota_percent: null,
    quota: "0 bytes",
    preferences: {},
    active: true,
    deleted: false,
    purged: false,
};

function mountComponent(props: Record<string, unknown> = {}): Wrapper<Vue> {
    const pinia = createTestingPinia({
        createSpy: vi.fn,
        initialState: {
            user: { currentUser: REGISTERED_USER },
        },
    });
    setActivePinia(pinia);

    return mount(WorkflowMissingToolsRequest as object, {
        localVue,
        pinia,
        propsData: {
            missingToolIds: MISSING_TOOL_IDS,
            workflowId: "workflow-encoded-id-abc",
            ...props,
        },
        attachTo: document.body,
    });
}

describe("WorkflowMissingToolsRequest", () => {
    beforeEach(() => {
        mockSubmitUserNotification.mockReset();
        setMockConfig({ enable_tool_request_form: true });
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    it("renders the request button when feature is enabled and user is authenticated", async () => {
        const wrapper = mountComponent();
        await flushPromises();
        expect(wrapper.text()).toContain("Request Installation");
        expect(wrapper.text()).toContain("2 missing tools");
    });

    it("does not render when feature flag is disabled", async () => {
        setMockConfig({ enable_tool_request_form: false });
        const wrapper = mountComponent();
        await flushPromises();
        expect(wrapper.text()).not.toContain("Request Installation");
    });

    it("does not render when no tool IDs are provided", async () => {
        const wrapper = mountComponent({ missingToolIds: [] });
        await flushPromises();
        expect(wrapper.find(".workflow-missing-tools-request").exists()).toBe(false);
    });

    it("shows confirmation modal when button is clicked", async () => {
        const wrapper = mountComponent();
        await flushPromises();
        await wrapper.find("[data-testid='request-install-btn']").trigger("click");
        await flushPromises();
        const modal = wrapper.findComponent(GModal);
        expect(modal.props("show")).toBe(true);
    });

    it("closes modal and does not call submitUserNotification when cancelled", async () => {
        const wrapper = mountComponent();
        await flushPromises();

        await wrapper.find("[data-testid='request-install-btn']").trigger("click");
        await flushPromises();

        const modal = wrapper.findComponent(GModal);
        expect(modal.props("show")).toBe(true);

        modal.vm.$emit("cancel");
        await flushPromises();

        expect(mockSubmitUserNotification).not.toHaveBeenCalled();
        expect(wrapper.findComponent(GModal).props("show")).toBe(false);
    });

    it("calls submitUserNotification with correct payload on confirm", async () => {
        mockSubmitUserNotification.mockResolvedValueOnce("notification-id-xyz");
        const wrapper = mountComponent();
        await flushPromises();

        await wrapper.find("button").trigger("click");
        await flushPromises();

        wrapper.findComponent(GModal).vm.$emit("ok");
        await flushPromises();

        expect(mockSubmitUserNotification).toHaveBeenCalledOnce();
        const payload = mockSubmitUserNotification.mock.calls[0]?.[0] as Record<string, unknown>;
        expect(payload.tool_names).toEqual(MISSING_TOOL_IDS);
        expect(payload.workflow_id).toBe("workflow-encoded-id-abc");
        expect(typeof payload.description).toBe("string");
    });

    it("shows success alert with link after successful request", async () => {
        mockSubmitUserNotification.mockResolvedValueOnce("notification-id-xyz");
        const wrapper = mountComponent();
        await flushPromises();

        await wrapper.find("[data-testid='request-install-btn']").trigger("click");
        await flushPromises();
        wrapper.findComponent(GModal).vm.$emit("ok");
        await flushPromises();

        expect(wrapper.text()).not.toContain("Request Installation");
        expect(wrapper.find(".alert-success").exists()).toBe(true);
        expect(wrapper.text()).toContain("view your request");
    });

    it("success alert links to notification", async () => {
        mockSubmitUserNotification.mockResolvedValueOnce("notification-id-xyz");
        const wrapper = mountComponent();
        await flushPromises();

        await wrapper.find("[data-testid='request-install-btn']").trigger("click");
        await flushPromises();
        wrapper.findComponent(GModal).vm.$emit("ok");
        await flushPromises();

        const link = wrapper.find(".alert-success a");
        expect(link.exists()).toBe(true);
        expect(link.attributes("href")).toContain("#notification-card-notification-id-xyz");
    });

    it("shows error alert when submission fails", async () => {
        mockSubmitUserNotification.mockRejectedValueOnce(new Error("Server error"));
        const wrapper = mountComponent();
        await flushPromises();

        await wrapper.find("[data-testid='request-install-btn']").trigger("click");
        await flushPromises();
        wrapper.findComponent(GModal).vm.$emit("ok");
        await flushPromises();

        expect(wrapper.find(".alert-danger").exists()).toBe(true);
        expect(wrapper.text()).toContain("Request Installation");
    });

    it("uses singular 'tool' for a single missing tool ID", async () => {
        const wrapper = mountComponent({ missingToolIds: [MISSING_TOOL_IDS[0]] });
        await flushPromises();
        expect(wrapper.text()).toContain("1 missing tool");
        expect(wrapper.text()).not.toContain("1 missing tools");
    });

    it("does not render when user is anonymous", async () => {
        const wrapper = mountComponent();
        const userStore = useUserStore();
        userStore.$patch({ currentUser: { id: "anon1", isAnonymous: true } as any });
        await flushPromises();
        expect(wrapper.find(".workflow-missing-tools-request").exists()).toBe(false);
    });

    it("sends tool_names as array of IDs", async () => {
        mockSubmitUserNotification.mockResolvedValueOnce("notif-id");
        const wrapper = mountComponent({ missingToolIds: [MISSING_TOOL_IDS[0]], workflowId: "wf-id" });
        await flushPromises();
        await wrapper.find("[data-testid='request-install-btn']").trigger("click");
        await flushPromises();
        wrapper.findComponent(GModal).vm.$emit("ok");
        await flushPromises();

        const payload = mockSubmitUserNotification.mock.calls[0]?.[0] as Record<string, unknown>;
        expect(payload.tool_names).toEqual([MISSING_TOOL_IDS[0]]);
        expect(payload.workflow_id).toBe("wf-id");
    });

    it("description includes each tool ID", async () => {
        mockSubmitUserNotification.mockResolvedValueOnce("notif-id");
        const wrapper = mountComponent();
        await flushPromises();
        await wrapper.find("[data-testid='request-install-btn']").trigger("click");
        await flushPromises();
        wrapper.findComponent(GModal).vm.$emit("ok");
        await flushPromises();

        const payload = mockSubmitUserNotification.mock.calls[0]?.[0] as Record<string, unknown>;
        for (const id of MISSING_TOOL_IDS) {
            expect(payload.description as string).toContain(id);
        }
    });

    it("button is disabled while the submission is in-flight", async () => {
        let resolveRequest!: () => void;
        mockSubmitUserNotification.mockReturnValueOnce(
            new Promise<string>((resolve) => {
                resolveRequest = () => resolve("notif-id");
            }),
        );
        const wrapper = mountComponent();
        await flushPromises();

        await wrapper.find("[data-testid='request-install-btn']").trigger("click");
        await flushPromises();
        wrapper.findComponent(GModal).vm.$emit("ok");
        await wrapper.vm.$nextTick();

        expect(wrapper.find("[data-testid='request-install-btn']").attributes("aria-disabled")).toBe("true");

        resolveRequest();
        await flushPromises();
    });

    it("dismissing the error alert clears the error and keeps the button visible", async () => {
        mockSubmitUserNotification.mockRejectedValueOnce(new Error("Oops"));
        const wrapper = mountComponent();
        await flushPromises();

        await wrapper.find("[data-testid='request-install-btn']").trigger("click");
        await flushPromises();
        wrapper.findComponent(GModal).vm.$emit("ok");
        await flushPromises();

        expect(wrapper.find(".alert-danger").exists()).toBe(true);

        wrapper.findComponent({ name: "BAlert" }).vm.$emit("dismissed");
        await flushPromises();

        expect(wrapper.find(".alert-danger").exists()).toBe(false);
        expect(wrapper.find("[data-testid='request-install-btn']").exists()).toBe(true);
    });

    it("modal body shows singular 'tool' when there is exactly 1 missing tool", async () => {
        const wrapper = mountComponent({ missingToolIds: [MISSING_TOOL_IDS[0]] });
        await flushPromises();
        await wrapper.find("[data-testid='request-install-btn']").trigger("click");
        await flushPromises();
        expect(wrapper.findComponent(GModal).text()).toContain("1 missing tool");
        expect(wrapper.findComponent(GModal).text()).not.toContain("1 missing tools");
    });

    it("can cancel and then reopen the modal", async () => {
        const wrapper = mountComponent();
        await flushPromises();

        await wrapper.find("[data-testid='request-install-btn']").trigger("click");
        await flushPromises();
        expect(wrapper.findComponent(GModal).props("show")).toBe(true);

        wrapper.findComponent(GModal).vm.$emit("cancel");
        await flushPromises();
        expect(wrapper.findComponent(GModal).props("show")).toBe(false);

        await wrapper.find("[data-testid='request-install-btn']").trigger("click");
        await flushPromises();
        expect(wrapper.findComponent(GModal).props("show")).toBe(true);
    });
});
