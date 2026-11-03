import { getLocalVue, nth } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { type DatatypeConverter, fetchDatatypeConverters } from "@/api/datatypes";
import { getDatatypesMapper } from "@/components/Datatypes";
import { DatatypesMapperModel } from "@/components/Datatypes/model";
import { useDatatypesMapperStore } from "@/stores/datatypesMapperStore";
import { type Tool, type ToolDataInput, useToolStore } from "@/stores/toolStore";

import DatasetExplore from "./DatasetExplore.vue";
import DelayedInput from "@/components/Common/DelayedInput.vue";

const mockPush = vi.fn();

vi.mock("vue-router", () => ({
    useRouter: vi.fn(() => ({ push: mockPush })),
}));

vi.mock("@/api/datatypes", () => ({
    fetchDatatypeConverters: vi.fn(),
}));

vi.mock("@/components/Datatypes", () => ({
    getDatatypesMapper: vi.fn(),
}));

const mockFetchConverters = vi.mocked(fetchDatatypeConverters);
const mockGetDatatypesMapper = vi.mocked(getDatatypesMapper);

enableAutoUnmount(afterEach);

const DATASET_ID = "dataset_id";

const RADIANT_ID = "toolshed.g2.bx.psu.edu/repos/iuc/radiant/interactive_tool_radiant";

const mapper = new DatatypesMapperModel({
    datatypes: ["bam", "csv", "tabular"],
    datatypes_mapping: {
        ext_to_class_name: {
            bam: "galaxy.datatypes.binary.Bam",
            csv: "galaxy.datatypes.tabular.CSV",
            tabular: "galaxy.datatypes.tabular.Tabular",
        },
        class_to_classes: {
            "galaxy.datatypes.binary.Bam": { "galaxy.datatypes.binary.Bam": true, "galaxy.datatypes.data.Data": true },
            "galaxy.datatypes.tabular.CSV": {
                "galaxy.datatypes.tabular.CSV": true,
                "galaxy.datatypes.data.Data": true,
            },
            "galaxy.datatypes.tabular.Tabular": {
                "galaxy.datatypes.tabular.Tabular": true,
                "galaxy.datatypes.data.Data": true,
            },
        },
    },
});

const CONVERTERS: DatatypeConverter[] = [{ source: "tabular", target: "csv", tool_id: "CONVERTER_tabular_to_csv" }];

function interactiveTool(
    id: string,
    name: string,
    version: string,
    dataInputs: ToolDataInput[],
    extra: Partial<Tool> = {},
): Tool {
    return {
        model_class: "InteractiveTool",
        id,
        name,
        version,
        description: "",
        data_inputs: dataInputs,
        ...extra,
    } as Tool;
}

function dataInput(name: string | null, extensions: string[]): ToolDataInput {
    return { name, extensions, multiple: false };
}

const IGV_TOOL = interactiveTool("interactive_tool_igv", "IGV", "1.0", [dataInput("input", ["bam"])]);

const TOOLS: Tool[] = [
    interactiveTool("interactive_tool_openrefine", "OpenRefine", "3.8", [dataInput("input", ["tabular"])], {
        description: "Explore and clean tabular data",
        icon: "openrefine.png",
    }),
    interactiveTool(`${RADIANT_ID}/1.0`, "Radiant", "1.0", [dataInput("inputs|infile", ["csv"])], {
        description: "Business analytics",
    }),
    interactiveTool(`${RADIANT_ID}/0.9`, "Radiant", "0.9", [dataInput("infile", ["csv"])]),
    interactiveTool("interactive_tool_jupyter_notebook", "Jupyter Notebook", "1.0.1", [dataInput(null, ["data"])], {
        description: "General purpose notebook",
    }),
    interactiveTool("interactive_tool_ml_jupyter_notebook", "ML Jupyter", "1.0", [dataInput("input", ["data"])]),
    IGV_TOOL,
    { ...interactiveTool("cat1", "Concatenate", "1.0", [dataInput("input1", ["data"])]), model_class: "Tool" },
];

/** Mount options whose pinia already holds the tools and the datatypes mapper. */
function setupStores(tools: Tool[]) {
    const localVue = getLocalVue();
    // A loaded tool list keeps fetchTools off the network.
    useToolStore().saveAllTools(tools);
    useDatatypesMapperStore().datatypesMapper = mapper;
    return localVue;
}

