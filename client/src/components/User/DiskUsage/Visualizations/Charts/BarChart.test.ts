import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it, vi } from "vitest";

import type { DataValuePoint } from ".";

import BarChart from "./BarChart.vue";
import VegaWrapper from "@/components/Common/VegaWrapper.vue";

const mockFinalize = vi.fn();
const mockAddSignalListener = vi.fn();
const mockResize = vi.fn(() => ({ runAsync: vi.fn() }));
const mockRunAsync = vi.fn();

const TEST_DATA = [
    { id: "id1", label: "foo", value: 1 },
    { id: "id2", label: "bar", value: 2 },
];

function buildMockView(dataPoints: DataValuePoint[] = []) {
    const formattedData = dataPoints.map((d) => ({
        ...d,
        formattedValue: `${d.label}: ${d.value}`,
    }));
    const colorMap: Record<string, string> = {};
    const colors = ["#4c78a8", "#f58518", "#e45756", "#72b7b2"];
    formattedData.forEach((d, i) => {
        if (!colorMap[d.formattedValue]) {
            colorMap[d.formattedValue] = colors[i % colors.length]!;
        }
    });
    return {
        finalize: mockFinalize,
        resize: mockResize,
        addSignalListener: mockAddSignalListener,
        runAsync: mockRunAsync,
        scale: vi.fn(() => (value: string) => colorMap[value] ?? "#000"),
        data: vi.fn((name: string, newData?: any[]) => {
            if (name === "data_0") {
                return formattedData;
            }
            if (name === "barSelection_store") {
                return newData ?? [];
            }
            return [];
        }),
    };
}

let currentMockView = buildMockView();

vi.mock("vega-embed", () => ({
    default: vi.fn(() => Promise.resolve({ view: currentMockView })),
}));

vi.mock("@vueuse/core", () => ({
    useResizeObserver: vi.fn(),
}));

interface BarChartProps {
    title: string;
    data: DataValuePoint[];
    description?: string;
    enableSelection?: boolean;
    labelFormatter?: (dataPoint?: DataValuePoint | null) => string;
}

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
            currentMockView = buildMockView(TEST_DATA);
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
            const wrapper = mountBarChartWrapper({
                title: "Test Bar Chart",
                data: TEST_DATA,
            });
            expect(wrapper.find("h4").text()).toBe("Test Bar Chart");
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

    describe("Legend", () => {
        it("should render legend items after view is created", async () => {
            currentMockView = buildMockView(TEST_DATA);
            const wrapper = mountBarChartWrapper({
                title: "Test Bar Chart",
                data: TEST_DATA,
            });
            await flushPromises();
            const vegaWrapper = wrapper.findComponent(VegaWrapper as any);
            vegaWrapper.vm.$emit("new-view", currentMockView);
            await flushPromises();
            const items = wrapper.findAll(".legend-item");
            expect(items.length).toBe(2);
            expect(items.at(0).text()).toBe("foo: 1");
            expect(items.at(1).text()).toBe("bar: 2");
        });

        it("should render legend symbols with correct colors", async () => {
            currentMockView = buildMockView(TEST_DATA);
            const wrapper = mountBarChartWrapper({
                title: "Test Bar Chart",
                data: TEST_DATA,
            });
            await flushPromises();
            const vegaWrapper = wrapper.findComponent(VegaWrapper as any);
            vegaWrapper.vm.$emit("new-view", currentMockView);
            await flushPromises();
            const symbols = wrapper.findAll(".legend-symbol");
            expect(symbols.length).toBe(2);
            expect(symbols.at(0).attributes("style")).toContain("background-color");
            expect(symbols.at(1).attributes("style")).toContain("background-color");
        });

        it("should not render legend when there is no data", () => {
            const wrapper = mountBarChartWrapper({
                title: "Test Bar Chart",
                data: [],
            });
            expect(wrapper.find(".legend-container").exists()).toBe(false);
        });

        it("should use default cursor when selection is disabled", async () => {
            currentMockView = buildMockView(TEST_DATA);
            const wrapper = mountBarChartWrapper({
                title: "Test Bar Chart",
                data: TEST_DATA,
                enableSelection: false,
            });
            await flushPromises();
            const vegaWrapper = wrapper.findComponent(VegaWrapper as any);
            vegaWrapper.vm.$emit("new-view", currentMockView);
            await flushPromises();
            const item = wrapper.find(".legend-item");
            expect(item.attributes("style")).toContain("cursor: default");
        });

        it("should use pointer cursor when selection is enabled", async () => {
            currentMockView = buildMockView(TEST_DATA);
            const wrapper = mountBarChartWrapper({
                title: "Test Bar Chart",
                data: TEST_DATA,
                enableSelection: true,
            });
            await flushPromises();
            const vegaWrapper = wrapper.findComponent(VegaWrapper as any);
            vegaWrapper.vm.$emit("new-view", currentMockView);
            await flushPromises();
            const item = wrapper.find(".legend-item");
            expect(item.attributes("style")).toContain("cursor: pointer");
        });

        it("should dim unselected legend items on click", async () => {
            currentMockView = buildMockView(TEST_DATA);
            const wrapper = mountBarChartWrapper({
                title: "Test Bar Chart",
                data: TEST_DATA,
                enableSelection: true,
            });
            await flushPromises();
            const vegaWrapper = wrapper.findComponent(VegaWrapper as any);
            vegaWrapper.vm.$emit("new-view", currentMockView);
            await flushPromises();
            const items = wrapper.findAll(".legend-item");
            await items.at(0).trigger("click");
            await flushPromises();
            expect(items.at(0).classes()).not.toContain("legend-item-dimmed");
            expect(items.at(1).classes()).toContain("legend-item-dimmed");
        });

        it("should not trigger selection on click when selection is disabled", async () => {
            currentMockView = buildMockView(TEST_DATA);
            mockRunAsync.mockClear();
            const wrapper = mountBarChartWrapper({
                title: "Test Bar Chart",
                data: TEST_DATA,
                enableSelection: false,
            });
            await flushPromises();
            const vegaWrapper = wrapper.findComponent(VegaWrapper as any);
            vegaWrapper.vm.$emit("new-view", currentMockView);
            await flushPromises();
            const item = wrapper.find(".legend-item");
            await item.trigger("click");
            expect(mockRunAsync).not.toHaveBeenCalled();
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
