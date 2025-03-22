<script setup>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faExclamationCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";

import { findExtension } from "./utils";

import UploadExtension from "./UploadExtension.vue";
import UploadSelect from "./UploadSelect.vue";
import Popper from "@/components/Popper/Popper.vue";

library.add(faExclamationCircle);

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
            what="文件类型"
            placeholder="选择类型"
            :warn="warnText ? true : false"
            @input="(newValue) => emit('input', newValue)" />
        <Popper v-if="warnText" placement="bottom" mode="light">
            <template v-slot:reference>
                <FontAwesomeIcon icon="fa-exclamation-circle" class="selection-warning" />
            </template>
            <div class="p-2">
                {{ warnText }}
            </div>
        </Popper>
        <UploadExtension :extension="value" :list-extensions="listExtensions" />
    </span>
</template>

<style lang="scss" scoped>
@import "theme/blue.scss";
.selection-warning {
    color: $brand-warning;
}
</style>
