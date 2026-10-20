import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { copy } from "@/utils/clipboard";

import WorkflowIndicators from "./WorkflowIndicators.vue";

vi.mock("@/utils/clipboard", () => ({
    copy: vi.fn(),
}));

const mockPush = vi.fn();
vi.mock("vue-router", async (importOriginal) => ({
    ...(await importOriginal<object>()),
    useRouter: () => ({ push: mockPush }),
}));

function mountComponent(sourceMetadata: Record<string, string>, overrides: Record<string, unknown> = {}) {
    return mount(WorkflowIndicators as object, {
        props: {
            workflow: {
                id: "workflow_id",
                name: "Workflow",
                owner: "owner",
                published: false,
                update_time: "2024-01-01T00:00:00",
                source_metadata: sourceMetadata,
                ...overrides,
            },
            publishedView: Boolean(overrides.published),
            noEditTime: true,
        },
        global: getLocalVue(),
    });
}

describe("WorkflowIndicators", () => {
    beforeEach(() => {
        vi.mocked(copy).mockClear();
        mockPush.mockClear();
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

    it.each([
        ["shared", false, "/workflows/list_shared_with_me?owner=someone_else"],
        ["published", true, "/workflows/list_published?owner=someone_else"],
    ])("filters by owner from the keyboard on the %s owner badge", async (_kind, published, path) => {
        const wrapper = mountComponent({}, { owner: "someone_else", published });
        const badge = wrapper.get('[aria-label="Filter by owner someone_else"]');
        expect(badge.attributes("role")).toBe("button");
        expect(badge.attributes("tabindex")).toBe("0");

        await badge.trigger("keydown", { key: "Enter" });
        expect(mockPush).toHaveBeenCalledWith(path);
        expect(wrapper.emitted("updateFilter")?.[0]).toEqual(["user", "'someone_else'"]);

        await badge.trigger("keydown", { key: " " });
        expect(mockPush).toHaveBeenCalledTimes(2);
    });
});
