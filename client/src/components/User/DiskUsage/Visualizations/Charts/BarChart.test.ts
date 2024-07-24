import { mount } from "@vue/test-utils";

import { type DataValuePoint } from ".";

import BarChart from "./BarChart.vue";

// Duplicated interface from BarChart.vue because of https://github.com/vuejs/core/issues/4294
interface BarChartProps {
    title: string;
    data: DataValuePoint[];
    description?: string;
    width?: number;
    height?: number;
    enableTooltips?: boolean;
    enableSelection?: boolean;
    labelFormatter?: (dataPoint?: DataValuePoint | null) => string;
}

const TEST_DATA = [
    { id: "id1", label: "foo", value: 1 },
    { id: "id2", label: "bar", value: 2 },
];

function mountBarChartWrapper(props: BarChartProps) {
    return mount(BarChart, {
        propsData: props,
    });
}

describe("BarChart.vue", () => {
    describe("Chart Rendering", () => {
        it("should render a bar chart when there is data", () => {
            const wrapper = mountBarChartWrapper({
                title: "Test Bar Chart",
                data: TEST_DATA,
            });
            expect(wrapper.find("svg").exists()).toBe(true);
        });

        it("should not render a bar chart when there is no data", () => {
            const wrapper = mountBarChartWrapper({
                title: "Test Bar Chart",
                data: [],
            });
            expect(wrapper.find("svg").exists()).toBe(false);
        });

        it("should render a bar chart with the correct title", () => {
            const title = "Test Bar Chart";
            const wrapper = mountBarChartWrapper({
                title,
                data: TEST_DATA,
            });
            expect(wrapper.find("h3").text()).toBe(title);
        });

        it("should render a bar chart with the correct description", () => {
            const description = "Test description";
            const wrapper = mountBarChartWrapper({
                title: "Test Bar Chart",
                data: TEST_DATA,
                description,
            });
            expect(wrapper.find(".chart-description").text()).toBe(description);
        });

        it("should render a bar chart with the correct width and height", () => {
            const width = 500;
            const height = 500;
            const wrapper = mountBarChartWrapper({
                title: "Test Bar Chart",
                data: TEST_DATA,
                width,
                height,
            });
            expect(wrapper.find("svg").attributes("width")).toBe(width.toString());
            expect(wrapper.find("svg").attributes("height")).toBe(height.toString());
        });

        it("should render a bar chart with the correct number of bars", () => {
            const wrapper = mountBarChartWrapper({
                title: "Test Bar Chart",
                data: TEST_DATA,
            });
            expect(wrapper.findAll(".bar").length).toBe(TEST_DATA.length);
        });

        it("should render a bar chart with the correct number of legend items", () => {
            const wrapper = mountBarChartWrapper({
                title: "Test Bar Chart",
                data: TEST_DATA,
            });
            expect(wrapper.findAll(".legend-item").length).toBe(TEST_DATA.length);
        });

        it("should render a bar chart with the correct legend labels", () => {
            const wrapper = mountBarChartWrapper({
                title: "Test Bar Chart",
                data: TEST_DATA,
            });
            TEST_DATA.forEach((dataPoint, index) => {
                expect(wrapper.findAll(".legend-item").at(index).text()).toContain(dataPoint.label);
            });
        });

        it("should refresh the bar chart and legend when the data prop changes", async () => {
            const wrapper = mountBarChartWrapper({
                title: "Test Bar Chart",
                data: TEST_DATA,
            });
            const newTestData = [
                ...TEST_DATA,
                { id: "id3", label: "baz", value: 3 },
                { id: "id4", label: "qux", value: 4 },
            ];
            await wrapper.setProps({
                data: newTestData,
            });
            expect(wrapper.findAll(".bar").length).toBe(newTestData.length);
            expect(wrapper.findAll(".legend-item").length).toBe(newTestData.length);
        });

        it("should refresh the bar chart and legend when the labelFormatter prop changes", async () => {
            const wrapper = mountBarChartWrapper({
                title: "Test Bar Chart",
                data: TEST_DATA,
            });
            const newLabelFormatter = (dataPoint?: DataValuePoint | null) => {
                return dataPoint?.label.toUpperCase() || "";
            };
            await wrapper.setProps({
                labelFormatter: newLabelFormatter,
            });
            TEST_DATA.forEach((dataPoint, index) => {
                expect(wrapper.findAll(".legend-item").at(index).text()).toContain(newLabelFormatter(dataPoint));
            });
        });
    });

    describe("Chart Options", () => {
        describe("Chart Tooltips", () => {
            it("should display chart-tooltip when a bar is hovered and enableTooltips is true", async () => {
                const wrapper = mountBarChartWrapper({
                    title: "Test Bar Chart",
                    data: TEST_DATA,
                    enableTooltips: true,
                });
                expect(wrapper.find(".chart-tooltip").isVisible()).toBe(false);
                await wrapper.find(".bar").trigger("mouseenter");
                expect(wrapper.find(".chart-tooltip").isVisible()).toBe(true);
            });

            it("should not display chart-tooltip when a bar is hovered and enableTooltips is false", async () => {
                const wrapper = mountBarChartWrapper({
                    title: "Test Bar Chart",
                    data: TEST_DATA,
                    enableTooltips: false,
                });
                expect(wrapper.find(".chart-tooltip").isVisible()).toBe(false);
                await wrapper.find(".bar").trigger("mouseenter");
                expect(wrapper.find(".chart-tooltip").isVisible()).toBe(false);
            });

            it("should display the correct label in the chart-tooltip when a bar is hovered and enableTooltips is true", async () => {
                const wrapper = mountBarChartWrapper({
                    title: "Test Bar Chart",
                    data: TEST_DATA,
                    enableTooltips: true,
                });
                await wrapper.find(".bar").trigger("mouseenter");
                expect(wrapper.find(".chart-tooltip").text()).toContain(TEST_DATA.at(0)?.label);
            });
        });

        describe("Chart Selection", () => {
            it("should display the selection-info when a bar is clicked and enableSelection is true", async () => {
                const wrapper = mountBarChartWrapper({
                    title: "Test Bar Chart",
                    data: TEST_DATA,
                    enableSelection: true,
                });
                await wrapper.find(".bar").trigger("click");
                expect(wrapper.find(".selection-info").exists()).toBe(true);
            });

            it("should not display the selection-info when a bar is clicked and enableSelection is false", async () => {
                const wrapper = mountBarChartWrapper({
                    title: "Test Bar Chart",
                    data: TEST_DATA,
                    enableSelection: false,
                });
                await wrapper.find(".bar").trigger("click");
                expect(wrapper.find(".selection-info").exists()).toBe(false);
            });

            it("should emit selection-changed event when a bar is clicked and enableSelection is true", async () => {
                const wrapper = mountBarChartWrapper({
                    title: "Test Bar Chart",
                    data: TEST_DATA,
                    enableSelection: true,
                });
                expect(wrapper.emitted("selection-changed")).toBeFalsy();
                await wrapper.find(".bar").trigger("click");
                expect(wrapper.emitted("selection-changed")).toBeTruthy();
            });

            it("should not emit selection-changed event when a bar is clicked and enableSelection is false", async () => {
                const wrapper = mountBarChartWrapper({
                    title: "Test Bar Chart",
                    data: TEST_DATA,
                    enableSelection: false,
                });
                expect(wrapper.emitted("selection-changed")).toBeFalsy();
                await wrapper.find(".bar").trigger("click");
                expect(wrapper.emitted("selection-changed")).toBeFalsy();
            });

            it("should display the correct selection info when a bar is clicked and enableSelection is true", async () => {
                const wrapper = mountBarChartWrapper({
                    title: "Test Bar Chart",
                    data: TEST_DATA,
                    enableSelection: true,
                });
                await wrapper.find(".bar").trigger("click");
                expect(wrapper.find(".selection-info").text()).toContain(TEST_DATA.at(0)?.label);
            });
        });
    });
});
