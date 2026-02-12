import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import VegaWrapper from "./VegaWrapper.vue";

const localVue = getLocalVue(true);

const mockFinalize = vi.fn();
const mockResize = vi.fn(() => ({ runAsync: vi.fn() }));
const mockView = {
    finalize: mockFinalize,
    resize: mockResize,
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

    describe("Rendering", () => {
        it("renders chart container", () => {
            const wrapper = mount(VegaWrapper as object, {
                localVue,
                propsData: { spec: defaultSpec },
            });
            expect(wrapper.find("div").exists()).toBe(true);
        });

        it("calls vega-embed on mount", async () => {
            const embed = (await import("vega-embed")).default;
            mount(VegaWrapper as object, {
                localVue,
                propsData: { spec: defaultSpec },
            });
            await flushPromises();
            expect(embed).toHaveBeenCalled();
        });
    });

    describe("Error handling", () => {
        it("displays error message when embed fails", async () => {
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

        it("hides error message on successful render", async () => {
            const wrapper = mount(VegaWrapper as object, {
                localVue,
                propsData: { spec: defaultSpec },
            });
            await flushPromises();

            expect(wrapper.find(".alert-danger").exists()).toBe(false);
        });
    });

    describe("Lifecycle", () => {
        it("finalizes view on unmount", async () => {
            const wrapper = mount(VegaWrapper as object, {
                localVue,
                propsData: { spec: defaultSpec },
            });
            await flushPromises();
            wrapper.destroy();

            expect(mockFinalize).toHaveBeenCalled();
        });

        it("re-embeds chart when props change", async () => {
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

    describe("Props", () => {
        it("defaults fillWidth to true", () => {
            const wrapper = mount(VegaWrapper as object, {
                localVue,
                propsData: { spec: defaultSpec },
            });
            expect(wrapper.props("fillWidth")).toBe(true);
        });

        it("applies w-100 class when fillWidth is true", () => {
            const wrapper = mount(VegaWrapper as object, {
                localVue,
                propsData: { spec: defaultSpec, fillWidth: true },
            });
            expect(wrapper.find(".w-100").exists()).toBe(true);
        });

        it("does not apply w-100 class when fillWidth is false", () => {
            const wrapper = mount(VegaWrapper as object, {
                localVue,
                propsData: { spec: defaultSpec, fillWidth: false },
            });
            expect(wrapper.find(".w-100").exists()).toBe(false);
        });
    });

    describe("Resize observer", () => {
        it("registers resize observer on mount", async () => {
            const { useResizeObserver } = await import("@vueuse/core");
            mount(VegaWrapper as object, {
                localVue,
                propsData: { spec: defaultSpec },
            });
            expect(useResizeObserver).toHaveBeenCalled();
        });
    });
});
