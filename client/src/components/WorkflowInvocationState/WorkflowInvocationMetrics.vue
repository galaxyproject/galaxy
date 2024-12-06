<script setup lang="ts">
import { BButtonGroup, BCol, BContainer, BRow } from "bootstrap-vue";
import type { VisualizationSpec } from "vega-embed";
import { computed, ref, watch } from "vue";
import { type ComputedRef } from "vue";

import { type components, GalaxyApi } from "@/api";
import { getAppRoot } from "@/onload/loadConfig";
import { errorMessageAsString } from "@/utils/simple-error";

import HelpText from "@/components/Help/HelpText.vue";

const VegaWrapper = () => import("./VegaWrapper.vue");

const props = defineProps({
    invocationId: {
        type: String,
        required: true,
    },
});

const groupBy = ref<"tool_id" | "step_id">("tool_id");
const timing = ref<"seconds" | "minutes" | "hours">("seconds");
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
    helpTerm?: string;
    values?: { x: string; y: Number }[];
}

interface piechartData {
    category_title: string;
    y_title: string;
    helpTerm?: string;
    values?: { category: string; y: Number }[];
}

interface JobInfo {
    toolId: string;
    stepIndex: number;
    stepLabel: string | null;
}

interface DerivedMetric {
    name: string;
    job_id: string;
    raw_value: string;
    tool_id: string;
    step_index: number;
    step_label: string | null;
}

type AnyMetric = components["schemas"]["WorkflowJobMetric"] & DerivedMetric;

function computeAllocatedCoreTime(
    jobMetrics: components["schemas"]["WorkflowJobMetric"][] | undefined
): DerivedMetric[] {
    const walltimePerJob: Record<string, number> = {};
    const coresPerJob: Record<string, number> = {};
    const jobInfo: Record<string, JobInfo> = {};
    jobMetrics?.forEach((jobMetric) => {
        if (jobMetric.name == "runtime_seconds") {
            walltimePerJob[jobMetric.job_id] = parseFloat(jobMetric.raw_value);
            jobInfo[jobMetric.job_id] = {
                toolId: jobMetric.tool_id,
                stepIndex: jobMetric.step_index,
                stepLabel: jobMetric.step_label,
            };
        } else if (jobMetric.name == "galaxy_slots") {
            coresPerJob[jobMetric.job_id] = parseFloat(jobMetric.raw_value);
        }
    });
    const thisMetric: DerivedMetric[] = [];
    Object.keys(walltimePerJob).map((jobId) => {
        const walltime: number | undefined = walltimePerJob[jobId];
        const cores: number | undefined = coresPerJob[jobId];
        const thisJobInfo = jobInfo[jobId];
        if (cores && thisJobInfo && walltime) {
            const metric: DerivedMetric = {
                name: "allocated_core_time",
                job_id: jobId,
                raw_value: (cores * walltime).toString(),
                tool_id: thisJobInfo.toolId as string,
                step_index: thisJobInfo.stepIndex,
                step_label: thisJobInfo.stepLabel,
            };
            thisMetric.push(metric);
        }
    });
    return thisMetric;
}

