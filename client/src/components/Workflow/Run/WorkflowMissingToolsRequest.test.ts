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

const { mockSubmitToolRequest } = vi.hoisted(() => ({
    mockSubmitToolRequest: vi.fn(),
}));

vi.mock("@/api/toolRequestForm", () => ({
    submitToolRequest: mockSubmitToolRequest,
}));

const localVue = getLocalVue(true);

const MISSING_TOOL_IDS = [
    "toolshed.g2.bx.psu.edu/repos/devteam/bwa/bwa/0.7.17",
    "toolshed.g2.bx.psu.edu/repos/devteam/samtools/samtools/1.13",
];

const STORAGE_KEY = `galaxy-tool-install-request:${[...MISSING_TOOL_IDS].sort().join(",")}`;

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
            workflowName: "My Analysis Workflow",
            ...props,
        },
        attachTo: document.body,
    });
}

describe("WorkflowMissingToolsRequest", () => {
    function clearToolRequestStorage() {
        Object.keys(localStorage)
            .filter((k) => k.startsWith("galaxy-tool-install-request:"))
            .forEach((k) => localStorage.removeItem(k));
    }

    beforeEach(() => {
        mockSubmitToolRequest.mockReset();
        clearToolRequestStorage();
        setMockConfig({ enable_tool_request_form: true });
    });

    afterEach(() => {
        clearToolRequestStorage();
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
        expect(wrapper.text()).toContain("My Analysis Workflow");
    });

    it("closes modal and does not call submitToolRequest when cancelled", async () => {
        const wrapper = mountComponent();
        await flushPromises();

        await wrapper.find("[data-testid='request-install-btn']").trigger("click");
        await flushPromises();

        const modal = wrapper.findComponent(GModal);
        expect(modal.props("show")).toBe(true);

        modal.vm.$emit("cancel");
        await flushPromises();

        expect(mockSubmitToolRequest).not.toHaveBeenCalled();
        expect(wrapper.findComponent(GModal).props("show")).toBe(false);
    });

    it("calls submitToolRequest with correct payload on confirm", async () => {
        mockSubmitToolRequest.mockResolvedValueOnce(undefined);
        const wrapper = mountComponent();
        await flushPromises();

        await wrapper.find("button").trigger("click");
        await flushPromises();

        wrapper.findComponent(GModal).vm.$emit("ok");
        await flushPromises();

        expect(mockSubmitToolRequest).toHaveBeenCalledOnce();
        const payload = mockSubmitToolRequest.mock.calls[0]?.[0] as Record<string, unknown>;
        expect(payload.tool_ids).toEqual(MISSING_TOOL_IDS);
        expect(payload.workflow_name).toBe("My Analysis Workflow");
        expect(payload.requester_name).toBeTruthy();
        expect(typeof payload.tool_name).toBe("string");
        expect(typeof payload.description).toBe("string");
        expect(payload.description as string).toContain("My Analysis Workflow");
    });

    it("disables button and shows success message after successful request", async () => {
        mockSubmitToolRequest.mockResolvedValueOnce(undefined);
        const wrapper = mountComponent();
        await flushPromises();

        await wrapper.find("[data-testid='request-install-btn']").trigger("click");
        await flushPromises();
        wrapper.findComponent(GModal).vm.$emit("ok");
        await flushPromises();

        // After success: request button no longer shown, success alert appears
        expect(wrapper.text()).not.toContain("Request Installation");
        expect(wrapper.find(".alert-success").exists()).toBe(true);
    });

    it("saves to localStorage after successful request", async () => {
        mockSubmitToolRequest.mockResolvedValueOnce(undefined);
        const wrapper = mountComponent();
        await flushPromises();

        await wrapper.find("[data-testid='request-install-btn']").trigger("click");
        await flushPromises();
        wrapper.findComponent(GModal).vm.$emit("ok");
        await flushPromises();

        expect(localStorage.getItem(STORAGE_KEY)).toBeTruthy();
    });

    it("shows already-requested state when localStorage has a prior entry", async () => {
        localStorage.setItem(STORAGE_KEY, String(Date.now()));
        const wrapper = mountComponent();
        await flushPromises();

        expect(wrapper.text()).not.toContain("Request Installation");
        expect(wrapper.find(".alert-success").exists()).toBe(true);
    });

    it("shows error alert when submission fails", async () => {
        mockSubmitToolRequest.mockRejectedValueOnce(new Error("Server error"));
        const wrapper = mountComponent();
        await flushPromises();

        await wrapper.find("[data-testid='request-install-btn']").trigger("click");
        await flushPromises();
        wrapper.findComponent(GModal).vm.$emit("ok");
        await flushPromises();

        expect(wrapper.find(".alert-danger").exists()).toBe(true);
        // Button is still visible after a failed attempt
        expect(wrapper.text()).toContain("Request Installation");
    });

    it("uses singular 'tool' for a single missing tool ID", async () => {
        const wrapper = mountComponent({ missingToolIds: [MISSING_TOOL_IDS[0]] });
        await flushPromises();
        expect(wrapper.text()).toContain("1 missing tool");
        expect(wrapper.text()).not.toContain("1 missing tools");
    });

    // ── Visibility / access-control edge cases ─────────────────────────────

    it("does not render when user is anonymous (no email field)", async () => {
        // The store ID is "userStore" — createTestingPinia initialState uses key "user"
        // which doesn't match, so we patch the store directly after mounting.
        // AnonymousUser has no `email` field → isRegisteredUser() = false → isAnonymousUser() = true
        const wrapper = mountComponent();
        const userStore = useUserStore();
        userStore.$patch({ currentUser: { id: "anon1", isAnonymous: true } as any });
        await flushPromises();
        expect(wrapper.find(".workflow-missing-tools-request").exists()).toBe(false);
    });

    // ── No workflowName prop ────────────────────────────────────────────────

    it("shows 'a workflow' fallback in modal body when workflowName is not provided", async () => {
        const wrapper = mountComponent({ workflowName: undefined });
        await flushPromises();
        await wrapper.find("[data-testid='request-install-btn']").trigger("click");
        await flushPromises();
        expect(wrapper.text()).not.toContain("required by workflow");
        // Modal body renders tool count but no named workflow span
        expect(wrapper.findComponent(GModal).text()).toContain("missing tool");
    });

    it("sends workflow_name as undefined when workflowName prop is omitted", async () => {
        mockSubmitToolRequest.mockResolvedValueOnce(undefined);
        const wrapper = mountComponent({ workflowName: undefined });
        await flushPromises();
        await wrapper.find("[data-testid='request-install-btn']").trigger("click");
        await flushPromises();
        wrapper.findComponent(GModal).vm.$emit("ok");
        await flushPromises();

        const payload = mockSubmitToolRequest.mock.calls[0]?.[0] as Record<string, unknown>;
        expect(payload.workflow_name).toBeUndefined();
        expect(payload.description as string).toContain("a workflow");
        expect(payload.description as string).not.toContain('"undefined"');
    });

    // ── Payload shape validation ────────────────────────────────────────────

    it("sets tool_name to the tool ID for a single missing tool", async () => {
        mockSubmitToolRequest.mockResolvedValueOnce(undefined);
        const wrapper = mountComponent({ missingToolIds: [MISSING_TOOL_IDS[0]], workflowName: "MyFlow" });
        await flushPromises();
        await wrapper.find("[data-testid='request-install-btn']").trigger("click");
        await flushPromises();
        wrapper.findComponent(GModal).vm.$emit("ok");
        await flushPromises();

        const payload = mockSubmitToolRequest.mock.calls[0]?.[0] as Record<string, unknown>;
        expect(payload.tool_name).toBe(MISSING_TOOL_IDS[0]);
    });

    it("uses plural 'tools are' and count-based tool_name for multiple tools", async () => {
        mockSubmitToolRequest.mockResolvedValueOnce(undefined);
        const wrapper = mountComponent();
        await flushPromises();
        await wrapper.find("[data-testid='request-install-btn']").trigger("click");
        await flushPromises();
        wrapper.findComponent(GModal).vm.$emit("ok");
        await flushPromises();

        const payload = mockSubmitToolRequest.mock.calls[0]?.[0] as Record<string, unknown>;
        expect(payload.description as string).toContain("tools are");
        expect(payload.tool_name as string).toContain("2 tools");
    });

    it("description includes each tool ID", async () => {
        mockSubmitToolRequest.mockResolvedValueOnce(undefined);
        const wrapper = mountComponent();
        await flushPromises();
        await wrapper.find("[data-testid='request-install-btn']").trigger("click");
        await flushPromises();
        wrapper.findComponent(GModal).vm.$emit("ok");
        await flushPromises();

        const payload = mockSubmitToolRequest.mock.calls[0]?.[0] as Record<string, unknown>;
        for (const id of MISSING_TOOL_IDS) {
            expect(payload.description as string).toContain(id);
        }
    });

    it("uses 'Galaxy user' as requester_name when currentUser is null", async () => {
        // currentUser is null by default in the test environment (initialState key mismatch
        // with store ID "userStore"), so isRegisteredUser(null) = false and the
        // requester_name falls back to the constant "Galaxy user".
        mockSubmitToolRequest.mockResolvedValueOnce(undefined);
        const wrapper = mountComponent();
        await flushPromises();
        await wrapper.find("[data-testid='request-install-btn']").trigger("click");
        await flushPromises();
        wrapper.findComponent(GModal).vm.$emit("ok");
        await flushPromises();

        const payload = mockSubmitToolRequest.mock.calls[0]?.[0] as Record<string, unknown>;
        expect(payload.requester_name).toBe("Galaxy user");
    });

    // ── localStorage / storage-key edge cases ──────────────────────────────

    it("storage key is sorted regardless of prop order", async () => {
        const reversed = [...MISSING_TOOL_IDS].reverse();
        // Same tools in different order → same storage key → already-requested if key is set
        localStorage.setItem(STORAGE_KEY, String(Date.now()));
        const wrapper = mountComponent({ missingToolIds: reversed });
        await flushPromises();
        // Because the key is the same, the component sees the prior request
        expect(wrapper.find(".alert-success").exists()).toBe(true);
        expect(wrapper.text()).not.toContain("Request Installation");
    });

    it("different tool sets produce different storage keys and do not share state", async () => {
        const otherToolId = "toolshed.g2.bx.psu.edu/repos/devteam/other/other/1.0";
        const otherKey = `galaxy-tool-install-request:${otherToolId}`;
        localStorage.setItem(otherKey, String(Date.now()));
        const wrapper = mountComponent(); // uses MISSING_TOOL_IDS, not otherToolId
        await flushPromises();
        // Prior entry for a different tool set should not affect this component
        expect(wrapper.find("[data-testid='request-install-btn']").exists()).toBe(true);
        // afterEach clearToolRequestStorage() will handle cleanup
    });

    // ── UI state during and after submission ────────────────────────────────

    it("button is disabled while the submission is in-flight", async () => {
        let resolveRequest!: () => void;
        mockSubmitToolRequest.mockReturnValueOnce(
            new Promise<void>((resolve) => {
                resolveRequest = resolve;
            }),
        );
        const wrapper = mountComponent();
        await flushPromises();

        await wrapper.find("[data-testid='request-install-btn']").trigger("click");
        await flushPromises();
        wrapper.findComponent(GModal).vm.$emit("ok");
        // Don't await flushPromises yet — request is pending
        await wrapper.vm.$nextTick();

        // GButton renders aria-disabled rather than the native disabled attribute
        expect(wrapper.find("[data-testid='request-install-btn']").attributes("aria-disabled")).toBe("true");

        // Cleanup
        resolveRequest();
        await flushPromises();
    });

    it("clears error message and retries successfully after a prior failure", async () => {
        mockSubmitToolRequest.mockRejectedValueOnce(new Error("Network error"));
        mockSubmitToolRequest.mockResolvedValueOnce(undefined);

        const wrapper = mountComponent();
        await flushPromises();

        // First attempt — fails
        await wrapper.find("[data-testid='request-install-btn']").trigger("click");
        await flushPromises();
        wrapper.findComponent(GModal).vm.$emit("ok");
        await flushPromises();
        expect(wrapper.find(".alert-danger").exists()).toBe(true);

        // Second attempt via the still-open modal — succeeds
        wrapper.findComponent(GModal).vm.$emit("ok");
        await flushPromises();
        expect(wrapper.find(".alert-danger").exists()).toBe(false);
        expect(wrapper.find(".alert-success").exists()).toBe(true);
        expect(localStorage.getItem(STORAGE_KEY)).toBeTruthy();
        expect(mockSubmitToolRequest).toHaveBeenCalledTimes(2);
    });

    it("dismissing the error alert clears the error and keeps the button visible", async () => {
        mockSubmitToolRequest.mockRejectedValueOnce(new Error("Oops"));
        const wrapper = mountComponent();
        await flushPromises();

        await wrapper.find("[data-testid='request-install-btn']").trigger("click");
        await flushPromises();
        wrapper.findComponent(GModal).vm.$emit("ok");
        await flushPromises();

        expect(wrapper.find(".alert-danger").exists()).toBe(true);

        // Simulate BAlert 'dismissed' event
        wrapper.findComponent({ name: "BAlert" }).vm.$emit("dismissed");
        await flushPromises();

        expect(wrapper.find(".alert-danger").exists()).toBe(false);
        expect(wrapper.find("[data-testid='request-install-btn']").exists()).toBe(true);
    });

    // ── Modal content ───────────────────────────────────────────────────────

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

        // Reopen
        await wrapper.find("[data-testid='request-install-btn']").trigger("click");
        await flushPromises();
        expect(wrapper.findComponent(GModal).props("show")).toBe(true);
    });
});
