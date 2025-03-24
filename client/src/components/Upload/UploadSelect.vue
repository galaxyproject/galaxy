<script setup>
import { computed } from "vue";
import Multiselect from "vue-multiselect";

import { uid } from "@/utils/utils";

const props = defineProps({
    id: {
        type: String,
        default: `upload-settings-select-${uid()}`,
    },
    disabled: {
        type: Boolean,
        default: false,
    },
    options: {
        type: Array,
        required: true,
    },
    placeholder: {
        type: String,
        default: "",
    },
    value: {
        type: String,
        default: null,
    },
    what: {
        type: String,
        default: null,
    },
    searchable: {
        type: Boolean,
        default: true,
    },
    warn: {
        type: Boolean,
        default: false,
    },
});

const emit = defineEmits(["input"]);

const currentValue = computed({
    get: () => props.options.find((option) => option.id === props.value),
    set(newValue) {
        emit("input", newValue.id);
    },
});
</script>

<template>
    <Multiselect
        :id="id"
        v-model="currentValue"
        class="upload-settings-select rounded"
        deselect-label=""
        :disabled="disabled"
        :searchable="searchable"
        label="text"
        :options="options"
        :placeholder="placeholder"
        select-label=""
        selected-label=""
        track-by="id">
        <span slot="noResult" v-localize>未找到匹配的{{ what }}。</span>
        <span slot="singleLabel" slot-scope="{ option }" :class="{ 'selection-warning': warn }">
            {{ option.text }}
        </span>
    </Multiselect>
</template>

<style lang="scss">
@import "theme/blue.scss";
.upload-settings-select.multiselect {
    display: inline-block;
    min-height: unset;
    width: 150px;
    .selection-warning {
        color: $brand-warning;
    }
    .multiselect__content-wrapper {
        .multiselect__content {
            width: inherit;
            word-break: break-all;
        }
    }
    .multiselect__select {
        height: 22px;
        padding: 0px;
        background: transparent;
        width: 20px;
    }
    .multiselect__tags {
        border-radius: 0.25rem;
        height: 22px;
        margin: 0px;
        padding: 0px;
        .multiselect__single {
            text-overflow: ellipsis;
            white-space: nowrap;
            width: 130px;
        }
    }
}
</style>
