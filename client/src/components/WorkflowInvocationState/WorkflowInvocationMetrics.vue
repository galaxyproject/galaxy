<script setup lang="ts">
import type { VisualizationSpec } from "vega-embed";
import { computed, ref, watch } from "vue";
import { type ComputedRef } from "vue";

import { type components, GalaxyApi } from "@/api";
import { getAppRoot } from "@/onload/loadConfig";
import { errorMessageAsString } from "@/utils/simple-error";

const VegaWrapper = () => import("./VegaWrapper.vue");

const props = defineProps({
    invocationId: {
        type: String,
        required: true,
    },
});

const groupBy = ref<"tool_id" | "step_id">("tool_id");
const jobMetrics = ref<components["schemas"]["WorkflowJobMetric"][]>();
const fetchError = ref<string>();

const attributeToLabel = {
    tool_id: "Tool ID",
    step_id: "Step",
};

async function fetchMetrics() {
    const { data, error } = await GalaxyApi().GET("/api/invocations/{invocation_id}/metrics", {
        params: {
            path: {
                invocation_id: props.invocationId,
            },
        },
    });
    if (error) {
        fetchError.value = errorMessageAsString(error);
    } else {
        jobMetrics.value = data;
    }
}

watch(props, () => fetchMetrics(), { immediate: true });

function itemToX(item: components["schemas"]["WorkflowJobMetric"]) {
    if (groupBy.value === "tool_id") {
        return item.tool_id;
    } else if (groupBy.value === "step_id") {
        return `${item.step_index + 1}: ${item.step_label || item.tool_id}`;
    } else {
        throw Error("Cannot happen");
    }
}

interface boxplotData {
    x_title: string;
    y_title: string;
    values?: { x: string; y: Number }[];
}

function metricToSpecData(
    jobMetrics: components["schemas"]["WorkflowJobMetric"][] | undefined,
    metricName: string,
    yTitle: string,
    transform?: (param: number) => number
) {
    const wallclock = jobMetrics?.filter((jobMetric) => jobMetric.name == metricName);
    const values = wallclock?.map((item) => {
        let y = parseFloat(item.raw_value);
        if (transform !== undefined) {
            y = transform(y);
        }
        return {
            y,
            x: itemToX(item),
            job_id: item.job_id,
            tooltip: "click to view job",
        };
    });
    return {
        x_title: attributeToLabel[groupBy.value],
        y_title: yTitle,
        values,
    };
}

const wallclock: ComputedRef<boxplotData> = computed(() => {
    return metricToSpecData(jobMetrics.value, "runtime_seconds", "Runtime (in Seconds)");
});

const coresAllocated: ComputedRef<boxplotData> = computed(() => {
    return metricToSpecData(jobMetrics.value, "galaxy_slots", "Cores Allocated");
});

const memoryAllocated: ComputedRef<boxplotData> = computed(() => {
    return metricToSpecData(jobMetrics.value, "galaxy_memory_mb", "Memory Allocated (in MB)");
});

const peakMemory: ComputedRef<boxplotData> = computed(() => {
    return metricToSpecData(jobMetrics.value, "memory.peak", "Max memory usage recorded (in MB)", (v) => v / 1024 ** 2);
});

function itemToSpec(item: boxplotData) {
    const spec: VisualizationSpec = {
        $schema: "https://vega.github.io/schema/vega-lite/v5.json",
        description: "A boxplot with jittered points.",
        data: {
            values: item.values!,
        },
        transform: [
            {
                calculate: "random() - 0.5",
                as: "random_jitter",
            },
            {
                calculate: "'" + getAppRoot() + "jobs/' + datum.job_id + '/view'",
                as: "url",
            },
        ],
        layer: [
            {
                mark: { type: "boxplot", opacity: 0.5 },
                encoding: {
                    x: { field: "x", type: "nominal" },
                    y: { field: "y", type: "quantitative" },
                },
                width: "container",
            },
            {
                mark: {
                    type: "point",
                    opacity: 0.7,
                },
                encoding: {
                    x: {
                        field: "x",
                        type: "nominal",
                        title: item.x_title,
                        axis: {
                            labelAngle: -45,
                            labelAlign: "right",
                        },
                    },
                    xOffset: { field: "random_jitter", type: "quantitative", scale: { domain: [-2, 2] } },
                    y: {
                        field: "y",
                        type: "quantitative",
                        scale: { zero: false },
                        title: item.y_title,
                    },
                    tooltip: { field: "tooltip", type: "nominal" },
                    href: { field: "url", type: "nominal" },
                },
                width: "container",
            },
        ],
    };
    return spec;
}

const specs = computed(() => {
    const items = [wallclock.value, coresAllocated.value, memoryAllocated.value, peakMemory.value].filter(
        (item) => item.values?.length
    );
    const specs = Object.fromEntries(items.map((item) => [item.y_title, itemToSpec(item)]));
    return specs;
});
</script>

<template>
    <div>
        <b-tabs lazy>
            <b-tab title="Summary by Tool" @click="groupBy = 'tool_id'">
                <div v-for="(spec, key) in specs" :key="key">
                    <h2 class="h-l truncate text-center">{{ key }}</h2>
                    <VegaWrapper :spec="spec" />
                </div>
            </b-tab>
            <b-tab title="Summary by Workflow Step" @click="groupBy = 'step_id'">
                <div v-for="(spec, key) in specs" :key="key">
                    <h2 class="h-l truncate text-center">{{ key }}</h2>
                    <VegaWrapper :spec="spec" />
                </div>
            </b-tab>
        </b-tabs>
    </div>
</template>
