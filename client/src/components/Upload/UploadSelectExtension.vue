<script setup>
import { computed } from "vue";

import { findExtension } from "./utils";

import UploadDatatypeWarning from "./UploadDatatypeWarning.vue";
import UploadExtension from "./UploadExtension.vue";
import UploadSelect from "./UploadSelect.vue";

const props = defineProps({
    disabled: {
        type: Boolean,
        default: false,
    },
    listExtensions: {
        type: Array,
        required: true,
    },
    value: {
        type: String,
        default: null,
    },
});

const emit = defineEmits(["input"]);

const details = computed(() => findExtension(props.listExtensions, props.value));
const warnText = computed(() => details.value.upload_warning);
</script>

<template>
    <span title="">
        <UploadSelect
            :value="value"
            :disabled="disabled"
            :options="listExtensions"
            what="file type"
            placeholder="Select Type"
            :warn="warnText ? true : false"
            @input="(newValue) => emit('input', newValue)">
            <template v-slot:option="{ option }">
                {{ option.text }}
                <UploadDatatypeWarning :message="option.upload_warning" />
            </template>
        </UploadSelect>
        <UploadExtension :extension="value" :list-extensions="listExtensions" />
        <span role="status">
            <UploadDatatypeWarning :message="warnText" />
        </span>
    </span>
</template>
