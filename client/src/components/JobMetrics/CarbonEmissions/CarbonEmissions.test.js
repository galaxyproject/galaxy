import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import { createPinia, disposePinia, getActivePinia, setActivePinia } from "pinia";
import { afterEach, describe, expect, it, onTestFinished } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";

import { worldwideCarbonIntensity, worldwidePowerUsageEffectiveness } from "./carbonEmissionConstants.js";

import CarbonEmissions from "./CarbonEmissions.vue";

const localVue = getLocalVue();
enableAutoUnmount(afterEach);

function mountCarbonEmissions(props) {
    const pinia = createPinia();
    const history = createMemoryHistory();
    const router = createRouter({ history, routes: [] });
    onTestFinished(() => {
        disposePinia(pinia);
        if (getActivePinia() === pinia) {
            setActivePinia(undefined);
        }
        history.destroy();
    });
    return mount(CarbonEmissions, { props, global: withPlugins(localVue, pinia, router) });
}

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
    it("shows CPU and memory emissions and energy estimates", () => {
        const wrapper = mountCarbonEmissions({
            carbonIntensity: worldwideCarbonIntensity,
            coresAllocated: 1,
            estimatedServerInstance: testServerInstance,
            jobRuntimeInSeconds: oneHourInSeconds,
            memoryAllocatedInMebibyte: oneGibibyteMemoryInMebibyte,
            powerUsageEffectiveness: worldwidePowerUsageEffectiveness,
            geographicalServerLocationName: "GLOBAL",
        });

        const cpuEmissions = wrapper.get("#cpu-carbon-emissions").text();
        const memoryEmissions = wrapper.get("#memory-carbon-emissions").text();
        const cpuEnergyUsage = wrapper.get("#cpu-energy-usage").text();
        const memoryEnergyUsage = wrapper.get("#memory-energy-usage").text();

        expect(cpuEmissions).toMatch("8 g CO2e");
        expect(memoryEmissions).toMatch("295 mg CO2e");
        expect(cpuEnergyUsage).toMatch("17 mW⋅h");
        expect(memoryEnergyUsage).toMatch("1 mW⋅h");
    });

    it("omits memory estimates when memory allocation is absent", () => {
        const wrapper = mountCarbonEmissions({
            coresAllocated: 1,
            estimatedServerInstance: testServerInstance,
            jobRuntimeInSeconds: 1,
            geographicalServerLocationName: "GLOBAL",
            powerUsageEffectiveness: worldwidePowerUsageEffectiveness,
            carbonIntensity: worldwideCarbonIntensity,
        });

        expect(wrapper.find("#memory-carbon-emissions").exists()).toBe(false);
        expect(wrapper.find("#memory-energy-usage").exists()).toBe(false);
    });

    it("shows zero emissions and energy for zero power usage effectiveness", () => {
        const wrapper = mountCarbonEmissions({
            carbonIntensity: 1,
            coresAllocated: 1,
            estimatedServerInstance: testServerInstance,
            jobRuntimeInSeconds: 1,
            memoryAllocatedInMebibyte: 1,
            powerUsageEffectiveness: 0,
            geographicalServerLocationName: "GLOBAL",
        });

        const cpuEmissions = wrapper.get("#cpu-carbon-emissions").text();
        const cpuEnergyUsage = wrapper.get("#cpu-energy-usage").text();
        const memoryEmissions = wrapper.get("#memory-carbon-emissions").text();
        const memoryEnergyUsage = wrapper.get("#memory-energy-usage").text();

        expect(cpuEmissions).toMatch("0 g CO2e");
        expect(cpuEnergyUsage).toMatch("0 kW⋅h");
        expect(memoryEmissions).toMatch("0 g CO2e");
        expect(memoryEnergyUsage).toMatch("0 kW⋅h");
    });

    it("shows zero emissions for zero carbon intensity", () => {
        const wrapper = mountCarbonEmissions({
            carbonIntensity: 0,
            coresAllocated: 1,
            estimatedServerInstance: testServerInstance,
            jobRuntimeInSeconds: 1,
            memoryAllocatedInMebibyte: 1,
            powerUsageEffectiveness: 1,
            geographicalServerLocationName: "GLOBAL",
        });

        const cpuEmissions = wrapper.get("#cpu-carbon-emissions").text();
        const memoryEmissions = wrapper.get("#memory-carbon-emissions").text();

        expect(cpuEmissions).toMatch("0 g CO2e");
        expect(memoryEmissions).toMatch("0 g CO2e");
    });

    it("explains the global carbon intensity", () => {
        const carbonIntensity = worldwideCarbonIntensity;
        const wrapper = mountCarbonEmissions({
            carbonIntensity,
            coresAllocated: 2,
            estimatedServerInstance: testServerInstance,
            jobRuntimeInSeconds: 2,
            geographicalServerLocationName: "GLOBAL",
            powerUsageEffectiveness: worldwidePowerUsageEffectiveness,
        });
        const locationText = wrapper.get("#location-explanation").element;
        expect(locationText).toHaveTextContent(
            `1. Based off of the global carbon intensity value of ${carbonIntensity}.`,
        );
    });

    it("explains the configured location and its carbon intensity", () => {
        const locationName = "Italy";
        const carbonIntensity = worldwideCarbonIntensity;
        const wrapper = mountCarbonEmissions({
            carbonIntensity,
            coresAllocated: 2,
            estimatedServerInstance: testServerInstance,
            jobRuntimeInSeconds: 2,
            memoryAllocatedInMebibyte: oneGibibyteMemoryInMebibyte,
            powerUsageEffectiveness: worldwideCarbonIntensity,
            geographicalServerLocationName: locationName,
        });

        const locationElement = wrapper.get("#location-explanation").element;
        expect(locationElement).toHaveTextContent(
            `1. based off of this galaxy instance's configured location of ${locationName}, which has a carbon intensity value of ${carbonIntensity} gCO2/kWh.`,
        );
    });

    it("explains the global power usage effectiveness", () => {
        const powerUsageEffectiveness = worldwidePowerUsageEffectiveness;
        const wrapper = mountCarbonEmissions({
            carbonIntensity: 1,
            coresAllocated: 1,
            estimatedServerInstance: testServerInstance,
            jobRuntimeInSeconds: 1,
            memoryAllocatedInMebibyte: 1,
            powerUsageEffectiveness,
            geographicalServerLocationName: "GLOBAL",
        });

        const locationElement = wrapper.get("#pue").element;
        expect(locationElement).toHaveTextContent(
            `2. Using the global default power usage effectiveness value of ${powerUsageEffectiveness}.`,
        );
    });
});
