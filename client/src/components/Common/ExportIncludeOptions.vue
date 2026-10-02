<script setup lang="ts">
import { BFormCheckbox, BFormGroup } from "bootstrap-vue";

interface Props {
    includeFiles: boolean;
    includeDeleted: boolean;
    includeHidden: boolean;
    disabled?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    disabled: false,
});

const emit = defineEmits<{
    (e: "update:include-files", value: boolean): void;
    (e: "update:include-deleted", value: boolean): void;
    (e: "update:include-hidden", value: boolean): void;
}>();
</script>

<template>
    <BFormGroup label="Dataset files included in the export:">
        <BFormCheckbox
            :checked="props.includeFiles"
            :disabled="props.disabled"
            switch
            data-test-id="include-files-checkbox"
            @change="emit('update:include-files', $event)">
            Include Active Files
        </BFormCheckbox>

        <BFormCheckbox
            :checked="props.includeDeleted"
            :disabled="props.disabled"
            switch
            data-test-id="include-deleted-checkbox"
            @change="emit('update:include-deleted', $event)">
            Include Deleted (not purged)
        </BFormCheckbox>

        <BFormCheckbox
            :checked="props.includeHidden"
            :disabled="props.disabled"
            switch
            data-test-id="include-hidden-checkbox"
            @change="emit('update:include-hidden', $event)">
            Include Hidden
        </BFormCheckbox>
    </BFormGroup>
</template>
