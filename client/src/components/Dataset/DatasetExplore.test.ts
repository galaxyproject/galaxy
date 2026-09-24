import { getLocalVue, nth } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { type DatasetInteractiveTool, fetchDatasetInteractiveTools } from "@/api/tools";

import DatasetExplore from "./DatasetExplore.vue";
import DelayedInput from "@/components/Common/DelayedInput.vue";

const mockPush = vi.fn();

vi.mock("vue-router", () => ({
    useRouter: vi.fn(() => ({ push: mockPush })),
}));

vi.mock("@/api/tools", () => ({
    fetchDatasetInteractiveTools: vi.fn(),
}));

const mockFetch = vi.mocked(fetchDatasetInteractiveTools);

const localVue = getLocalVue();

enableAutoUnmount(afterEach);

const DATASET_ID = "dataset_id";

const TOOLS: DatasetInteractiveTool[] = [
    {
        id: "interactive_tool_openrefine",
        name: "OpenRefine",
        description: "Explore and clean tabular data",
        version: "3.8",
        icon: true,
        input_name: "input",
        match: "direct",
    },
    {
        id: "toolshed.g2.bx.psu.edu/repos/iuc/radiant/interactive_tool_radiant/1.0",
        name: "Radiant",
        description: "Business analytics",
        version: "1.0",
        icon: false,
        input_name: "inputs|infile",
        match: "converted",
    },
    {
        id: "interactive_tool_jupyter_notebook",
        name: "Jupyter Notebook",
        description: "General purpose notebook",
        version: "1.0.1",
        icon: false,
        input_name: null,
        match: "generic",
    },
    {
        id: "interactive_tool_ml_jupyter_notebook",
        name: "ML Jupyter",
        description: null,
        version: "1.0",
        icon: false,
        input_name: "input",
        match: "generic",
    },
];

async function mountComponent(
    tools: DatasetInteractiveTool[] = TOOLS,
    datasetExtension: string | undefined = "tabular",
) {
    mockFetch.mockResolvedValue(tools);
    const wrapper = mount(DatasetExplore as object, {
        props: { datasetId: DATASET_ID, datasetExtension },
        // isVisible() reads computed styles, which need the element in the document.
        attachTo: document.body,
        global: {
            ...localVue,
            stubs: {
                DelayedInput: true,
                FontAwesomeIcon: true,
            },
        },
    });
    await flushPromises();
    return wrapper;
}

function row(wrapper: Awaited<ReturnType<typeof mountComponent>>, toolId: string) {
    return wrapper.find(`[data-tool-id='${toolId}']`);
}

async function search(wrapper: Awaited<ReturnType<typeof mountComponent>>, query: string) {
    wrapper.findComponent(DelayedInput).vm.$emit("change", query);
    await flushPromises();
}