function metricToSpecData(
    jobMetrics: AnyMetric[] | undefined,
    metricName: string,
    yTitle: string,
    helpTerm?: string,
    transform?: (param: number) => number
): boxplotData {
    const thisMetric = jobMetrics?.filter((jobMetric) => jobMetric.name == metricName);
    const values = thisMetric?.map((item) => {
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
        helpTerm,
        values,
    };
}

function metricToAggregateData(
    jobMetrics: AnyMetric[] | undefined,
    metricName: string,
    yTitle: string,
    helpTerm?: string,
    transform?: (param: number) => number
): piechartData {
    const thisMetric = jobMetrics?.filter((jobMetric) => jobMetric.name == metricName);
    const aggregateByX: Record<string, number> = {};
    thisMetric?.forEach((item) => {
        let y = parseFloat(item.raw_value);
        if (transform !== undefined) {
            y = transform(y);
        }
        const x = itemToX(item);
        if (!(x in aggregateByX)) {
            aggregateByX[x] = 0;
        }
        if (x in aggregateByX) {
            aggregateByX[x] += y;
        }
    });
    const values = Object.keys(aggregateByX).map((key) => {
        const value = aggregateByX[key];
        return {
            category: key,
            y: value || 0,
        };
    });
    return {
        category_title: attributeToLabel[groupBy.value],
        y_title: yTitle,
        helpTerm,
        values,
    };
}

function transformTime(time: number): number {
    if (timing.value == "minutes") {
        return time / 60;
    } else if (timing.value == "hours") {
        return time / 3600;
    } else {
        return time;
    }
}

const allocatedCoreTime: ComputedRef<DerivedMetric[]> = computed(() => {
    return computeAllocatedCoreTime(jobMetrics.value);
});

const wallclock: ComputedRef<boxplotData> = computed(() => {
    const title = `Runtime (in ${timingInTitles.value})`;
    return metricToSpecData(jobMetrics.value, "runtime_seconds", title, "galaxy.jobs.metrics.walltime", transformTime);
});

const wallclockAggregate: ComputedRef<piechartData> = computed(() => {
    const title = `Runtime (in ${timingInTitles.value})`;
    return metricToAggregateData(
        jobMetrics.value,
        "runtime_seconds",
        title,
        "galaxy.jobs.metrics.walltime",
        transformTime
    );
});

const allocatedCoreTimeSpec: ComputedRef<boxplotData> = computed(() => {
    const title = `Allocated Core Time (in ${timingInTitles.value})`;
    return metricToSpecData(
        allocatedCoreTime.value as AnyMetric[],
        "allocated_core_time",
        title,
        "galaxy.jobs.metrics.allocated_core_time",
        transformTime
    );
});

const allocatedCoreTimeAggregate: ComputedRef<piechartData> = computed(() => {
    const title = `Allocated Core Time (in ${timingInTitles.value})`;
    return metricToAggregateData(
        allocatedCoreTime.value as AnyMetric[],
        "allocated_core_time",
        title,
        "galaxy.jobs.metrics.allocated_core_time",
        transformTime
    );
});

const coresAllocated: ComputedRef<boxplotData> = computed(() => {
    return metricToSpecData(jobMetrics.value, "galaxy_slots", "Cores Allocated", "galaxy.jobs.metrics.cores");
});

const memoryAllocated: ComputedRef<boxplotData> = computed(() => {
    return metricToSpecData(jobMetrics.value, "galaxy_memory_mb", "Memory Allocated (in MB)");
});

const peakMemory: ComputedRef<boxplotData> = computed(() => {
    return metricToSpecData(
        jobMetrics.value,
        "memory.peak",
        "Max memory usage recorded (in MB)",
        undefined,
        (v) => v / 1024 ** 2
    );
});

function itemToPieChartSpec(item: piechartData) {
    const spec: VisualizationSpec = {
        $schema: "https://vega.github.io/schema/vega-lite/v5.json",
        description: "Aggregate data.",
        data: {
            values: item.values!,
        },
        mark: { type: "arc", tooltip: true },
        encoding: {
            theta: { field: "y", type: "quantitative" },
            color: {
                field: "category",
                type: "nominal",
                legend: {
                    type: "symbol",
                    title: "", // should be item.category_title but it doesn't align right so just hide it
                    direction: "vertical",
                    titleAlign: "right",
                    padding: 10,
                    // rowPadding: 3,
                    labelOffset: 40,
                    // symbolOffset: 50,
                    labelLimit: 120,
                    // labelAlign: 'center',
                    columnPadding: 5,
                    // clipHeight: 20,
                    titleOrient: "top",
                },
            },
            tooltip: [
                { field: "category", type: "nominal", title: item.category_title },
                { field: "y", type: "quantitative", title: item.y_title },
            ],
        },
        autosize: {
            type: "fit",
            resize: true,
        },
        width: 400,
        height: 250,
    };
    return spec;
}

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
        encoding: {
            y: {
                field: "y",
                type: "quantitative",
                scale: { zero: false },
                title: item.y_title,
            },
            x: {
                field: "x",
                type: "nominal",
                title: item.x_title,
                axis: {
                    labelAngle: -45,
                    labelAlign: "right",
                },
            },
        },
        layer: [
            {
                mark: { type: "boxplot", opacity: 0.5 },
                width: "container",
            },
            {
                mark: {
                    type: "point",
                    opacity: 0.7,
                },
                encoding: {
                    xOffset: { field: "random_jitter", type: "quantitative", scale: { domain: [-2, 2] } },
                    tooltip: { field: "tooltip", type: "nominal" },
                    href: { field: "url", type: "nominal" },
                    color: { field: "x", type: "nominal", legend: null },
                },
                width: "container",
                height: 350,
            },
        ],
    };
    return spec;
}

