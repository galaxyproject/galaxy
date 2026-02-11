import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it, vi } from "vitest";

import type { DataValuePoint } from ".";

import VegaWrapper from "@/components/Common/VegaWrapper.vue";

import BarChart from "./BarChart.vue";

const mockFinalize = vi.fn();
const mockAddSignalListener = vi.fn();
const mockResize = vi.fn(() => ({ runAsync: vi.fn() }));
const mockView = {
    finalize: mockFinalize,
    resize: mockResize,
    addSignalListener: mockAddSignalListener,
};

vi.mock("vega-embed", () => ({
    default: vi.fn(() => Promise.resolve({ view: mockView })),
}));

vi.mock("@vueuse/core", () => ({
    useDebounceFn: (fn: Function) => fn,
    useResizeObserver: vi.fn(),
}));

interface BarChartProps {
    title: string;
    data: DataValuePoint[];
    description?: string;
    enableSelection?: boolean;
    labelFormatter?: (dataPoint?: DataValuePoint | null) => string;
}

const TEST_DATA = [
    { id: "id1", label: "foo", value: 1 },
    { id: "id2", label: "bar", value: 2 },
];

function mountBarChartWrapper(props: BarChartProps) {
    const pinia = createTestingPinia({ createSpy: vi.fn });
    const localVue = getLocalVue();
    return mount(BarChart as object, {
        propsData: props,
        localVue,
        pinia,
    });
}

describe("BarChart.vue", () => {
    describe("Chart Rendering", () => {
        it("should render VegaWrapper when there is data", async () => {
            const wrapper = mountBarChartWrapper({
                title: "Test Bar Chart",
                data: TEST_DATA,
            });
            await flushPromises();
            expect(wrapper.findComponent(VegaWrapper as any).exists()).toBe(true);
        });

        it("should not render VegaWrapper when there is no data", () => {
            const wrapper = mountBarChartWrapper({
                title: "Test Bar Chart",
                data: [],
            });
            expect(wrapper.findComponent(VegaWrapper as any).exists()).toBe(false);
        });

        it("should render with the correct title", () => {
            const title = "Test Bar Chart";
            const wrapper = mountBarChartWrapper({
                title,
                data: TEST_DATA,
            });
            expect(wrapper.find("h4").text()).toBe(title);
        });

        it("should render with the correct description", () => {
            const description = "Test description";
            const wrapper = mountBarChartWrapper({
                title: "Test Bar Chart",
                data: TEST_DATA,
                description,
            });
            expect(wrapper.find(".chart-description").text()).toBe(description);
        });

        it("should display empty state message when there is no data", () => {
            const wrapper = mountBarChartWrapper({
                title: "Test Bar Chart",
                data: [],
            });
            expect(wrapper.text()).toContain("No data to display");
        });

        it("should display empty state when all values are zero", () => {
            const wrapper = mountBarChartWrapper({
                title: "Test Bar Chart",
                data: [
                    { id: "id1", label: "foo", value: 0 },
                    { id: "id2", label: "bar", value: 0 },
                ],
            });
            expect(wrapper.text()).toContain("No data to display");
        });
    });

    describe("Chart Selection", () => {
        it("should not display selection-info initially", () => {
            const wrapper = mountBarChartWrapper({
                title: "Test Bar Chart",
                data: TEST_DATA,
                enableSelection: true,
            });
            expect(wrapper.find(".selection-info").exists()).toBe(false);
        });

        it("should not display selection-info when enableSelection is false", () => {
            const wrapper = mountBarChartWrapper({
                title: "Test Bar Chart",
                data: TEST_DATA,
                enableSelection: false,
            });
            expect(wrapper.find(".selection-info").exists()).toBe(false);
        });
    });
});
