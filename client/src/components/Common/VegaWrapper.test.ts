import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { useResizeObserver } from "@vueuse/core";
import flushPromises from "flush-promises";
import embed, { type VisualizationSpec } from "vega-embed";
import { beforeEach, describe, expect, it, vi } from "vitest";

import VegaWrapper, { type VisSpec } from "./VegaWrapper.vue";

const { mockView, mockRunAsync } = vi.hoisted(() => {
    const mockRunAsync = vi.fn();
    return {
        mockRunAsync,
        mockView: {
            finalize: vi.fn(),
            width: vi.fn(() => ({ runAsync: mockRunAsync })),
        },
    };
});

vi.mock("vega-embed", () => ({
    default: vi.fn(() => Promise.resolve({ view: mockView })),
}));

vi.mock("@vueuse/core", () => ({
    useResizeObserver: vi.fn(),
}));

const mockEmbed = vi.mocked(embed);

const localVue = getLocalVue(true);

const BAR_SPEC: VisualizationSpec = {
    data: { values: [] },
    mark: "bar",
    encoding: {
        x: { field: "a", type: "nominal" },
        y: { field: "b", type: "quantitative" },
    },
};

const LINE_SPEC: VisualizationSpec = { data: { values: [] }, mark: "line" };

async function mountVegaWrapper(props: Partial<VisSpec> = {}) {
    const wrapper = mount(VegaWrapper, {
        global: localVue,
        props: { spec: BAR_SPEC, ...props },
    });
    await flushPromises();
    return wrapper;
}

type VegaWrapperWrapper = Awaited<ReturnType<typeof mountVegaWrapper>>;

function chartContainer(wrapper: VegaWrapperWrapper) {
    return wrapper.element.lastElementChild;
}

function resizeContainer(wrapper: VegaWrapperWrapper, clientWidth: number) {
    Object.defineProperty(wrapper.element, "clientWidth", { value: clientWidth });
    const onResize = vi.mocked(useResizeObserver).mock.calls[0]?.[1];
    if (!onResize) {
        throw new Error("VegaWrapper did not observe its container's size");
    }
    onResize([], {} as ResizeObserver);
}

describe("VegaWrapper", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("embeds the spec as SVG into the chart container on mount and emits the new view", async () => {
        const wrapper = await mountVegaWrapper();

        expect(mockEmbed).toHaveBeenCalledTimes(1);
        expect(mockEmbed).toHaveBeenCalledWith(chartContainer(wrapper), BAR_SPEC, { renderer: "svg" });
        expect(wrapper.emitted("new-view")).toEqual([[mockView]]);
    });

    it("shows the embed error in a danger alert", async () => {
        mockEmbed.mockRejectedValueOnce(new Error("Invalid spec"));

        const wrapper = await mountVegaWrapper();

        expect(wrapper.find(".alert-danger").text()).toBe("Error: Invalid spec");
    });

    it("finalizes the view on unmount", async () => {
        const wrapper = await mountVegaWrapper();

        wrapper.unmount();

        expect(mockView.finalize).toHaveBeenCalledTimes(1);
    });

    it("finalizes the old view and embeds the new spec when the spec changes", async () => {
        const wrapper = await mountVegaWrapper();

        await wrapper.setProps({ spec: LINE_SPEC });
        await flushPromises();

        expect(mockView.finalize).toHaveBeenCalledTimes(1);
        expect(mockEmbed).toHaveBeenCalledTimes(2);
        expect(mockEmbed).toHaveBeenLastCalledWith(chartContainer(wrapper), LINE_SPEC, { renderer: "svg" });
    });

    it("resizes the view to the container width when the container resizes", async () => {
        const wrapper = await mountVegaWrapper();

        resizeContainer(wrapper, 640);

        expect(mockView.width).toHaveBeenCalledWith(640);
        expect(mockRunAsync).toHaveBeenCalledTimes(1);
    });

    it("keeps the view's width on container resize when fillWidth is off", async () => {
        const wrapper = await mountVegaWrapper({ fillWidth: false });

        resizeContainer(wrapper, 640);

        expect(mockView.width).not.toHaveBeenCalled();
    });
});
