<script setup lang="ts">
import { BAlert, BButtonGroup, BCol, BContainer, BDropdown, BDropdownItem, BRow } from "bootstrap-vue";
import type { VisualizationSpec } from "vega-embed";
import { computed, ref, watch } from "vue";
import { type ComputedRef } from "vue";

import { type components, GalaxyApi } from "@/api";
import { getAppRoot } from "@/onload/loadConfig";
import { errorMessageAsString } from "@/utils/simple-error";
import { capitalizeFirstLetter } from "@/utils/strings";

import LoadingSpan from "../LoadingSpan.vue";
import HelpText from "@/components/Help/HelpText.vue";

const VegaWrapper = () => import("@/components/Common/VegaWrapper.vue");

interface Props {
    invocationId: string;
    notTerminal?: boolean;
}
const props = defineProps<Props>();

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

watch(
    () => props.invocationId,
    () => fetchMetrics(),
    { immediate: true }
);

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

interface barChartData {
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
            step_index: item.step_index,
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
): barChartData {
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
            const newX = aggregateByX[x] || 0 + y;
            aggregateByX[x] = newX;
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

const wallclockAggregate: ComputedRef<barChartData> = computed(() => {
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

const allocatedCoreTimeAggregate: ComputedRef<barChartData> = computed(() => {
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

function itemToBarChartSpec(item: barChartData) {
    const spec: VisualizationSpec = {
        $schema: "https://vega.github.io/schema/vega-lite/v5.json",
        description: "Aggregate data.",
        data: {
            values: item.values!,
        },
        mark: { type: "bar", tooltip: true },
        encoding: {
            order: { field: "y", type: "quantitative", sort: "descending" },
            y: { field: "y", type: "quantitative", title: item.y_title },
            color: {
                field: "category",
                type: "nominal",
                sort: { field: "y", order: "descending" },
                legend: {
                    type: "symbol",
                    title: item.category_title,
                    labelExpr: "truncate(replace(datum.label, /(^\\d+: )?.*\\/repos\\/[^/]+\\/[^/]+\\//, '$1'), 32)",
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
            {
                calculate: "parseInt(datum.step_index)",
                as: "x_numeric",
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
                type: "ordinal",
                title: item.x_title,
                axis: {
                    labelAngle: -45,
                    labelAlign: "right",
                    // 35 seems to be the maximum amount of characters we can display
                    labelExpr: "truncate(replace(datum.label, /(^\\d+: )?.*\\/repos\\/[^/]+\\/[^/]+\\//, '$1'), 35)",
                },
                sort: {
                    field: "step_index",
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

const timingInTitles = computed(() => {
    return capitalizeFirstLetter(timing.value);
});

const groupByInTitles = computed(() => {
    return attributeToLabel[groupBy.value];
});
</script>

<template>
    <div>
        <BAlert v-if="props.notTerminal" variant="warning" show>
            <LoadingSpan message="Metrics will update and change as the workflow progresses." />
        </BAlert>
        <BContainer>
            <BRow align-h="end" class="mb-2">
                <BButtonGroup>
                    <BDropdown variant="outline-primary" size="sm" right :text="'Timing: ' + timingInTitles">
                        <BDropdownItem @click="timing = 'seconds'">
                            {{ capitalizeFirstLetter("seconds") }}
                        </BDropdownItem>
                        <BDropdownItem @click="timing = 'minutes'">
                            {{ capitalizeFirstLetter("minutes") }}
                        </BDropdownItem>
                        <BDropdownItem @click="timing = 'hours'">
                            {{ capitalizeFirstLetter("hours") }}
                        </BDropdownItem>
                    </BDropdown>
                    <BDropdown variant="outline-primary" size="sm" right :text="'Group By: ' + groupByInTitles">
                        <BDropdownItem @click="groupBy = 'tool_id'">Tool</BDropdownItem>
                        <BDropdownItem @click="groupBy = 'step_id'">Workflow Step</BDropdownItem>
                    </BDropdown>
                </BButtonGroup>
            </BRow>
            <BRow>
                <BCol v-if="wallclockAggregate && wallclockAggregate.values" class="text-center">
                    <Heading class="h3 truncate text-center">
                        Aggregate
                        <HelpText :for-title="true" uri="galaxy.jobs.metrics.walltime" text="Runtime Time" /> (in
                        {{ timingInTitles }})
                    </Heading>
                    <VegaWrapper :spec="itemToBarChartSpec(wallclockAggregate)" :fill-width="false" />
                </BCol>
                <BCol v-if="allocatedCoreTimeAggregate && allocatedCoreTimeAggregate.values" class="text-center">
                    <Heading class="h3 truncate text-center">
                        Aggregate
                        <HelpText
                            :for-title="true"
                            uri="galaxy.jobs.metrics.allocated_core_time"
                            text="Allocated Core Time" />
                        (in {{ timingInTitles }})
                    </Heading>
                    <VegaWrapper :spec="itemToBarChartSpec(allocatedCoreTimeAggregate)" :fill-width="false" />
                </BCol>
            </BRow>
            <BRow v-for="({ spec, item }, key) in metrics" :key="key">
                <BCol>
                    <Heading class="h3 truncate text-center">
                        <span v-if="item.helpTerm">
                            <HelpText :for-title="true" :uri="item.helpTerm" :text="`${key}`" />
                        </span>
                        <span v-else>
                            {{ key }}
                        </span>
                    </Heading>
                    <VegaWrapper :spec="spec" />
                </BCol>
            </BRow>
        </BContainer>
    </div>
</template>
