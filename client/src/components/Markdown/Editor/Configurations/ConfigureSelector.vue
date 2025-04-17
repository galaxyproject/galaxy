<template>
    <SelectionField
        :do-query="hasLabels ? doQuery : undefined"
        :object-id="objectId"
        :object-name="objectName"
        :object-title="objectTitle"
        :object-type="objectType"
        @change="$emit('change', $event)"
    />
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { WorkflowLabel } from "@/components/Markdown/Editor/types";

import { getRequiredLabels } from "@/components/Markdown/Utilities/requirements";
import SelectionField from "@/components/SelectionField/SelectionField.vue";

export interface OptionType {
    id: string;
    name: string;
}
export type ApiResponse = Array<any> | undefined;

const props = withDefaults(
    defineProps<{
        labels?: Array<WorkflowLabel>;
        objectId?: string;
        objectName?: string;
        objectTitle?: string;
        objectType: string;
    }>(),
    {
        labels: undefined,
        objectId: "",
        objectName: "...",
        objectTitle: undefined,
    }
);

defineEmits<{
    (e: "change", newValue: OptionType): void;
}>();

const hasLabels = computed(() => props.labels !== undefined);

const mappedLabels = computed(() =>
    props.labels
        ?.filter((workflowLabel) => getRequiredLabels(props.objectType).includes(workflowLabel.type))
        .map((workflowLabel) => ({
            id: workflowLabel.label,
            name: `${workflowLabel.label} (${workflowLabel.type})`,
            label: {
                invocation_id: "",
                [workflowLabel.type]: workflowLabel.label,
            },
        }))
);

async function doQuery(): Promise<any> {
    return mappedLabels.value;
}
</script>
