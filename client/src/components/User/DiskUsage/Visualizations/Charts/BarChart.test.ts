import { composeStories } from "@storybook/vue3-vite";
import { nth } from "@tests/vitest/helpers";
import { type StoryOf, useStoryMount } from "@tests/vitest/stories";
import type * as VueUse from "@vueuse/core";
import flushPromises from "flush-promises";
import { disposePinia, getActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, onTestFinished, vi } from "vitest";

import type { DataValuePoint } from ".";
import * as BarChartStories from "./BarChart.stories";

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
        if (!colorMap[d.id]) {
            colorMap[d.id] = nth(colors, i % colors.length);
        }
    });
    return {
        finalize: mockFinalize,
        resize: mockResize,
        addSignalListener: mockAddSignalListener,
        runAsync: mockRunAsync,
        scale: vi.fn(() => (value: string) => colorMap[value] ?? "#000"),
        data: vi.fn((name: string, newData?: unknown[]) => {
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

vi.mock("@vueuse/core", async (importOriginal) => ({
    ...(await importOriginal<typeof VueUse>()),
    useResizeObserver: vi.fn(),
}));

type BarChartProps = InstanceType<typeof BarChart>["$props"];

const stories = composeStories(BarChartStories);
const mountStory = useStoryMount();
// Finish the mock embed while mounted so VegaWrapper owns and finalizes its view.
afterEach(async () => {
    await flushPromises();
});

function mountBarChartWrapper(props: BarChartProps, story: StoryOf<typeof stories> = stories.DatasetCounts) {
    const wrapper = mountStory(story, { props, pinia: { stubActions: true } }).getComponent(BarChart);
    const pinia = getActivePinia();
    onTestFinished(() => pinia && disposePinia(pinia));
    return wrapper;
}

beforeEach(() => {
    vi.clearAllMocks();
    currentMockView = buildMockView();
});

describe("BarChart.vue", () => {
    describe("Chart Rendering", () => {
        it("should render VegaWrapper when there is data", async () => {
            currentMockView = buildMockView(TEST_DATA);
            const wrapper = mountBarChartWrapper({
                title: "Test Bar Chart",
                data: TEST_DATA,
            });
            await flushPromises();
            expect(wrapper.findComponent(VegaWrapper).exists()).toBe(true);
        });

        it("should not render VegaWrapper when there is no data", () => {
            const wrapper = mountBarChartWrapper(
                {
                    title: "Test Bar Chart",
                    data: [],
                },
                stories.NoHistories,
            );
            expect(wrapper.text()).toContain("No data to display. Populate some data and come back.");
            expect(wrapper.findComponent(VegaWrapper).exists()).toBe(false);
        });
    });

    describe("Legend", () => {
        it("should render legend symbols with correct colors", async () => {
            currentMockView = buildMockView(TEST_DATA);
            const wrapper = mountBarChartWrapper({
                title: "Test Bar Chart",
                data: TEST_DATA,
            });
            await flushPromises();
            const vegaWrapper = wrapper.getComponent(VegaWrapper);
            vegaWrapper.vm.$emit("new-view", currentMockView);
            await flushPromises();
            const symbols = wrapper.findAll(".legend-symbol");
            expect(symbols.length).toBe(2);
            expect(nth(symbols, 0).attributes("style")).toContain("background-color");
            expect(nth(symbols, 1).attributes("style")).toContain("background-color");
            expect((nth(symbols, 0).element as HTMLElement).style.backgroundColor).toBe("#4c78a8");
            expect((nth(symbols, 1).element as HTMLElement).style.backgroundColor).toBe("#f58518");
        });

        it("should not render legend when there is no data", () => {
            const wrapper = mountBarChartWrapper(
                {
                    title: "Test Bar Chart",
                    data: [],
                },
                stories.NoHistories,
            );
            expect(wrapper.text()).toContain("No data to display. Populate some data and come back.");
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
            const vegaWrapper = wrapper.getComponent(VegaWrapper);
            vegaWrapper.vm.$emit("new-view", currentMockView);
            await flushPromises();
            const item = wrapper.get(".legend-item");
            expect(item.attributes("style")).toContain("cursor: default");
        });

        it("should use pointer cursor when selection is enabled", async () => {
            currentMockView = buildMockView(TEST_DATA);
            const wrapper = mountBarChartWrapper(
                {
                    title: "Test Bar Chart",
                    data: TEST_DATA,
                    enableSelection: true,
                },
                stories.SelectableHistories,
            );
            await flushPromises();
            const vegaWrapper = wrapper.getComponent(VegaWrapper);
            vegaWrapper.vm.$emit("new-view", currentMockView);
            await flushPromises();
            const item = wrapper.get(".legend-item");
            expect(item.attributes("style")).toContain("cursor: pointer");
        });

        it("should dim unselected legend items on click", async () => {
            currentMockView = buildMockView(TEST_DATA);
            const wrapper = mountBarChartWrapper(
                {
                    title: "Test Bar Chart",
                    data: TEST_DATA,
                    enableSelection: true,
                },
                stories.SelectableHistories,
            );
            await flushPromises();
            const vegaWrapper = wrapper.getComponent(VegaWrapper);
            vegaWrapper.vm.$emit("new-view", currentMockView);
            await flushPromises();
            const items = wrapper.findAll(".legend-item");
            expect(nth(items, 0).classes()).not.toContain("legend-item-dimmed");
            expect(nth(items, 1).classes()).not.toContain("legend-item-dimmed");
            await nth(items, 0).trigger("click");
            await flushPromises();
            expect(nth(items, 0).classes()).not.toContain("legend-item-dimmed");
            expect(nth(items, 1).classes()).toContain("legend-item-dimmed");
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
            const vegaWrapper = wrapper.getComponent(VegaWrapper);
            vegaWrapper.vm.$emit("new-view", currentMockView);
            await flushPromises();
            const item = wrapper.get(".legend-item");
            expect(item.text()).toBe("foo: 1");
            await item.trigger("click");
            expect(mockRunAsync).not.toHaveBeenCalled();
        });
    });

    describe("Chart Selection", () => {
        it("should not display selection-info initially", () => {
            const wrapper = mountBarChartWrapper(
                {
                    title: "Test Bar Chart",
                    data: TEST_DATA,
                    enableSelection: true,
                },
                stories.SelectableHistories,
            );
            expect(wrapper.get("h4").text()).toBe("Test Bar Chart");
            expect(wrapper.find(".selection-info").exists()).toBe(false);
        });

        it("should not display selection-info when enableSelection is false", () => {
            const wrapper = mountBarChartWrapper({
                title: "Test Bar Chart",
                data: TEST_DATA,
                enableSelection: false,
            });
            expect(wrapper.get("h4").text()).toBe("Test Bar Chart");
            expect(wrapper.find(".selection-info").exists()).toBe(false);
        });
    });
});
