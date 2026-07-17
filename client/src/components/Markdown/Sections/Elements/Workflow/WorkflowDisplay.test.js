import { getLocalVue } from "@tests/vitest/helpers";
import { mount, shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";

import MountTarget from "./WorkflowDisplay.vue";
import ToolLinkPopover from "@/components/Tool/ToolLinkPopover.vue";
import WorkflowStepIcon from "@/components/WorkflowInvocationState/WorkflowStepIcon.vue";

// Translates only what a test asks for, so the other assertions see the source strings.
const translations = vi.hoisted(() => ({}));
vi.mock("@/utils/localization", async (importOriginal) => {
    const actual = await importOriginal();
    const localize = (text) => translations[text] ?? actual.localize(text);
    return { ...actual, default: localize, localize };
});

const localVue = getLocalVue(true);
const { server, http } = useServerMock();

let getRequests = [];

beforeEach(() => {
    getRequests = [];
});

afterEach(() => {
    Object.keys(translations).forEach((text) => delete translations[text]);
});

function mountDefault(data = { name: "workflow_name" }) {
    server.use(
        http.untyped.get("/api/workflows/workflow_id/download", ({ request }) => {
            getRequests.push({ url: request.url });
            return HttpResponse.json(data);
        }),
    );
    return mount(MountTarget, {
        props: {
            workflowId: "workflow_id",
            embedded: false,
            expanded: false,
        },
        // ToolLinkPopover fetches tool details we don't mock here
        global: { ...localVue, stubs: { ...localVue.stubs, ToolLinkPopover: true } },
    });
}

function mountError(errContent) {
    const data = {
        err_msg: errContent,
    };
    server.use(
        http.untyped.get("/api/workflows/workflow_id/download", () => {
            return HttpResponse.json(data, { status: 400 });
        }),
    );
    return mount(MountTarget, {
        props: {
            workflowId: "workflow_id",
            embedded: false,
            expanded: false,
        },
        global: localVue,
    });
}

function mountWithSteps(steps) {
    server.use(
        http.untyped.get("/api/workflows/workflow_id/download", () => {
            return HttpResponse.json({ name: "workflow_name", steps });
        }),
    );
    return shallowMount(MountTarget, {
        props: {
            workflowId: "workflow_id",
            embedded: false,
            expanded: false,
        },
        // The real GLink, so the assertions see the button users get.
        global: { ...localVue, stubs: { ...localVue.stubs, GLink: false } },
    });
}

describe("WorkflowDisplay", () => {
    it("opens a tool step's popover from a named button", async () => {
        const wrapper = mountWithSteps([
            { order_index: 0, type: "data_input" },
            { order_index: 1, type: "tool", tool_id: "cat1", tool_version: "1.0.0" },
        ]);
        await flushPromises();

        const buttons = wrapper.findAll("button[aria-label='Tool details']");
        expect(buttons).toHaveLength(1);
        const button = buttons.at(0);
        expect(button.attributes("type")).toBe("button");
        // The same tool icon as the other step types, so the button is never empty.
        expect(button.findComponent(WorkflowStepIcon).props("stepType")).toBe("tool");
        const popover = wrapper.findComponent(ToolLinkPopover);
        expect(popover.props("target")).toBe(button.attributes("id"));
        expect(popover.props("interactive")).toBe(true);
    });

    it("shows no tool details button for a tool step without a tool", async () => {
        const wrapper = mountWithSteps([{ order_index: 0, type: "tool" }]);
        await flushPromises();

        expect(wrapper.find("[aria-label='Tool details']").exists()).toBe(false);
        expect(wrapper.findComponent(WorkflowStepIcon).props("stepType")).toBe("tool");
    });

    it("localizes the tool step button's accessible name", async () => {
        translations["Tool details"] = "Werkzeugdetails";
        const wrapper = mountWithSteps([{ order_index: 1, type: "tool", tool_id: "cat1", tool_version: "1.0.0" }]);
        await flushPromises();

        expect(wrapper.find("button[aria-label='Werkzeugdetails']").exists()).toBe(true);
    });

    it("gives each instance its own step button ids", async () => {
        const steps = [{ order_index: 1, type: "tool", tool_id: "cat1", tool_version: "1.0.0" }];
        const first = mountWithSteps(steps);
        const second = mountWithSteps(steps);
        await flushPromises();

        const id = (wrapper) => wrapper.find("[aria-label='Tool details']").attributes("id");
        expect(id(first)).toMatch(/-step-1$/);
        expect(id(first)).not.toBe(id(second));
    });

    it("basics", async () => {
        const wrapper = mountDefault();
        await flushPromises();
        const cardHeader = wrapper.find(".card-header");
        expect(cardHeader.text()).toBe("Workflow:workflow_name");
        const downloadUrl = wrapper.find("[data-description='workflow download']");
        expect(downloadUrl.attributes("href")).toBe("/api/workflows/workflow_id/download?format=json-download");
        const importUrl = wrapper.find("[data-description='workflow import']");
        expect(importUrl.attributes("href")).toBe("/workflow/imp?id=workflow_id");
        expect(getRequests.length).toBe(1);
        expect(getRequests[0].url).toContain("/api/workflows/workflow_id/download");
        expect(getRequests[0].url).toContain("style=preview");
    });

    it("renders numbered step titles from preview steps", async () => {
        const wrapper = mountDefault({
            name: "workflow_name",
            steps: [
                { order_index: 0, type: "data_input", label: "Input dataset", inputs: [] },
                {
                    order_index: 1,
                    type: "tool",
                    label: "My cool tool",
                    tool_id: "cat1",
                    tool_version: "1.0",
                    inputs: [],
                },
                { order_index: 2, type: "subworkflow", label: "My subworkflow", inputs: [] },
            ],
        });
        await flushPromises();
        const text = wrapper.text();
        expect(text).toContain("Step 1: Input dataset");
        expect(text).toContain("Step 2: My cool tool");
        expect(text).toContain("Step 3: My subworkflow");
        expect(text).not.toContain("NaN");
    });

    it("error message as object", async () => {
        const wrapper = mountError({
            firstError: "firstValue",
            secondError: "secondValue",
        });
        await flushPromises();
        const errorContent = wrapper.findAll("li");
        expect(errorContent.at(0).text()).toBe("firstError: firstValue");
        expect(errorContent.at(1).text()).toBe("secondError: secondValue");
    });

    it("error message as text", async () => {
        const wrapper = mountError("Something went wrong.");
        await flushPromises();
        const errorContent = wrapper.find(".alert > div");
        expect(errorContent.text()).toBe("Something went wrong.");
    });
});
