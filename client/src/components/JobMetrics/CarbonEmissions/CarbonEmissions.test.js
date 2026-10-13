import { composeStories } from "@storybook/vue3-vite";
import { useStoryMount } from "@tests/vitest/stories";
import { describe, expect, it } from "vitest";

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
});
