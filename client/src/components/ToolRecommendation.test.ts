import { getLocalVue } from "@tests/vitest/helpers";
import { enableAutoUnmount, shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { getDatatypesMapper } from "@/components/Datatypes";
import { DatatypesMapperModel } from "@/components/Datatypes/model";
import { getToolPredictions } from "@/components/Workflow/Editor/modules/services";
import { getCompatibleRecommendations } from "@/components/Workflow/Editor/modules/utilities";

import ToolRecommendation from "./ToolRecommendation.vue";

vi.mock("@/components/Datatypes", () => ({ getDatatypesMapper: vi.fn() }));
vi.mock("@/components/Workflow/Editor/modules/services", () => ({ getToolPredictions: vi.fn() }));
vi.mock("@/components/Workflow/Editor/modules/utilities", () => ({ getCompatibleRecommendations: vi.fn() }));

const predictions = {
    predicted_data: {
        name: "cat1",
        is_deprecated: false,
        message: "",
        o_extensions: ["txt"],
        children: [{ name: "Cut", id: "cut1" }],
    },
};

describe("ToolRecommendation", () => {
    enableAutoUnmount(afterEach);

    beforeEach(() => {
        vi.clearAllMocks();
        vi.mocked(getToolPredictions).mockResolvedValue(predictions);
        vi.mocked(getDatatypesMapper).mockResolvedValue(
            new DatatypesMapperModel({
                datatypes: [],
                datatypes_mapping: { ext_to_class_name: {}, class_to_classes: {} },
            }),
        );
        vi.mocked(getCompatibleRecommendations).mockReturnValue(predictions.predicted_data.children);
    });

    async function mountRecommendation() {
        const wrapper = shallowMount(ToolRecommendation, {
            props: { toolId: "cat1" },
            global: getLocalVue(),
        });
        await flushPromises();
        return wrapper;
    }

    it("renders compatible recommendations", async () => {
        const wrapper = await mountRecommendation();
        expect(getToolPredictions).toHaveBeenCalledWith({ tool_sequence: "cat1" });
        expect(wrapper.text()).toContain("For further analysis");
        // root node ("cat1") plus one child node ("Cut") rendered by d3
        expect(wrapper.findAll("g.node")).toHaveLength(2);
        expect(wrapper.text()).toContain("Cut");
    });

    it.each(["API authentication required for this request", "Network Error"])(
        "handles prediction failure: %s",
        async (message) => {
            vi.mocked(getToolPredictions).mockRejectedValue(new Error(message));
            const wrapper = await mountRecommendation();
            expect(wrapper.text()).toContain("Tool recommendations could not be loaded");
            expect(wrapper.text()).toContain(message);
            expect(getDatatypesMapper).not.toHaveBeenCalled();
            expect(wrapper.findAll("g.node")).toHaveLength(0);
        },
    );

    it("handles datatype loading failure", async () => {
        vi.mocked(getDatatypesMapper).mockRejectedValue(new Error("Datatypes unavailable"));
        const wrapper = await mountRecommendation();
        expect(wrapper.text()).toContain("Datatypes unavailable");
        expect(wrapper.findAll("g.node")).toHaveLength(0);
    });

    it("handles an unconfigured prediction model", async () => {
        vi.mocked(getToolPredictions).mockResolvedValue(null);
        const wrapper = await mountRecommendation();
        expect(getDatatypesMapper).not.toHaveBeenCalled();
        expect(wrapper.findAll("g.node")).toHaveLength(0);
        expect(wrapper.text()).not.toContain("For further analysis");
    });
});
