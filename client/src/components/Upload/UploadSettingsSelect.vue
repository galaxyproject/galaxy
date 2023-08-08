<script setup>
import { computed } from "vue";
import Multiselect from "vue-multiselect";

const props = defineProps({
    disabled: Boolean,
    options: Array,
    placeholder: String,
    value: String,
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
        v-model="currentValue"
        class="upload-settings-select rounded"
        deselect-label=""
        :disabled="disabled"
        label="text"
        :options="options"
        :placeholder="placeholder"
        select-label=""
        selected-label=""
        track-by="id" />
</template>

<style lang="scss">
@import "theme/blue.scss";
.upload-settings-select.multiselect {
    display: inline-block;
    min-height: unset;
    width: 150px;
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
            width: 130px;
        }
    }
}
</style>
