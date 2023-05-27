<script setup lang="ts">
import { computed } from "vue";
import ec2 from "./ec2.json";

export interface AwsEstimateProps {
    jobRuntime: number;
    coresAllocated: number;
    memoryAllocated?: number;
}

const props = defineProps<AwsEstimateProps>();

const computedAwsEstimate = computed(() => {
    const { coresAllocated, jobRuntime, memoryAllocated } = props;

    if (coresAllocated <= 0 || jobRuntime <= 0) {
        return;
    }

    const adjustedMemoryAllocated = memoryAllocated ? memoryAllocated / 1024 : 0.5;

    // Estimate EC2 instance. Data is already sorted
    const ec2Instance = ec2.find((ec) => {
        return ec.mem >= adjustedMemoryAllocated && ec.vcpus >= coresAllocated;
    });

    if (!ec2Instance) {
        return;
    }

    return {
       seconds: jobRuntime,
       vcpus: coresAllocated,
       memory: adjustedMemoryAllocated,
       price: ((jobRuntime * ec2Instance.price) / 3600).toFixed(2),
       instance: ec2Instance
    };
});
</script>

<template>
    <div v-if="computedAwsEstimate" id="aws-estimate" class="mt-4">
        <h3>AWS estimate</h3>

        <strong id="aws-cost">{{ computedAwsEstimate.price }} USD</strong>

        <br />

        This job requested {{ computedAwsEstimate.vcpus }} core(s) and
        {{ computedAwsEstimate.memory.toFixed(3) }} GiB of memory. Given this
        information, the smallest EC2 machine we could find is:

        <span id="aws-name">{{ computedAwsEstimate.instance.name }}</span>
        (<span id="aws-mem">{{ computedAwsEstimate.instance.mem }}</span> GB /
        <span id="aws-vcpus">{{ computedAwsEstimate.instance.vcpus }}</span> vCPUs /
        <span id="aws-cpu">{{ computedAwsEstimate.instance.cpu.join(", ") }}</span
        >). This instance is priced at {{ computedAwsEstimate.instance.price }} USD/hour.

        <br />

        &ast;Please note, that these numbers are only estimates, all jobs are always free of charge for all users.
    </div>
</template>
