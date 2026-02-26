import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import VegaWrapper from "./VegaWrapper.vue";

const localVue = getLocalVue(true);

const mockFinalize = vi.fn();
const mockView = {
    finalize: mockFinalize,
};

vi.mock("vega-embed", () => ({
    default: vi.fn(() => Promise.resolve({ view: mockView })),
}));

vi.mock("@vueuse/core", () => ({
    useResizeObserver: vi.fn(),
}));

const defaultSpec = {
    mark: "bar",
    encoding: {
        x: { field: "a", type: "nominal" },
        y: { field: "b", type: "quantitative" },
    },
};

describe("VegaWrapper", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("should call vega-embed on mount", async () => {
        const embed = (await import("vega-embed")).default;
        mount(VegaWrapper as object, {
            localVue,
            propsData: { spec: defaultSpec },
        });
        await flushPromises();
        expect(embed).toHaveBeenCalled();
    });

    it("should display error message when embed fails", async () => {
        const embed = (await import("vega-embed")).default;
        (embed as any).mockRejectedValueOnce(new Error("Invalid spec"));

        const wrapper = mount(VegaWrapper as object, {
            localVue,
            propsData: { spec: defaultSpec },
        });
        await flushPromises();

        expect(wrapper.find(".alert-danger").exists()).toBe(true);
        expect(wrapper.text()).toContain("Invalid spec");
    });

    it("should finalize view on unmount", async () => {
        const wrapper = mount(VegaWrapper as object, {
            localVue,
            propsData: { spec: defaultSpec },
        });
        await flushPromises();
        wrapper.destroy();

        expect(mockFinalize).toHaveBeenCalled();
    });

    it("should re-embed chart when props change", async () => {
        const embed = (await import("vega-embed")).default;
        const wrapper = mount(VegaWrapper as object, {
            localVue,
            propsData: { spec: defaultSpec },
        });
        await flushPromises();

        const initialCallCount = (embed as any).mock.calls.length;

        await wrapper.setProps({ spec: { mark: "line" } });
        await flushPromises();

        expect((embed as any).mock.calls.length).toBeGreaterThan(initialCallCount);
    });
});
