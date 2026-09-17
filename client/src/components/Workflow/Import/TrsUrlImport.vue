<script setup lang="ts">
import { BForm, BFormGroup, BFormInput } from "bootstrap-vue";
import { computed, ref, watch } from "vue";

interface Props {
    queryTrsUrl?: string;
}

const props = withDefaults(defineProps<Props>(), {
    queryTrsUrl: "",
});

const emit = defineEmits<{
    (e: "onImport", url: string): void;
    (e: "input-valid", valid: boolean): void;
}>();

const trsUrl = ref(props.queryTrsUrl);

// Validation state for wizard mode
const isValid = computed(() => {
    return trsUrl.value !== null && trsUrl.value !== undefined && trsUrl.value.length > 0;
});

watch(
    isValid,
    (newValue) => {
        emit("input-valid", newValue);
    },
    { immediate: true },
);

function submit(ev: SubmitEvent) {
    ev.preventDefault();

    if (trsUrl.value) {
        emit("onImport", trsUrl.value);
    }
}

// Expose method for wizard submit
function triggerImport() {
    if (trsUrl.value) {
        emit("onImport", trsUrl.value);
    }
}

defineExpose({ triggerImport });
</script>

<template>
    <BForm class="mt-4" @submit="submit">
        <BFormGroup label="TRS URL:" label-class="font-weight-bold">
            <BFormInput id="trs-import-url-input" v-model="trsUrl" aria-label="TRS URL" type="url" />
            If the workflow is accessible via a TRS URL, enter the URL above and click Import.
        </BFormGroup>
    </BForm>
</template>
