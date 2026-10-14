import type { Meta, StoryObj } from "@storybook/vue3-vite";

import { ec2Instances } from "./awsEc2ReferenceData.js";

import AwsEstimate from "./AwsEstimate.vue";

const meta = {
    title: "JobMetrics/AwsEstimate",
    component: AwsEstimate,
    args: { ec2Instances },
    argTypes: { ec2Instances: { control: false } },
} satisfies Meta<typeof AwsEstimate>;

export default meta;
type Story = StoryObj<typeof meta>;

/** A nine-second, one-core job with 2 GiB of memory, using Galaxy's bundled reference prices. */
export const ShortSingleCoreJob: Story = {
    args: { coresAllocated: 1, jobRuntimeInSeconds: 9, memoryAllocatedInMebibyte: 2048 },
};

/** A five-hour, forty-core job with 190 GiB of memory, using the same reference snapshot. */
export const LongMulticoreJob: Story = {
    args: { coresAllocated: 40, jobRuntimeInSeconds: 18000, memoryAllocatedInMebibyte: 194560 },
};
