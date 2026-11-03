import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";

import HistoryDatasetAsTable from "./Elements/HistoryDatasetAsTable.vue";
import MarkdownGalaxy from "./MarkdownGalaxy.vue";
import Heading from "@/components/Common/Heading.vue";

const { server, http } = useServerMock();

// mock routes
vi.mock("@/utils/redirect", () => ({
    withPrefix: vi.fn((url) => url),
}));

vi.mock("@/composables/config", () => ({
    useConfig: vi.fn(() => ({
        config: {
            version_major: "test_version",
        },
        isConfigLoaded: true,
    })),
}));

vi.mock("@/stores/invocationStore", () => ({
    useInvocationStore: vi.fn(() => ({
        getInvocationById: () => null,
        getInvocationLoadError: () => null,
        isLoadingInvocation: () => false,
    })),
}));

vi.mock("@/stores/workflowStore", () => ({
    useWorkflowStore: vi.fn(() => ({
        fetchWorkflowForInstanceIdCached: vi.fn(() => Promise.resolve()),
        getStoredWorkflowIdByInstanceId: () => null,
    })),
}));

enableAutoUnmount(afterEach);
afterEach(() => vi.useRealTimers());

let postRequests = [];

beforeEach(() => {
    postRequests = [];
});

function mountMarkdown(props = {}, options = {}) {
    const handlers = [
        http.get("/api/histories/test_history_id", ({ response }) =>
            response(200).json({ id: "test_history_id", name: "history_name" }),
        ),
    ];

    if (options.enableHistoryPost) {
        handlers.push(
            http.untyped.post("/api/histories", async ({ request }) => {
                const data = await request.json();
                postRequests.push({ url: request.url, data });
                return HttpResponse.json({});
            }),
        );
    }

    if (options.enableDatasetAsTable) {
        handlers.push(
            http.untyped.get("/api/datasets/dataset_id/get_content_as_text", () =>
                HttpResponse.json({ item_data: "a\tb\n", truncated: false }),
            ),
            http.untyped.get("/api/datasets/dataset_id", () =>
                HttpResponse.json({ metadata_columns: 2, metadata_column_names: ["a", "b"] }),
            ),
        );
    }

    server.use(...handlers);

    return mount(MarkdownGalaxy, {
        global: withPlugins(getLocalVue(), createTestingPinia({ createSpy: vi.fn, stubActions: false })),
        props,
        stubs: {
            FontAwesomeIcon: true,
        },
    });
}

