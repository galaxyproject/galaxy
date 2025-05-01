<script setup lang="ts">
import { type WorkflowLabel } from "./labels";

interface LabelSelectorProps {
    hasLabels: boolean;
    labels: WorkflowLabel[];
    value?: WorkflowLabel;
    labelTitle: string;
}

const props = withDefaults(defineProps<LabelSelectorProps>(), {
    value: undefined,
});

const emit = defineEmits<{
    (e: "input", value: WorkflowLabel | undefined): void;
}>();

function update(index: number) {
    const label: WorkflowLabel | undefined = props.labels[index] || undefined;
    emit("input", label);
}
</script>

<template>
    <div>
        <h2 class="mb-3 h-text">选择 {{ labelTitle }} 标签：</h2>
        <div v-if="hasLabels">
            <b-form-radio
                v-for="(label, index) in labels"
                :key="index"
                class="my-2"
                name="labels"
                :value="index"
                @change="update">
                {{ label.label }}
            </b-form-radio>
        </div>
        <b-alert v-else show variant="info"> 未找到标签。请在工作流编辑器中指定标签。 </b-alert>
        <p class="mt-3 text-muted">
            您可以通过在工作流编辑器中选择一个步骤，然后在步骤表单中编辑相应的标签字段来添加新标签。
        </p>
    </div>
</template>
