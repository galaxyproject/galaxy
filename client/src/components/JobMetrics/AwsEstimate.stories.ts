import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { expect, waitFor } from "storybook/test";
import { h, onUnmounted } from "vue";

import { ec2Instances } from "./awsEc2ReferenceData.js";

import AwsEstimate from "./AwsEstimate.vue";

const meta = {
    title: "JobMetrics/AwsEstimate",
    component: AwsEstimate,
    decorators: [
        (story) => ({
            setup() {
                const ownKeys = () =>
                    Array.from({ length: localStorage.length }, (_, index) => localStorage.key(index)!).filter((key) =>
                        key.startsWith("toggle-state-aws-estimate-"),
                    );
                const previous = new Map(ownKeys().map((key) => [key, localStorage.getItem(key)!]));
                // Wait until the child's storage watchers are disposed before restoring its section state.
                onUnmounted(() => {
                    for (const key of ownKeys()) {
                        if (!previous.has(key)) {
                            localStorage.removeItem(key);
                        }
                    }
                    for (const [key, value] of previous) {
                        localStorage.setItem(key, value);
                    }
                });
            },
            render: () => h(story()),
        }),
    ],
    args: { ec2Instances },
    argTypes: { ec2Instances: { control: false } },
} satisfies Meta<typeof AwsEstimate>;

export default meta;
type Story = StoryObj<typeof meta>;
type PlayContext = Parameters<NonNullable<Story["play"]>>[0];

async function readEstimate(context: PlayContext, name: string, cost: string) {
    await expect(context.canvas.getByRole("heading", { name: "AWS estimate", level: 2 })).toBeVisible();
    const expand = context.canvas.queryByRole("button", { name: "Expand section" });
    if (expand) {
        await expect(context.canvas.queryByText(cost, { exact: true })).not.toBeInTheDocument();
        await context.userEvent.click(expand);
    }
    await expect(context.canvas.getByRole("button", { name: "Collapse section" })).toHaveAttribute(
        "aria-expanded",
        "true",
    );
    await expect(context.canvas.getByText(name, { exact: true })).toBeVisible();
    await expect(context.canvas.getByText(cost, { exact: true })).toBeVisible();
    const instance = ec2Instances.find((candidate) => candidate.name === name)!;
    await expect(context.canvas.getByText(instance.mem.toString(), { exact: true })).toBeVisible();
    await expect(context.canvas.getByText(instance.vCpuCount.toString(), { exact: true })).toBeVisible();
    await expect(
        context.canvas.getByText(instance.cpu.map(({ cpuModel }) => cpuModel).join(", "), { exact: true }),
    ).toBeVisible();
}

/** A nine-second, one-core job with 2 GiB of memory, using Galaxy's bundled reference prices. */
export const ShortSingleCoreJob: Story = {
    play: async (context) => {
        await context.step("Read the smallest instance and exact estimate for the short one-core job", async () => {
            await readEstimate(context, "t2.small", "0.00 USD");
        });
    },
    args: { coresAllocated: 1, jobRuntimeInSeconds: 9, memoryAllocatedInMebibyte: 2048 },
};

/** A five-hour, forty-core job with 190 GiB of memory, using the same reference snapshot. */
export const LongMulticoreJob: Story = {
    play: async (context) => {
        await context.step("Read the instance and exact estimate for the five-hour multicore job", async () => {
            await readEstimate(context, "m5d.12xlarge", "16.32 USD");
        });
    },
    args: { coresAllocated: 40, jobRuntimeInSeconds: 18000, memoryAllocatedInMebibyte: 194560 },
};

/** Hide and reveal the short job's estimate through the section controls. */
export const CollapsesAndExpandsEstimate: Story = {
    args: ShortSingleCoreJob.args,
    play: async (context) => {
        await context.step("Read the expanded short-job estimate", async () => {
            await readEstimate(context, "t2.small", "0.00 USD");
        });
        await context.step("Collapse the estimate while retaining its heading", async () => {
            await context.userEvent.click(context.canvas.getByRole("button", { name: "Collapse section" }));
            await expect(context.canvas.getByRole("heading", { name: "AWS estimate", level: 2 })).toBeVisible();
            await expect(context.canvas.getByRole("button", { name: "Expand section" })).toHaveAttribute(
                "aria-expanded",
                "false",
            );
            await waitFor(() =>
                expect(context.canvas.queryByText("0.00 USD", { exact: true })).not.toBeInTheDocument(),
            );
            await expect(context.canvas.queryByText("t2.small", { exact: true })).not.toBeInTheDocument();
        });
        await context.step("Expand the section and restore the complete estimate", async () => {
            await context.userEvent.click(context.canvas.getByRole("button", { name: "Expand section" }));
            await readEstimate(context, "t2.small", "0.00 USD");
        });
    },
};
