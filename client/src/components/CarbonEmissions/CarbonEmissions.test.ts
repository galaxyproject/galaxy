import { createTestingPinia } from "@pinia/testing";
import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import { ref } from "vue";

import { worldwideCarbonIntensity } from "./carbonEmissionConstants";

import CarbonEmissions from "./CarbonEmissions.vue";

const carbonIntensity = ref(worldwideCarbonIntensity);
const geographicalServerLocationName = ref("GLOBAL");
jest.mock("@/composables/carbonEmissions", () => ({
    useCarbonEmissions: () => {
        return {
            carbonIntensity,
            geographicalServerLocationName,
        };
    },
}));

const localVue = getLocalVue();
const pinia = createTestingPinia();
const slots = {
    header: "<div>foo</div>",
    footer: "<div>bar</div>",
};

describe("CarbonEmissions/CarbonEmissions.vue", () => {
    it("correctly calculates carbon emissions.", () => {
        const wrapper = mount(CarbonEmissions as any, {
            propsData: {
                energyNeededCPU: 0.015,
                energyNeededMemory: 0.005,
            },
            pinia,
            slots,
            localVue,
        });

        const cpuEmissions = wrapper.find("#cpu-carbon-emissions").text();
        const memoryEmissions = wrapper.find("#memory-carbon-emissions").text();
        const cpuEnergyUsage = wrapper.find("#cpu-energy-usage").text();
        const memoryEnergyUsage = wrapper.find("#memory-energy-usage").text();

        expect(cpuEmissions).toMatch("7 g CO2e");
        expect(memoryEmissions).toMatch("2 g CO2e");
        expect(cpuEnergyUsage).toMatch("15 mW⋅h");
        expect(memoryEnergyUsage).toMatch("5 mW⋅h");
    });

    it("does not render any data for memory if its memroy usage is 0.", () => {
        const wrapper = mount(CarbonEmissions as any, {
            propsData: {
                energyNeededCPU: 0,
                energyNeededMemory: 0,
            },
            pinia,
            slots,
            localVue,
        });

        expect(wrapper.find("#memory-energy-usage").exists()).toBe(false);
        expect(wrapper.find("#memroy-carbon-emissions").exists()).toBe(false);
    });

    it("takes the configured `carbonIntensity` value into account.", () => {
        carbonIntensity.value = 0;
        const wrapper = mount(CarbonEmissions as any, {
            propsData: {
                energyNeededCPU: 1_000,
                energyNeededMemory: 1_000,
            },
            pinia,
            slots,
            localVue,
        });

        const cpuEmissions = wrapper.find("#cpu-carbon-emissions").text();
        const memoryEmissions = wrapper.find("#memory-carbon-emissions").text();

        expect(cpuEmissions).toMatch("0 g CO2e");
        expect(memoryEmissions).toMatch("0 g CO2e");
    });
});