const metrics = computed(() => {
    const items = [
        wallclock.value,
        allocatedCoreTimeSpec.value,
        coresAllocated.value,
        memoryAllocated.value,
        peakMemory.value,
    ].filter((item) => item.values?.length);

    return Object.fromEntries(items.map((item) => [item.y_title, { spec: itemToSpec(item), item: item }]));
});

function getTimingInTitle(timing: string): string {
    return timing.charAt(0).toUpperCase() + timing.slice(1);
}

const timingInTitles = computed(() => {
    return getTimingInTitle(timing.value);
});
</script>

<template>
    <div>
        <BContainer>
            <BRow align-h="end" class="mb-2">
                <BButtonGroup>
                    <b-dropdown right :text="'Timing: ' + timingInTitles">
                        <b-dropdown-item @click="timing = 'seconds'">{{ getTimingInTitle("seconds") }}</b-dropdown-item>
                        <b-dropdown-item @click="timing = 'minutes'">{{ getTimingInTitle("minutes") }}</b-dropdown-item>
                        <b-dropdown-item @click="timing = 'hours'">{{ getTimingInTitle("hours") }}</b-dropdown-item>
                    </b-dropdown>
                    <b-dropdown right text="Group By: Tool">
                        <b-dropdown-item @click="groupBy = 'tool_id'">Tool</b-dropdown-item>
                        <b-dropdown-item @click="groupBy = 'step_id'">Workflow Step</b-dropdown-item>
                    </b-dropdown>
                </BButtonGroup>
            </BRow>
            <BRow>
                <BCol v-if="wallclockAggregate && wallclockAggregate.values">
                    <h2 class="h-l truncate text-center">
                        Aggregate
                        <HelpText :for-title="true" uri="galaxy.jobs.metrics.walltime" text="Runtime Time" /> (in
                        {{ timingInTitles }})
                    </h2>
                    <VegaWrapper :spec="itemToPieChartSpec(wallclockAggregate)" />
                </BCol>
                <BCol v-if="allocatedCoreTimeAggregate && allocatedCoreTimeAggregate.values">
                    <h2 class="h-l truncate text-center">
                        Aggregate
                        <HelpText
                            :for-title="true"
                            uri="galaxy.jobs.metrics.allocated_core_time"
                            text="Allocated Core Time" />
                        (in {{ timingInTitles }})
                    </h2>
                    <VegaWrapper :spec="itemToPieChartSpec(allocatedCoreTimeAggregate)" />
                </BCol>
            </BRow>
            <BRow v-for="({ spec, item }, key) in metrics" :key="key">
                <BCol>
                    <h2 class="h-l truncate text-center">
                        <span v-if="item.helpTerm">
                            <HelpText :for-title="true" :uri="item.helpTerm" :text="key" />
                        </span>
                        <span v-else>
                            {{ key }}
                        </span>
                    </h2>
                    <VegaWrapper :spec="spec" />
                </BCol>
            </BRow>
        </BContainer>
    </div>
</template>
