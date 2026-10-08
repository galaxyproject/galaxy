import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as services from "./services";

import VisualizationCard from "./VisualizationCard.vue";
import VisualizationsAdmin from "./VisualizationsAdmin.vue";

vi.mock("./services");
vi.mock("@/composables/toast", () => ({ useToast: () => ({ success: vi.fn(), error: vi.fn() }) }));
vi.mock("@/composables/confirmDialog", () => ({ useConfirmDialog: () => ({ confirm: vi.fn() }) }));

const localVue = getLocalVue();

const NORA = {
    id: "nora",
    package: "@galaxyproject/nora",
    version: "1.2.3",
    enabled: true,
    installed: true,
    message: "",
};

function mountAdmin() {
    return mount(VisualizationsAdmin, { global: localVue });
}

describe("VisualizationsAdmin", () => {
    beforeEach(() => {
        vi.mocked(services.getInstalledVisualizations).mockResolvedValue([NORA] as never);
        vi.mocked(services.getStagingStatus).mockResolvedValue({
            message: "",
            staged_count: 0,
            staged_visualizations: [],
            total_size: 0,
        } as never);
    });

    it("refreshes the installed list when staging fails after a successful update", async () => {
        const wrapper = mountAdmin();
        await flushPromises();
        vi.mocked(services.getInstalledVisualizations).mockClear();
        vi.mocked(services.getStagingStatus).mockClear();

        vi.mocked(services.updateVisualization).mockResolvedValue({} as never);
        vi.mocked(services.stageVisualization).mockRejectedValue(new Error("missing static config"));

        wrapper.findComponent(VisualizationCard).vm.$emit("update", NORA, "1.2.4");
        await flushPromises();

        // the update itself went through, so the list and staging status must reflect it
        expect(services.getInstalledVisualizations).toHaveBeenCalled();
        expect(services.getStagingStatus).toHaveBeenCalled();
    });
});
