<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
    jobRuntimeInSeconds: number;
    coresAllocated: number;
    memoryAllocatedInMebibyte?: number;
    ec2Instances: {
        name: string;
        mem: number;
        price: number;
        priceUnit: string;
        vCpuCount: number;
        cpu: {
            cpuModel: string;
            tdp: number;
            coreCount: number;
            source: string;
        }[];
    }[];
}>();

const computedAwsEstimate = computed(() => {
    const { coresAllocated, jobRuntimeInSeconds, memoryAllocatedInMebibyte } = props;

    if (coresAllocated <= 0 || jobRuntimeInSeconds <= 0) {
        return;
    }

    const adjustedMemoryAllocated = memoryAllocatedInMebibyte ? memoryAllocatedInMebibyte / 1024 : 0.5;

    // Estimate EC2 instance. Data is already sorted
    const ec2Instance = props.ec2Instances.find((ec) => {
        return ec.mem >= adjustedMemoryAllocated && ec.vCpuCount >= coresAllocated;
    });

    if (!ec2Instance) {
        return;
    }

    return {
        seconds: jobRuntimeInSeconds,
        requestedVCpuCount: coresAllocated,
        memory: adjustedMemoryAllocated,
        price: ((jobRuntimeInSeconds * ec2Instance.price) / 3600).toFixed(2),
        instance: ec2Instance,
    };
});
</script>

<template>
    <div v-if="computedAwsEstimate" id="aws-estimate" class="mt-4">
        <h3>AWS estimate</h3>

        <strong id="aws-cost">{{ computedAwsEstimate.price }} USD</strong>

        <br />

        This job requested {{ computedAwsEstimate.requestedVCpuCount }} core(s) and
        {{ computedAwsEstimate.memory.toFixed(3) }} GiB of memory. Given this information, the smallest EC2 machine we
        could find is:

        <span id="aws-name">{{ computedAwsEstimate.instance.name }}</span>
        (<span id="aws-mem">{{ computedAwsEstimate.instance.mem }}</span> GB /
        <span id="aws-vcpus">{{ computedAwsEstimate.instance.vCpuCount }}</span> vCPUs /
        <span id="aws-cpu">{{ computedAwsEstimate.instance.cpu.map(({ cpuModel }) => cpuModel).join(", ") }}</span
        >). This instance is priced at {{ computedAwsEstimate.instance.price }} USD/hour.

        <br />

        &ast;Please note, that these numbers are only estimates, all jobs are always free of charge for all users.
    </div>
</template>
