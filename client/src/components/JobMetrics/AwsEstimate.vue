<script setup lang="ts">
import { computed } from "vue";
import ec2 from "./ec2.json";

export interface AwsEstimateProps {
    jobRuntime: number;
    coresAllocated: number;
    memoryAllocated: number;
}

const props = withDefaults(defineProps<AwsEstimateProps>(), {
    memoryAllocated: 0.5,
});

const computedAwsEstimate = computed(() => {
    const aws: Record<string, any> = {};

    const { coresAllocated, jobRuntime, memoryAllocated } = props;

    aws.seconds = jobRuntime;
    aws.vcpus = coresAllocated;
    aws.memory = memoryAllocated;

    if (aws.memory) {
        aws.memory /= 1024;
    } else {
        // if memory was not specified, assign the smallest amount (we judge based on CPU-count only)
        aws.memory = 0.5;
    }

    // Estimate EC2 instance. Data is already sorted
    aws.instance = ec2.find((ec) => {
        return ec.mem >= aws.memory && ec.vcpus >= aws.vcpus;
    });

    if (!aws.instance) {
        return;
    }

    aws.price = ((aws.seconds * aws.instance.price) / 3600).toFixed(2);

    return aws;
});
</script>

<template>
    <div v-if="computedAwsEstimate" class="aws mt-4">
        <h3>AWS estimate</h3>

        <strong>{{ computedAwsEstimate.price }} USD</strong>

        <br />

        This job requested {{ computedAwsEstimate.vcpus }} core{{ computedAwsEstimate.vcpus > 1 ? "s" : "" }} and
        {{ computedAwsEstimate.memory.toFixed(3) }} GiB of memory. Given this information, the smallest EC2 machine we
        could find is:

        <span id="aws_name">{{ computedAwsEstimate.instance.name }}</span>
        (<span id="aws_mem">{{ computedAwsEstimate.instance.mem }}</span> GB /
        <span id="aws_vcpus">{{ computedAwsEstimate.instance.vcpus }}</span> vCPUs /
        <span v-for="cpu in computedAwsEstimate.instance.cpu" id="aws_cpu" :key="cpu">{{ cpu }}</span
        >). This instance is priced at {{ computedAwsEstimate.instance.price }} USD/hour.

        <br />

        &ast;Please note, that these numbers are only estimates, all jobs are always free of charge for all users.
    </div>
</template>