describe("MarkdownGalaxy", () => {
    it("renders the Galaxy version and expands its optional collapse heading", async () => {
        const version = "test_version";
        const wrapper = mountMarkdown({
            content: "generate_galaxy_version()",
        });
        const versionEl = wrapper.find(".galaxy-version");
        expect(versionEl.exists()).toBe(true);
        expect(versionEl.text()).toContain(version);

        // test collapsing
        const nolink = wrapper.find("a");
        expect(nolink.exists()).toBe(false);
        const collapse = "Click here to expand/collapse";
        await wrapper.setProps({ content: `generate_galaxy_version(collapse="${collapse}")` });
        const heading = wrapper.findComponent(Heading);
        expect(heading.text()).toBe(collapse);
        const container = wrapper.find(".g-collapse");
        expect(container.classes()).not.toContain("g-collapse-open");
        await heading.find("h2").trigger("click");
        expect(container.classes()).toContain("g-collapse-open");
    });

    it("renders the current UTC timestamp", async () => {
        const time = new Date("2025-01-15T12:34:56Z");
        vi.useFakeTimers();
        vi.setSystemTime(time);
        const wrapper = mountMarkdown({
            content: "generate_time()",
        });
        const version = wrapper.find(".galaxy-time");
        expect(version.exists()).toBe(true);
        expect(version.text()).toBe(time.toUTCString());
    });

    it("loads the history link name and imports it on click", async () => {
        const wrapper = mountMarkdown(
            {
                content: "history_link(history_id=test_history_id)",
            },
            {
                enableHistoryPost: true,
            },
        );
        expect(wrapper.find("a").text()).toBe("Click to Import History: ...");
        await flushPromises();
        const link = wrapper.find("a");
        expect(link.text()).toBe("Click to Import History: history_name");
        await link.trigger("click");
        await flushPromises();
        expect(postRequests).toHaveLength(1);
        expect(postRequests[0].data.history_id).toBe("test_history_id");
        expect(wrapper.find(".text-success span").text()).toBe("Successfully Imported History: history_name!");
    });

    it("shows the history import error when the import request fails", async () => {
        server.use(http.untyped.post("/api/histories", () => HttpResponse.error()));
        const wrapper = mountMarkdown({
            content: "history_link(history_id=test_history_id)",
        });
        await wrapper.find("a").trigger("click");
        await flushPromises();
        expect(wrapper.find(".text-danger span").text()).toBe("Failed to handle History: history_name!");
    });

    it("shows an error for invalid directive syntax", async () => {
        const wrapper = mountMarkdown({
            content: "not_valid_content(",
        });
        const alert = wrapper.find(".alert-danger");
        expect(alert.exists()).toBe(true);
        expect(alert.text()).toContain("The directive provided below is invalid");
    });

    it("shows an error for an unknown component type", async () => {
        const wrapper = mountMarkdown({
            content: "unknown_component()",
        });
        const alert = wrapper.find(".alert-danger");
        expect(alert.text()).toContain("Invalid component type");
    });

    it("rejects an unknown component even with an unmatched input label", async () => {
        const wrapper = mountMarkdown({
            content: "tool_a(input=foo)",
            labels: [{ type: "input", label: "NotFoo" }],
        });
        const alert = wrapper.find(".alert-danger");
        expect(alert.text()).toContain("Invalid component type tool_a");
    });

    it("shows unavailable data when labels have no invocation ID", async () => {
        const wrapper = mountMarkdown({
            content: "history_dataset_display(input=foo)",
            labels: [
                { type: "input", label: "foo" },
                { type: "output", label: "bar" },
            ],
        });
        await flushPromises();
        const alert = wrapper.find(".alert-info");
        expect(alert.text()).toContain("Data for rendering not yet available for");
    });

    it("rejects a dataset directive with both input and output labels", async () => {
        const wrapper = mountMarkdown({
            content: "history_dataset_display(input=foo, output=bar)",
            labels: [
                { type: "input", label: "foo" },
                { type: "output", label: "bar" },
            ],
        });
        await flushPromises();
        const alert = wrapper.find(".alert-danger");
        expect(alert.text()).toMatch(/Invalid or missing label for\s*history_dataset_display/);
    });

    it("shows a loading indicator while the invocation loads", async () => {
        const { useInvocationStore } = await import("@/stores/invocationStore");
        vi.mocked(useInvocationStore).mockReturnValueOnce({
            getInvocationById: () => null,
            getInvocationLoadError: () => null,
            isLoadingInvocation: vi.fn(() => true),
        });
        const wrapper = mountMarkdown({
            content: "history_dataset_display(invocation_id=123, input=foo)",
            labels: [
                { type: "input", label: "foo" },
                { type: "output", label: "bar" },
            ],
        });
        await flushPromises();
        expect(wrapper.findComponent({ name: "LoadingSpan" }).exists()).toBe(true);
    });

    it("fetches the invocation workflow before resolving directive arguments", async () => {
        const invocation = { workflow_id: "wf123", inputs: {}, outputs: {} };
        const { useInvocationStore } = await import("@/stores/invocationStore");
        const { useWorkflowStore } = await import("@/stores/workflowStore");
        const fetchWorkflowMock = vi.fn(() => Promise.resolve());
        vi.mocked(useInvocationStore).mockReturnValueOnce({
            getInvocationById: () => invocation,
            getInvocationLoadError: () => null,
            isLoadingInvocation: () => false,
        });
        vi.mocked(useWorkflowStore).mockReturnValueOnce({
            fetchWorkflowForInstanceIdCached: fetchWorkflowMock,
            getStoredWorkflowIdByInstanceId: () => "wf123",
        });
        mountMarkdown({
            content: "tool_a(invocation_id=123, input=foo, output=bar)",
            labels: [
                { type: "input", label: "foo" },
                { type: "output", label: "bar" },
            ],
        });
        await flushPromises();
        expect(fetchWorkflowMock).toHaveBeenCalledWith("wf123");
    });

    it("parses compact and show_column_headers args as booleans, not truthy strings", async () => {
        const wrapper = mountMarkdown(
            {
                content:
                    "history_dataset_as_table(history_dataset_id=dataset_id, compact=false, show_column_headers=false)",
            },
            { enableDatasetAsTable: true },
        );
        await flushPromises();
        const table = wrapper.findComponent(HistoryDatasetAsTable);
        expect(table.props("compact")).toBe(false);
        expect(table.props("showColumnHeaders")).toBe(false);

        await wrapper.setProps({
            content: "history_dataset_as_table(history_dataset_id=dataset_id, compact=true, show_column_headers=true)",
        });
        await flushPromises();
        expect(table.props("compact")).toBe(true);
        expect(table.props("showColumnHeaders")).toBe(true);
    });

    it("defaults compact to false and show_column_headers to true when args are absent", async () => {
        const wrapper = mountMarkdown(
            { content: "history_dataset_as_table(history_dataset_id=dataset_id)" },
            { enableDatasetAsTable: true },
        );
        await flushPromises();
        const table = wrapper.findComponent(HistoryDatasetAsTable);
        expect(table.props("compact")).toBe(false);
        expect(table.props("showColumnHeaders")).toBe(true);
    });
});
