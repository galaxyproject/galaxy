<script setup>
import { faExclamationCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";

import { findExtension } from "./utils";

import UploadExtension from "./UploadExtension.vue";
import UploadSelect from "./UploadSelect.vue";
import Popper from "@/components/Popper/Popper.vue";

const props = defineProps({
    disabled: {
        type: Boolean,
        default: false,
    },
    listExtensions: {
        type: Array,
        required: true,
    },
    modelValue: {
        type: String,
        default: null,
    },
});

const emit = defineEmits(["update:modelValue"]);

const details = computed(() => findExtension(props.listExtensions, props.modelValue));
const warnText = computed(() => details.value.upload_warning);
</script>

<template>
    <span title="">
        <UploadSelect
            :model-value="modelValue"
            :disabled="disabled"
            :options="listExtensions"
            what="file type"
            placeholder="Select Type"
            :warn="warnText ? true : false"
            @update:model-value="(newValue) => emit('update:modelValue', newValue)" />
        <Popper v-if="warnText" placement="bottom" mode="light">
            <template v-slot:reference>
                <FontAwesomeIcon :icon="faExclamationCircle" class="selection-warning" />
            </template>
            <div class="p-2">
                {{ warnText }}
            </div>
        </Popper>
        <UploadExtension :extension="modelValue" :list-extensions="listExtensions" />
    </span>
</template>

<style lang="scss" scoped>
@import "@/style/scss/theme/blue.scss";
.selection-warning {
    color: $brand-warning;
}
</style>
