<script setup lang="ts">
import { BButton, BForm, BFormGroup, BFormInput } from "bootstrap-vue";
import { computed, ref } from "vue";

interface Props {
    queryTrsUrl?: string;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "onImport", url: string): void;
}>();

const trsUrl = ref(props.queryTrsUrl);

const isImportDisabled = computed(() => {
    return !trsUrl.value;
});

const importTooltip = computed(() => {
    return isImportDisabled.value ? "您必须提供一个 TRS URL。" : "从 TRS URL 导入工作流";
});

function submit(ev: SubmitEvent) {
    ev.preventDefault();

    if (trsUrl.value) {
        emit("onImport", trsUrl.value);
    }
}

// Automatically trigger the import if the TRS URL was provided as a query param
if (trsUrl.value) {
    emit("onImport", trsUrl.value);
}
</script>

<template>
    <BForm class="mt-4" @submit="submit">
        <h2 class="h-sm">或者，直接提供一个 TRS URL</h2>

        <BFormGroup label="TRS URL:" label-class="font-weight-bold">
            <BFormInput id="trs-import-url-input" v-model="trsUrl" aria-label="TRS URL" type="url" />
            如果工作流可通过 TRS URL 访问，请在上方输入 URL 并点击导入。
        </BFormGroup>

        <BButton
            id="trs-url-import-button"
            type="submit"
            :disabled="isImportDisabled"
            :title="importTooltip"
            variant="primary">
            导入工作流
        </BButton>
    </BForm>
</template>