describe("DatasetExplore", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("fetches tools for the dataset and lists specific matches", async () => {
        const wrapper = await mountComponent();
        expect(mockFetch).toHaveBeenCalledWith(DATASET_ID);
        const specificRows = wrapper.findAll(".dataset-explore-specific [data-tool-id]");
        expect(specificRows.length).toBe(2);
        expect(nth(specificRows, 0).text()).toContain("OpenRefine");
        expect(nth(specificRows, 0).text()).toContain("Explore and clean tabular data");
        expect(nth(specificRows, 1).text()).toContain("Radiant");
        expect(row(wrapper, "interactive_tool_openrefine").find("img").attributes("src")).toBe(
            "/api/tools/interactive_tool_openrefine/icon",
        );
    });

    it("collapses the general-purpose group until toggled", async () => {
        const wrapper = await mountComponent();
        const toggle = wrapper.find(".dataset-explore-generic-toggle");
        expect(toggle.text()).toContain("General-purpose (2)");
        expect(toggle.attributes("aria-expanded")).toBe("false");
        expect(row(wrapper, "interactive_tool_jupyter_notebook").isVisible()).toBe(false);

        await toggle.trigger("click");
        expect(toggle.attributes("aria-expanded")).toBe("true");
        expect(row(wrapper, "interactive_tool_jupyter_notebook").isVisible()).toBe(true);
        expect(row(wrapper, "interactive_tool_ml_jupyter_notebook").isVisible()).toBe(true);

        await toggle.trigger("click");
        expect(toggle.attributes("aria-expanded")).toBe("false");
    });

    it("shows conversion and no-prefill hints", async () => {
        const wrapper = await mountComponent();
        const direct = row(wrapper, "interactive_tool_openrefine");
        expect(direct.find(".dataset-explore-converted").exists()).toBe(false);
        expect(direct.find(".dataset-explore-no-prefill").exists()).toBe(false);
        const converted = row(wrapper, TOOLS[1]!.id);
        expect(converted.find(".dataset-explore-converted").text()).toBe("via conversion");
        const noPrefill = row(wrapper, "interactive_tool_jupyter_notebook");
        expect(noPrefill.find(".dataset-explore-no-prefill").text()).toBe("select dataset in form");
    });

    it("opens the tool form at the listed version with the dataset preselected", async () => {
        const wrapper = await mountComponent();
        await row(wrapper, "interactive_tool_openrefine").trigger("click");
        expect(mockPush).toHaveBeenCalledWith(`/?tool_id=interactive_tool_openrefine&version=3.8&input=${DATASET_ID}`);

        await row(wrapper, TOOLS[1]!.id).trigger("click");
        expect(mockPush).toHaveBeenLastCalledWith(
            `/?tool_id=${encodeURIComponent(TOOLS[1]!.id)}&version=1.0&inputs%7Cinfile=${DATASET_ID}`,
        );
    });

    it("opens the tool form without preselection when the input cannot be prefilled", async () => {
        const wrapper = await mountComponent();
        await row(wrapper, "interactive_tool_jupyter_notebook").trigger("click");
        expect(mockPush).toHaveBeenCalledWith("/?tool_id=interactive_tool_jupyter_notebook&version=1.0.1");
    });

    it("shows the dataset extension when no tools match", async () => {
        const wrapper = await mountComponent([]);
        expect(wrapper.find(".dataset-explore-empty").text()).toBe(
            "No interactive tools accept 'tabular' on this server.",
        );
        expect(wrapper.findComponent(DelayedInput).exists()).toBe(false);
    });

    it("filters by name and description and expands the general-purpose group", async () => {
        const wrapper = await mountComponent();
        await search(wrapper, "NOTEBOOK");
        expect(wrapper.findAll(".dataset-explore-specific [data-tool-id]").length).toBe(0);
        const toggle = wrapper.find(".dataset-explore-generic-toggle");
        expect(toggle.text()).toContain("General-purpose (1)");
        expect(toggle.attributes("aria-expanded")).toBe("true");
        expect(row(wrapper, "interactive_tool_jupyter_notebook").isVisible()).toBe(true);
        expect(row(wrapper, "interactive_tool_ml_jupyter_notebook").exists()).toBe(false);

        await search(wrapper, "clean tabular");
        expect(row(wrapper, "interactive_tool_openrefine").exists()).toBe(true);
        expect(wrapper.find(".dataset-explore-generic").exists()).toBe(false);

        await search(wrapper, "");
        expect(wrapper.find(".dataset-explore-generic-toggle").attributes("aria-expanded")).toBe("false");
    });

    it("locks the general-purpose group open while searching and restores the user's choice", async () => {
        const wrapper = await mountComponent();
        const toggle = () => wrapper.find(".dataset-explore-generic-toggle");
        await toggle().trigger("click");
        expect(toggle().attributes("aria-disabled")).toBeUndefined();

        await search(wrapper, "notebook");
        expect(toggle().attributes("aria-expanded")).toBe("true");
        expect(toggle().attributes("aria-disabled")).toBe("true");
        await toggle().trigger("click");
        expect(toggle().attributes("aria-expanded")).toBe("true");

        await search(wrapper, "");
        expect(toggle().attributes("aria-disabled")).toBeUndefined();
        expect(toggle().attributes("aria-expanded")).toBe("true");
    });

    it("shows a message when the search has no hits", async () => {
        const wrapper = await mountComponent();
        await search(wrapper, "nothing like this");
        expect(wrapper.find(".dataset-explore-no-match").exists()).toBe(true);
        expect(wrapper.findAll("[data-tool-id]").length).toBe(0);
    });

    it("shows an error when the request fails", async () => {
        mockFetch.mockRejectedValue(new Error("Dataset not accessible"));
        const wrapper = mount(DatasetExplore as object, {
            props: { datasetId: DATASET_ID },
            global: { ...localVue, stubs: { DelayedInput: true, FontAwesomeIcon: true } },
        });
        expect(wrapper.find(".loading-message").exists()).toBe(true);
        await flushPromises();
        expect(wrapper.find(".alert-danger").text()).toBe("Dataset not accessible");
        expect(wrapper.find("[data-tool-id]").exists()).toBe(false);
    });
});
