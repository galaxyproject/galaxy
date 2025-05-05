import { createTestingPinia } from "@pinia/testing";
import { mount } from "@vue/test-utils";
import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import flushPromises from "flush-promises";
import { getLocalVue } from "tests/jest/helpers";
import { withPrefix } from "utils/redirect";

import { useServerMock } from "@/api/client/__mocks__";

import MountTarget from "./MarkdownGalaxy.vue";

const { server, http } = useServerMock();

// mock routes
jest.mock("utils/redirect");
withPrefix.mockImplementation((url) => url);

jest.mock("@/composables/config", () => ({
    useConfig: jest.fn(() => ({
        config: {
            version_major: "test_version",
        },
        isConfigLoaded: true,
    })),
}));

const localVue = getLocalVue();
const axiosMock = new MockAdapter(axios);
const pinia = createTestingPinia({ stubActions: false });

function mapAxios(apiMap = {}) {
    axiosMock.reset();
    for (const [method, apiDetails] of Object.entries(apiMap)) {
        for (const [path, response] of Object.entries(apiDetails)) {
            axiosMock[method](path).reply(200, response);
        }
    }
}

function mountComponent(propsData = {}, apiMap = {}) {
    mapAxios(apiMap);
    server.use(
        http.get("/api/histories/test_history_id", ({ response }) =>
            response(200).json({ id: "test_history_id", name: "history_name" })
        )
    );
    return mount(MountTarget, {
        localVue,
        pinia,
        propsData,
        stubs: {
            FontAwesomeIcon: true,
        },
    });
}

describe("MarkdownContainer", () => {
    it("Renders version", async () => {
        const version = "test_version";
        const wrapper = mountComponent({
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
        const link = wrapper.find("a");
        expect(link.text()).toBe(collapse);
        const container = wrapper.find(".collapse");
        expect(container.attributes("style")).toBe("display: none;");
        await link.trigger("click");
        expect(container.attributes("style")).toBe("");
    });

    it("Renders time stamp", async () => {
        const time = new Date();
        jest.useFakeTimers().setSystemTime(time);
        const wrapper = mountComponent({
            content: "generate_time()",
        });
        const version = wrapper.find(".galaxy-time");
        expect(version.exists()).toBe(true);
        expect(version.text()).toBe(time.toUTCString());
    });

    it("Renders history link", async () => {
        const wrapper = mountComponent(
            {
                content: "history_link(history_id=test_history_id)",
            },
            {
                onPost: { "/api/histories": {} },
            }
        );
        expect(wrapper.find("a").text()).toBe("Click to Import History: ...");
        await flushPromises();
        const link = wrapper.find("a");
        expect(link.text()).toBe("Click to Import History: history_name");
        await link.trigger("click");
        const postedData = JSON.parse(axiosMock.history.post[0].data);
        expect(postedData.history_id).toBe("test_history_id");
        await flushPromises();
        const error = wrapper.find(".text-success");
        const message = error.find("span");
        expect(message.text()).toBe("Successfully Imported History: history_name!");
    });

    it("Renders history link (with failing import error message)", async () => {
        const wrapper = mountComponent({
            content: "history_link(history_id=test_history_id)",
        });
        await wrapper.find("a").trigger("click");
        await flushPromises();
        const error = wrapper.find(".text-danger");
        const message = error.find("span");
        expect(message.text()).toBe("Failed to handle History: history_name!");
    });

    it("Renders error for invalid directive syntax", async () => {
        const wrapper = mountComponent({
            content: "not_valid_content(",
        });
        const alert = wrapper.find(".alert-danger");
        expect(alert.exists()).toBe(true);
        expect(alert.text()).toContain("The directive provided below is invalid");
    });

    it("Renders error for invalid component type", async () => {
        const wrapper = mountComponent({
            content: "unknown_component()",
        });
        const alert = wrapper.find(".alert-danger");
        expect(alert.text()).toContain("Invalid component type");
    });

    it("Renders error for missing required label", async () => {
        const wrapper = mountComponent({
            content: "tool_a(input=foo)",
            labels: [{ type: "input", label: "NotFoo" }],
        });
        const alert = wrapper.find(".alert-danger");
        expect(alert.text()).toContain("Invalid component type tool_a");
    });

    it("Renders info alert if labels exist but no invocation_id is present", async () => {
        const wrapper = mountComponent({
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

    it("Renders danger alert if more than one label exists", async () => {
        const wrapper = mountComponent({
            content: "history_dataset_display(input=foo, output=bar)",
            labels: [
                { type: "input", label: "foo" },
                { type: "output", label: "bar" },
            ],
        });
        await flushPromises();
        const alert = wrapper.find(".alert-danger");
        expect(alert.text()).toContain("Invalid or missing label for history_dataset_display");
    });

    it("Renders loading span while invocation is loading", async () => {
        const mockInvocationStore = require("@/stores/invocationStore");
        mockInvocationStore.useInvocationStore = jest.fn(() => ({
            getInvocationById: () => null,
            getInvocationLoadError: () => null,
            isLoadingInvocation: jest.fn(() => true),
        }));
        const wrapper = mountComponent({
            content: "history_dataset_display(invocation_id=123, input=foo)",
            labels: [
                { type: "input", label: "foo" },
                { type: "output", label: "bar" },
            ],
        });
        await flushPromises();
        expect(wrapper.findComponent({ name: "LoadingSpan" }).exists()).toBe(true);
    });

    it("Handles invocation fetching and workflow ID resolution", async () => {
        const invocation = { workflow_id: "wf123", inputs: {}, outputs: {} };
        const mockInvocationStore = require("@/stores/invocationStore");
        const mockWorkflowStore = require("@/stores/workflowStore");
        mockInvocationStore.useInvocationStore = jest.fn(() => ({
            getInvocationById: () => invocation,
            getInvocationLoadError: () => null,
            isLoadingInvocation: () => false,
        }));
        const fetchWorkflowMock = jest.fn(() => Promise.resolve());
        mockWorkflowStore.useWorkflowStore = jest.fn(() => ({
            fetchWorkflowForInstanceIdCached: fetchWorkflowMock,
            getStoredWorkflowIdByInstanceId: () => "wf123",
        }));
        mountComponent({
            content: "tool_a(invocation_id=123, input=foo, output=bar)",
            labels: [
                { type: "input", label: "foo" },
                { type: "output", label: "bar" },
            ],
        });
        await flushPromises();
        expect(fetchWorkflowMock).toHaveBeenCalledWith("wf123");
    });
});
