<script setup lang="ts">
import { computed } from "vue";
import ActivityItem from "components/ActivityBar/ActivityItem.vue";

interface Workflow {
    id: string;
    name: string;
}

export interface Props {
    workflows: Workflow[];
}

const props = withDefaults(defineProps<Props>(), {});

const activityOptions = computed(() => {
    return [
        {
            name: "All workflows",
            value: `/workflows/list`,
        },
        ...props.workflows.map((workflow) => {
            return {
                name: workflow.name,
                value: `/workflows/run?id=${workflow.id}`,
            };
        }),
    ];
});

const hasWorkflows = computed(() => {
    return props.workflows && props.workflows.length > 0;
});
</script>

<template>
    <ActivityItem
        v-if="hasWorkflows"
        id="activity-workflow"
        title="Workflow"
        tooltip="Select a Workflow:"
        icon="sitemap"
        :options="activityOptions" />
</template>
