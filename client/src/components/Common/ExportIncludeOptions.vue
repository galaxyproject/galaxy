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
    (e: "update:includeFiles", value: boolean): void;
    (e: "update:includeDeleted", value: boolean): void;
    (e: "update:includeHidden", value: boolean): void;
}>();
</script>

<template>
    <BFormGroup label="Dataset files included in the export:">
        <BFormCheckbox
            :checked="props.includeFiles"
            :disabled="props.disabled"
            switch
            data-test-id="include-files-checkbox"
            @change="emit('update:includeFiles', $event)">
            Include Active Files
        </BFormCheckbox>

        <BFormCheckbox
            :checked="props.includeDeleted"
            :disabled="props.disabled"
            switch
            data-test-id="include-deleted-checkbox"
            @change="emit('update:includeDeleted', $event)">
            Include Deleted (not purged)
        </BFormCheckbox>

        <BFormCheckbox
            :checked="props.includeHidden"
            :disabled="props.disabled"
            switch
            data-test-id="include-hidden-checkbox"
            @change="emit('update:includeHidden', $event)">
            Include Hidden
        </BFormCheckbox>
    </BFormGroup>
</template>
