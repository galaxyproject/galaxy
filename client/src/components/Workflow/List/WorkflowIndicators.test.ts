import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { copy } from "@/utils/clipboard";

import WorkflowIndicators from "./WorkflowIndicators.vue";

vi.mock("@/utils/clipboard", () => ({
    copy: vi.fn(),
}));

function mountComponent(sourceMetadata: Record<string, string>) {
    return mount(WorkflowIndicators as object, {
        props: {
            workflow: {
                id: "workflow_id",
                name: "Workflow",
                owner: "owner",
                published: false,
                update_time: "2024-01-01T00:00:00",
                source_metadata: sourceMetadata,
            },
            publishedView: false,
            noEditTime: true,
        },
        global: getLocalVue(),
    });
}

describe("WorkflowIndicators", () => {
    beforeEach(() => {
        vi.mocked(copy).mockClear();
    });

    it("copies the source URL when the import button is clicked", async () => {
        const wrapper = mountComponent({ url: "https://example.org/workflow.ga" });
        await wrapper.find(".workflow-external-link").trigger("click");
        expect(copy).toHaveBeenCalledWith("https://example.org/workflow.ga", "URL copied");
    });

    it("copies the TRS ID when the TRS button is clicked", async () => {
        const wrapper = mountComponent({ trs_server: "dockstore", trs_tool_id: "#workflow/github.com/org/repo" });
        await wrapper.find(".workflow-trs-icon").trigger("click");
        expect(copy).toHaveBeenCalledWith("#workflow/github.com/org/repo", "TRS ID copied");
    });
});
