import { shallowMount, type Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { ComponentOptions } from "vue";

import { getDatatypesMapper } from "@/components/Datatypes";
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
    let wrapper: Wrapper<Vue>;
    const renderD3Tree = vi.fn();

    beforeEach(() => {
        vi.clearAllMocks();
        vi.spyOn((ToolRecommendation as unknown as ComponentOptions<Vue>).methods!, "renderD3Tree").mockImplementation(
            renderD3Tree,
        );
        vi.mocked(getToolPredictions).mockResolvedValue(predictions);
        vi.mocked(getDatatypesMapper).mockResolvedValue({} as Awaited<ReturnType<typeof getDatatypesMapper>>);
        vi.mocked(getCompatibleRecommendations).mockReturnValue(predictions.predicted_data.children);
    });

    afterEach(() => wrapper?.destroy());

    async function mountRecommendation() {
        wrapper = shallowMount(ToolRecommendation as object, {
            propsData: { toolId: "cat1" },
        });
        await flushPromises();
    }

    it("renders compatible recommendations", async () => {
        await mountRecommendation();
        expect(getToolPredictions).toHaveBeenCalledWith({ tool_sequence: "cat1" });
        expect(wrapper.text()).toContain("For further analysis");
        expect(renderD3Tree).toHaveBeenCalledWith({
            name: "cat1",
            o_extensions: ["txt"],
            children: predictions.predicted_data.children,
        });
    });

    it.each(["API authentication required for this request", "Network Error"])(
        "handles prediction failure: %s",
        async (message) => {
            vi.mocked(getToolPredictions).mockRejectedValue(new Error(message));
            await mountRecommendation();
            expect(wrapper.text()).toContain("Tool recommendations could not be loaded");
            expect(wrapper.text()).toContain(message);
            expect(getDatatypesMapper).not.toHaveBeenCalled();
            expect(renderD3Tree).not.toHaveBeenCalled();
        },
    );

    it("handles datatype loading failure", async () => {
        vi.mocked(getDatatypesMapper).mockRejectedValue(new Error("Datatypes unavailable"));
        await mountRecommendation();
        expect(wrapper.text()).toContain("Datatypes unavailable");
        expect(renderD3Tree).not.toHaveBeenCalled();
    });

    it("handles an unconfigured prediction model", async () => {
        vi.mocked(getToolPredictions).mockResolvedValue(null);
        await mountRecommendation();
        expect(getDatatypesMapper).not.toHaveBeenCalled();
        expect(renderD3Tree).not.toHaveBeenCalled();
        expect(wrapper.text()).not.toContain("For further analysis");
    });
});
