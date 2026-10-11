import { createTestRouter } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it, vi } from "vitest";

import { Toast } from "@/composables/toast";

import Home from "./Home.vue";

vi.mock("@/composables/toast", () => {
    const toast = { addToast: vi.fn() };
    return { Toast: toast, useToast: () => toast };
});
vi.mock("@/components/Tool/ToolForm.vue", () => ({
    default: { name: "ToolForm", props: ["id", "uuid", "version", "jobId"], render: () => null },
}));
vi.mock("@/components/Workflow/Run/WorkflowRun.vue", () => ({
    default: {
        name: "WorkflowRun",
        props: ["workflowId", "version", "preferSimpleForm", "simpleFormTargetHistory", "simpleFormUseJobCache"],
        render: () => null,
    },
}));
vi.mock("@/entry/analysis/modules/CenterFrame.vue", () => ({
    default: { name: "CenterFrame", props: ["src"], render: () => null },
}));

async function mountHome(path: string, config: Record<string, unknown> = {}) {
    const router = createTestRouter();
    await router.push(path);
    const replace = vi.spyOn(router, "replace");
    const wrapper = mount(Home, {
        props: { config, query: router.currentRoute.value.query },
        global: { plugins: [router] },
    });
    await flushPromises();
    return { wrapper, replace };
}

describe("Home", () => {
    it("shows the welcome page without a tool or workflow query", async () => {
        const { wrapper } = await mountHome("/");
        expect(wrapper.findComponent({ name: "CenterFrame" }).props("src")).toEqual("/welcome");
    });

    it("shows the welcome page for the upload tool", async () => {
        const { wrapper } = await mountHome("/?tool_id=upload1");
        expect(wrapper.findComponent({ name: "ToolForm" }).exists()).toBe(false);
        expect(wrapper.findComponent({ name: "CenterFrame" }).exists()).toBe(true);
    });

    it("decodes the tool id and version unless they contain a plus", async () => {
        const { wrapper } = await mountHome("/?tool_id=toolshed%252Frepo%252Fcat&version=1.0%252Bgalaxy0");
        expect(wrapper.findComponent({ name: "ToolForm" }).props()).toEqual({
            id: "toolshed/repo/cat",
            uuid: undefined,
            version: "1.0+galaxy0",
            jobId: undefined,
        });
        const plusTool = await mountHome("/?tool_id=a%2Bb%252F&job_id=J1");
        expect(plusTool.wrapper.findComponent({ name: "ToolForm" }).props()).toEqual({
            id: "a+b%2F",
            uuid: undefined,
            version: undefined,
            jobId: "J1",
        });
    });

    it("passes the simplified workflow run settings to WorkflowRun", async () => {
        const config = {
            simplified_workflow_run_ui: "off",
            simplified_workflow_run_ui_target_history: "current",
            simplified_workflow_run_ui_job_cache: "on",
        };
        const { wrapper } = await mountHome("/?workflow_id=W1&version=2", config);
        expect(wrapper.findComponent({ name: "WorkflowRun" }).props()).toEqual({
            workflowId: "W1",
            version: "2",
            preferSimpleForm: false,
            simpleFormTargetHistory: "current",
            simpleFormUseJobCache: true,
        });
        const overridden = await mountHome("/?workflow_id=W1&simplified_workflow_run_ui=prefer", config);
        expect(overridden.wrapper.findComponent({ name: "WorkflowRun" }).props("preferSimpleForm")).toBe(true);
    });

    it("toasts a queued data import and strips the notification param", async () => {
        const { replace } = await mountHome("/?notification=tool-submitted&foo=bar");
        expect(Toast.addToast).toHaveBeenCalledWith("Check your history panel for progress.", {
            title: "Data import queued",
            variant: "info",
            duration: 0,
        });
        expect(replace).toHaveBeenCalledWith({ query: { foo: "bar" } });
    });
});
