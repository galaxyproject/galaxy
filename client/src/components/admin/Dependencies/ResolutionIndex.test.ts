import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it, vi } from "vitest";

import { getToolboxDependencies } from "../AdminServices";

import ResolutionIndex from "./ResolutionIndex.vue";

vi.mock("../AdminServices", () => ({
    getToolboxDependencies: vi.fn(),
    installDependencies: vi.fn(),
    uninstallDependencies: vi.fn(),
}));

const localVue = getLocalVue();

const REQUIREMENTS = [{ requirements: [{ name: "bwa", version: "0.7" }], status: [], tool_ids: ["bwa_tool"] }];

async function mountIndex(requirements: object[]) {
    vi.mocked(getToolboxDependencies).mockResolvedValue(requirements);
    const wrapper = mount(ResolutionIndex as object, {
        localVue,
        stubs: { ResolutionDetails: true },
    });
    await flushPromises();
    return wrapper;
}

function headerBox(wrapper: Awaited<ReturnType<typeof mountIndex>>) {
    return wrapper.find("#requirements-table thead input[type='checkbox']").element as HTMLInputElement;
}

describe("ResolutionIndex", () => {
    it("disables the header select-all box while there are no requirements", async () => {
        const wrapper = await mountIndex([]);
        expect(headerBox(wrapper).disabled).toBe(true);
    });

    it("enables the header select-all box once there are requirements", async () => {
        const wrapper = await mountIndex(REQUIREMENTS);
        expect(headerBox(wrapper).disabled).toBe(false);
    });
});
