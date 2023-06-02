import { getLocalVue } from "tests/jest/helpers";
import CarbonEmissions from "./CarbonEmissions";
import { mount } from "@vue/test-utils";

const localVue = getLocalVue();

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
    it("correctly calculates carbon emissions.", async () => {
        const wrapper = mount(CarbonEmissions, {
            propsData: {
                estimatedServerInstance: testServerInstance,
                jobRuntimeInSeconds: oneHourInSeconds,
                coresAllocated: 1,
                memoryAllocatedInMebibyte: oneGibibyteMemoryInMebibyte,
            },
            localVue,
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
                estimatedServerInstance: testServerInstance,
                jobRuntime: 1,
                coresAllocated: 1,
            },
            localVue,
        });

        expect(wrapper.find("#memory-carbon-emissions").exists()).toBe(false);
        expect(wrapper.find("#memory-energy-usage").exists()).toBe(false);
    });
});
