import { composeStories } from "@storybook/vue3-vite";
import { useStoryMount } from "@tests/vitest/stories";
import { describe, expect, it } from "vitest";

import { worldwideCarbonIntensity, worldwidePowerUsageEffectiveness } from "./carbonEmissionConstants.js";
import * as CarbonEmissionsStories from "./CarbonEmissions.stories";

const stories = composeStories(CarbonEmissionsStories);
const mountStory = useStoryMount();

describe("CarbonEmissions/CarbonEmissions.vue", () => {
    it("shows CPU and memory emissions and energy estimates", () => {
        const wrapper = mountStory(stories.GlobalDefaults);

        const cpuEmissions = wrapper.get("#cpu-carbon-emissions").text();
        const memoryEmissions = wrapper.get("#memory-carbon-emissions").text();
        const cpuEnergyUsage = wrapper.get("#cpu-energy-usage").text();
        const memoryEnergyUsage = wrapper.get("#memory-energy-usage").text();

        expect(cpuEmissions).toBe("8 g CO2e");
        expect(memoryEmissions).toBe("295 mg CO2e");
        expect(cpuEnergyUsage).toBe("17 mW⋅h");
        expect(memoryEnergyUsage).toBe("1 mW⋅h");
    });

    it("omits memory estimates when memory allocation is absent", () => {
        const wrapper = mountStory(stories.CpuOnly);

        expect(wrapper.find("#memory-carbon-emissions").exists()).toBe(false);
        expect(wrapper.find("#memory-energy-usage").exists()).toBe(false);
    });

    it("shows zero emissions and energy for zero power usage effectiveness", () => {
        const wrapper = mountStory(stories.GlobalDefaults, { props: { powerUsageEffectiveness: 0 } });

        const cpuEmissions = wrapper.get("#cpu-carbon-emissions").text();
        const cpuEnergyUsage = wrapper.get("#cpu-energy-usage").text();
        const memoryEmissions = wrapper.get("#memory-carbon-emissions").text();
        const memoryEnergyUsage = wrapper.get("#memory-energy-usage").text();

        expect(cpuEmissions).toBe("0 g CO2e");
        expect(cpuEnergyUsage).toBe("0 kW⋅h");
        expect(memoryEmissions).toBe("0 g CO2e");
        expect(memoryEnergyUsage).toBe("0 kW⋅h");
    });

    it("shows zero emissions for zero carbon intensity", () => {
        const wrapper = mountStory(stories.GlobalDefaults, { props: { carbonIntensity: 0 } });

        const cpuEmissions = wrapper.get("#cpu-carbon-emissions").text();
        const memoryEmissions = wrapper.get("#memory-carbon-emissions").text();

        expect(cpuEmissions).toBe("0 g CO2e");
        expect(memoryEmissions).toBe("0 g CO2e");
    });

    it("explains the global carbon intensity", () => {
        const carbonIntensity = worldwideCarbonIntensity;
        const wrapper = mountStory(stories.CpuOnly);
        const locationText = wrapper.get("#location-explanation").element;
        expect(locationText).toHaveTextContent(
            `1. Based off of the global carbon intensity value of ${carbonIntensity}.`,
        );
    });

    it("explains the configured location and its carbon intensity", () => {
        const { geographicalServerLocationName: locationName, carbonIntensity } = stories.ConfiguredLocation.args;
        const wrapper = mountStory(stories.ConfiguredLocation);

        const locationElement = wrapper.get("#location-explanation").element;
        expect(locationElement).toHaveTextContent(
            `1. based off of this galaxy instance's configured location of ${locationName}, which has a carbon intensity value of ${carbonIntensity} gCO2/kWh.`,
        );
    });

    it("explains the global power usage effectiveness", () => {
        const powerUsageEffectiveness = worldwidePowerUsageEffectiveness;
        const wrapper = mountStory(stories.GlobalDefaults);

        const locationElement = wrapper.get("#pue").element;
        expect(locationElement).toHaveTextContent(
            `2. Using the global default power usage effectiveness value of ${powerUsageEffectiveness}.`,
        );
    });
});
