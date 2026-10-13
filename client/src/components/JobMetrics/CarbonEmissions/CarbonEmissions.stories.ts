import type { Meta, StoryObj } from "@storybook/vue3-vite";

import { ec2Instances } from "../awsEc2ReferenceData.js";
import { worldwideCarbonIntensity, worldwidePowerUsageEffectiveness } from "./carbonEmissionConstants.js";

import CarbonEmissions from "./CarbonEmissions.vue";

/** The named EC2 instance as JobMetrics passes it: its first CPU stands in for the server's. */
function estimatedServerInstance(name: string) {
    const instance = ec2Instances.find((candidate) => candidate.name === name);
    if (!instance) {
        throw new Error(`No EC2 instance named ${name}`);
    }
    const cpu = instance.cpu[0]!;
    return {
        name: instance.name,
        cpuInfo: { modelName: cpu.cpuModel, totalAvailableCores: cpu.coreCount, tdp: cpu.tdp },
    };
}

const meta = {
    title: "JobMetrics/CarbonEmissions",
    component: CarbonEmissions,
    args: {
        carbonIntensity: worldwideCarbonIntensity,
        geographicalServerLocationName: "GLOBAL",
        powerUsageEffectiveness: worldwidePowerUsageEffectiveness,
    },
} satisfies Meta<typeof CarbonEmissions>;

export default meta;
type Story = StoryObj<typeof meta>;

/** A one-hour, one-core job with 1 GiB of memory, on a Galaxy with no location or PUE configured. */
export const GlobalDefaults: Story = {
    args: {
        coresAllocated: 1,
        estimatedServerInstance: estimatedServerInstance("t2.micro"),
        jobRuntimeInSeconds: 3600,
        memoryAllocatedInMebibyte: 1024,
    },
};

/** A job with no memory metric, so only the CPU row is shown and there's no ratio chart. */
export const CpuOnly: Story = {
    args: {
        coresAllocated: 1,
        estimatedServerInstance: estimatedServerInstance("t2.nano"),
        jobRuntimeInSeconds: 600,
    },
};

/** A Galaxy configured in Italy with its own data centre PUE. */
export const ConfiguredLocation: Story = {
    args: {
        carbonIntensity: 323.84,
        coresAllocated: 2,
        estimatedServerInstance: estimatedServerInstance("t3.micro"),
        geographicalServerLocationName: "Italy",
        jobRuntimeInSeconds: 1800,
        memoryAllocatedInMebibyte: 1024,
        powerUsageEffectiveness: 1.4,
    },
};
