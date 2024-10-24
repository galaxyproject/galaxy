<script setup lang="ts">
import { computed, ref, watch } from "vue";

import { type components, GalaxyApi } from "@/api";
import { errorMessageAsString } from "@/utils/simple-error";

import VegaWrapper from "./VegaWrapper.vue";

const props = defineProps({
    invocationId: {
        type: String,
        required: true,
    },
});

const jobMetrics = ref<components["schemas"]["WorkflowJobMetric"][]>();
const fetchError = ref<string>();

async function fetchMetrics() {
    const { data, error } = await GalaxyApi().GET("/api/invocations/{invocation_id}/metrics", {
        params: {
            path: {
                invocation_id: props.invocationId,
            },
        },
    });
    console.log("data", data, error);
    if (error) {
        fetchError.value = errorMessageAsString(error);
    } else {
        jobMetrics.value = data;
    }
}

watch(props, () => fetchMetrics(), { immediate: true });

const wallclock = computed(() => {
    const wallclock = jobMetrics.value?.filter((jobMetric) => jobMetric.name == "runtime_seconds");
    return wallclock?.map((item) => {
        return {
            raw_value: parseFloat(item.raw_value),
            tool_id: item.tool_id,
        };
    });
});

const spec = computed(() => {
    console.log(wallclock.value);
    return {
        $schema: "https://vega.github.io/schema/vega-lite/v5.json",
        description: "A boxplot with jittered points.",
        data: {
            values: wallclock.value,
        },
        layer: [
            {
                mark: { type: "boxplot", opacity: 0.5 },
                encoding: {
                    x: { field: "tool_id", type: "ordinal" },
                    y: { field: "raw_value", type: "quantitative" },
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
                        field: "tool_id",
                        type: "ordinal",
                        bandPosition: { signal: "(random() + 0.05)" }, // Apply random jitter within the categorical band
                    },
                    y: {
                        field: "raw_value",
                        type: "quantitative",
                        axis: { title: "Raw Value" },
                        scale: { zero: false },
                    },
                },
                width: "container",
            },
        ],
    };
});
</script>

<template>
    <VegaWrapper v-if="spec" :spec="spec" />
</template>