async function mountComponent(tools: Tool[] = TOOLS) {
    const localVue = setupStores(tools);
    mockFetchConverters.mockResolvedValue(CONVERTERS);
    const wrapper = mount(DatasetExplore as object, {
        props: { datasetId: DATASET_ID, datasetExtension: "tabular" },
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

    it("lists the latest version of each interactive tool that accepts the dataset", async () => {
        const wrapper = await mountComponent();
        const specificRows = wrapper.findAll(".dataset-explore-specific [data-tool-id]");
        expect(specificRows.length).toBe(2);
        expect(nth(specificRows, 0).text()).toContain("OpenRefine");
        expect(nth(specificRows, 0).text()).toContain("Explore and clean tabular data");
        expect(nth(specificRows, 1).text()).toContain("Radiant");
        expect(row(wrapper, `${RADIANT_ID}/0.9`).exists()).toBe(false);
        expect(row(wrapper, "interactive_tool_igv").exists()).toBe(false);
        expect(row(wrapper, "cat1").exists()).toBe(false);
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
        const converted = row(wrapper, `${RADIANT_ID}/1.0`);
        expect(converted.find(".dataset-explore-converted").text()).toBe("via conversion");
        const noPrefill = row(wrapper, "interactive_tool_jupyter_notebook");
        expect(noPrefill.find(".dataset-explore-no-prefill").text()).toBe("select dataset in form");
    });

    it("opens the tool form at the listed version with the dataset preselected", async () => {
        const wrapper = await mountComponent();
        await row(wrapper, "interactive_tool_openrefine").trigger("click");
        expect(mockPush).toHaveBeenCalledWith(`/?tool_id=interactive_tool_openrefine&version=3.8&input=${DATASET_ID}`);

        await row(wrapper, `${RADIANT_ID}/1.0`).trigger("click");
        expect(mockPush).toHaveBeenLastCalledWith(
            `/?tool_id=${encodeURIComponent(`${RADIANT_ID}/1.0`)}&version=1.0&inputs%7Cinfile=${DATASET_ID}`,
        );
    });

    it("opens the tool form without preselection when the input cannot be prefilled", async () => {
        const wrapper = await mountComponent();
        await row(wrapper, "interactive_tool_jupyter_notebook").trigger("click");
        expect(mockPush).toHaveBeenCalledWith("/?tool_id=interactive_tool_jupyter_notebook&version=1.0.1");
    });

    it("shows the dataset extension when no tools match", async () => {
        const wrapper = await mountComponent([IGV_TOOL]);
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

    it("shows an error when loading fails", async () => {
        const localVue = setupStores(TOOLS);
        mockFetchConverters.mockRejectedValue(new Error("Converters unavailable"));
        const wrapper = mount(DatasetExplore as object, {
            props: { datasetId: DATASET_ID, datasetExtension: "tabular" },
            global: { ...localVue, stubs: { DelayedInput: true, FontAwesomeIcon: true } },
        });
        expect(wrapper.find(".loading-message").exists()).toBe(true);
        await flushPromises();
        expect(wrapper.find(".alert-danger").text()).toBe("Converters unavailable");
        expect(wrapper.find("[data-tool-id]").exists()).toBe(false);
    });

    it("shows an error when a datatypes load started elsewhere fails", async () => {
        const localVue = setupStores(TOOLS);
        mockFetchConverters.mockResolvedValue(CONVERTERS);
        mockGetDatatypesMapper.mockRejectedValue(new Error("Datatypes unavailable"));
        const datatypesMapperStore = useDatatypesMapperStore();
        datatypesMapperStore.datatypesMapper = null;
        const otherLoad = datatypesMapperStore.createMapper().catch(() => undefined);
        const wrapper = mount(DatasetExplore as object, {
            props: { datasetId: DATASET_ID, datasetExtension: "tabular" },
            global: { ...localVue, stubs: { DelayedInput: true, FontAwesomeIcon: true } },
        });
        await otherLoad;
        await flushPromises();
        expect(wrapper.find(".loading-message").exists()).toBe(false);
        expect(wrapper.find(".alert-danger").text()).toBe("Datatypes unavailable");
    });
});
