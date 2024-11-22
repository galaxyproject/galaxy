import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import VueRouter from "vue-router";

import { worldwideCarbonIntensity, worldwidePowerUsageEffectiveness } from "./carbonEmissionConstants.js";
import CarbonEmissions from "./CarbonEmissions";

const localVue = getLocalVue();
localVue.use(VueRouter);
const router = new VueRouter();

const oneGibibyteMemoryInMebibyte = 1024;
const oneHourInSeconds = 3600;
const testServerInstance = {
    name: "some-server-name",
    cpuInfo: {
        modelName: "some-processor-name",
        totalAvailableCores: 10,
        tdp: 100,
    },
};

describe("CarbonEmissions/CarbonEmissions.vue", () => {
    it("correctly calculates carbon emissions.", () => {
        const wrapper = mount(CarbonEmissions, {
            propsData: {
                carbonIntensity: worldwideCarbonIntensity,
                coresAllocated: 1,
                estimatedServerInstance: testServerInstance,
                jobRuntimeInSeconds: oneHourInSeconds,
                memoryAllocatedInMebibyte: oneGibibyteMemoryInMebibyte,
                powerUsageEffectiveness: worldwidePowerUsageEffectiveness,
                geographicalServerLocationName: "GLOBAL",
            },
            localVue,
            router,
        });

        const cpuEmissions = wrapper.find("#cpu-carbon-emissions").text();
        const memoryEmissions = wrapper.find("#memory-carbon-emissions").text();
        const cpuEnergyUsage = wrapper.find("#cpu-energy-usage").text();
        const memoryEnergyUsage = wrapper.find("#memory-energy-usage").text();

        expect(cpuEmissions).toMatch("8 g CO2e");
        expect(memoryEmissions).toMatch("295 mg CO2e");
        expect(cpuEnergyUsage).toMatch("17 mW⋅h");
        expect(memoryEnergyUsage).toMatch("1 mW⋅h");
    });

    it("does not render memory estimates when no value can be determined.", () => {
        const wrapper = mount(CarbonEmissions, {
            propsData: {
                coresAllocated: 1,
                estimatedServerInstance: testServerInstance,
                jobRuntimeInSeconds: 1,
                geographicalServerLocationName: "GLOBAL",
                powerUsageEffectiveness: worldwidePowerUsageEffectiveness,
                carbonIntensity: worldwideCarbonIntensity,
            },
            localVue,
            router,
        });

        expect(wrapper.find("#memory-carbon-emissions").exists()).toBe(false);
        expect(wrapper.find("#memory-energy-usage").exists()).toBe(false);
    });

    it("takes the configured `powerUsageEffectiveness` value into account.", () => {
        const wrapper = mount(CarbonEmissions, {
            propsData: {
                carbonIntensity: 1,
                coresAllocated: 1,
                estimatedServerInstance: testServerInstance,
                jobRuntimeInSeconds: 1,
                memoryAllocatedInMebibyte: 1,
                powerUsageEffectiveness: 0,
                geographicalServerLocationName: "GLOBAL",
            },
            localVue,
            router,
        });

        const cpuEmissions = wrapper.find("#cpu-carbon-emissions").text();
        const cpuEnergyUsage = wrapper.find("#cpu-energy-usage").text();
        const memoryEmissions = wrapper.find("#memory-carbon-emissions").text();
        const memoryEnergyUsage = wrapper.find("#memory-energy-usage").text();

        expect(cpuEmissions).toMatch("0 g CO2e");
        expect(cpuEnergyUsage).toMatch("0 kW⋅h");
        expect(memoryEmissions).toMatch("0 g CO2e");
        expect(memoryEnergyUsage).toMatch("0 kW⋅h");
    });

    it("takes the configured `carbonIntensity` value into account.", () => {
        const wrapper = mount(CarbonEmissions, {
            propsData: {
                carbonIntensity: 0,
                coresAllocated: 1,
                estimatedServerInstance: testServerInstance,
                jobRuntimeInSeconds: 1,
                memoryAllocatedInMebibyte: 1,
                powerUsageEffectiveness: 1,
                geographicalServerLocationName: "GLOBAL",
            },
            localVue,
            router,
        });

        const cpuEmissions = wrapper.find("#cpu-carbon-emissions").text();
        const memoryEmissions = wrapper.find("#memory-carbon-emissions").text();

        expect(cpuEmissions).toMatch("0 g CO2e");
        expect(memoryEmissions).toMatch("0 g CO2e");
    });

    it("displays text saying that global values were used when the `geographicalServerLocationName` prop is set to `GLOBAL`.", () => {
        const carbonIntensity = worldwideCarbonIntensity;
        const wrapper = mount(CarbonEmissions, {
            propsData: {
                carbonIntensity,
                coresAllocated: 2,
                estimatedServerInstance: testServerInstance,
                jobRuntimeInSeconds: 2,
                geographicalServerLocationName: "GLOBAL",
                powerUsageEffectiveness: worldwidePowerUsageEffectiveness,
            },
            localVue,
            router,
        });
        const locationText = wrapper.find("#location-explanation").element;
        expect(locationText).toHaveTextContent(
            `1. Based off of the global carbon intensity value of ${carbonIntensity}.`
        );
    });

    it("displays text saying that the carbon intensity value corresponding to `geographicalServerLocationName` was used.", () => {
        const locationName = "Italy";
        const carbonIntensity = worldwideCarbonIntensity;
        const wrapper = mount(CarbonEmissions, {
            propsData: {
                carbonIntensity,
                coresAllocated: 2,
                estimatedServerInstance: testServerInstance,
                jobRuntimeInSeconds: 2,
                memoryAllocatedInMebibyte: oneGibibyteMemoryInMebibyte,
                powerUsageEffectiveness: worldwideCarbonIntensity,
                geographicalServerLocationName: locationName,
            },
            localVue,
            router,
        });

        const locationElement = wrapper.find("#location-explanation").element;
        expect(locationElement).toHaveTextContent(
            `1. based off of this galaxy instance's configured location of ${locationName}, which has a carbon intensity value of ${carbonIntensity} gCO2/kWh.`
        );
    });

    it("displays text saying that global average values for PUE where used when `powerUsageEffectiveness` matches the global average.", () => {
        const powerUsageEffectiveness = worldwidePowerUsageEffectiveness;
        const wrapper = mount(CarbonEmissions, {
            propsData: {
                carbonIntensity: 1,
                coresAllocated: 1,
                estimatedServerInstance: testServerInstance,
                jobRuntimeInSeconds: 1,
                memoryAllocatedInMebibyte: 1,
                powerUsageEffectiveness,
                geographicalServerLocationName: "GLOBAL",
            },
            localVue,
            router,
        });

        const locationElement = wrapper.find("#pue").element;
        expect(locationElement).toHaveTextContent(
            `2. Using the global default power usage effectiveness value of ${powerUsageEffectiveness}.`
        );
    });
});
