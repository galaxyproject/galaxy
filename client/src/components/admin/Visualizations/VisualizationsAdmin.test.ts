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
    });

    it("refreshes the installed list after an update, even one that fails", async () => {
        const wrapper = mountAdmin();
        await flushPromises();
        vi.mocked(services.getInstalledVisualizations).mockClear();

        vi.mocked(services.updateVisualization).mockRejectedValue(new Error("missing static config"));

        wrapper.findComponent(VisualizationCard).vm.$emit("update", NORA, "1.2.4");
        await flushPromises();

        expect(services.getInstalledVisualizations).toHaveBeenCalled();
    });
});
