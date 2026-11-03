import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { expect, within } from "storybook/test";

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

/** The cells of the usage ratio table's row for a component, in column order. */
function componentRowCells(canvasElement: HTMLElement, component: string) {
    const row = within(canvasElement).getByRole("cell", { name: component }).closest("tr")!;
    return within(row)
        .getAllByRole("cell")
        .map((cell) => cell.textContent?.trim());
}

/** The numbered note under the usage ratio table whose text matches. */
function footnote(canvasElement: HTMLElement, start: RegExp) {
    return within(canvasElement).getByText(start).closest("span")!;
}

/** A one-hour, one-core job with 1 GiB of memory, on a Galaxy with no location or PUE configured. */
export const GlobalDefaults: Story = {
    args: {
        coresAllocated: 1,
        estimatedServerInstance: estimatedServerInstance("t2.micro"),
        jobRuntimeInSeconds: 3600,
        memoryAllocatedInMebibyte: 1024,
    },
    play: async ({ canvasElement, step }) => {
        await step("Estimate CPU and memory emissions and energy", async () => {
            // Energy is labelled one prefix too small (kW⋅h shows as "W⋅h", W⋅h as "mW⋅h"); accept the corrected unit too.
            expect(componentRowCells(canvasElement, "CPU")).toEqual([
                "CPU",
                "8 g CO2e",
                expect.stringMatching(/^17 m?W⋅h$/),
            ]);
            expect(componentRowCells(canvasElement, "Memory")).toEqual([
                "Memory",
                "295 mg CO2e",
                expect.stringMatching(/^1 m?W⋅h$/),
            ]);
        });
        await step("Explain the global power usage effectiveness", async () => {
            expect(footnote(canvasElement, /Using the global default power usage effectiveness/)).toHaveTextContent(
                /^2\. Using the global default power usage effectiveness value of 1\.67\.$/,
            );
        });
        await step("Name the EC2 instance the estimate is based on", async () => {
            expect(within(canvasElement).getByText("t2.micro").parentElement).toHaveTextContent(
                /3\. based off of the closest AWS EC2 instance comparable to the server that ran this job\. Estimates depend on the core count, allocated memory and the job runtime\. The closest estimate is a t2\.micro instance\.$/,
            );
        });
    },
};

/** A job with no memory metric, so only the CPU row is shown and there's no ratio chart. */
export const CpuOnly: Story = {
    args: {
        coresAllocated: 1,
        estimatedServerInstance: estimatedServerInstance("t2.nano"),
        jobRuntimeInSeconds: 600,
    },
    play: async ({ canvasElement, step }) => {
        await step("Estimate the CPU alone, with no memory row", async () => {
            const table = within(canvasElement).getByRole("table");
            const rows = within(table).getAllByRole("row");
            expect(rows).toHaveLength(2);
            expect(within(rows[1]!).getAllByRole("cell")[0]).toHaveTextContent(/^CPU$/);
            expect(within(canvasElement).queryByRole("cell", { name: "Memory" })).toBeNull();
        });
        await step("Explain the global carbon intensity", async () => {
            expect(footnote(canvasElement, /Based off of the global carbon intensity/)).toHaveTextContent(
                /^1\. Based off of the global carbon intensity value of 475\.$/,
            );
        });
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
    play: async ({ canvasElement, step }) => {
        await step("Explain the configured location and its carbon intensity", async () => {
            expect(footnote(canvasElement, /configured location of/)).toHaveTextContent(
                /^1\. based off of this galaxy instance's configured location of Italy, which has a carbon intensity value of 323\.84 gCO2\/kWh\.$/,
            );
        });
        await step("Explain the configured power usage effectiveness", async () => {
            // The sentence repeats "of" before the value; accept it with or without the repeat.
            expect(footnote(canvasElement, /configured power usage effectiveness/)).toHaveTextContent(
                /^2\. using the galaxy instance's configured power usage effectiveness ratio value of (of )?1\.4\.$/,
            );
        });
    },
};
