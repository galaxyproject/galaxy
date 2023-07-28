<script setup>
import { computed } from "vue";
import Multiselect from "vue-multiselect";

const props = defineProps({
    disabled: Boolean,
    options: Array,
    placeholder: String,
    value: String,
});

const emit = defineEmits();

const currentValue = computed({
    get: () => props.options.find((option) => option.id === props.value),
    set(newValue) {
        emit("input", newValue.id);
    },
});
</script>

<template>
    <Multiselect
        class="upload-settings-select"
        v-model="currentValue"
        deselect-label=""
        label="text"
        :options="options"
        :placeholder="placeholder"
        select-label=""
        track-by="id" />
</template>

<style>
.upload-settings-select.multiselect {
    display: inline-block;
    width: 150px;
    .multiselect__select {
        height: 15px;
        width: 22px;
        padding: 0px;
        top: 5px;
    }
    .multiselect__single {
        background: transparent;
        margin: 0px;
        height: 18px;
        overflow: hidden;
    }
    .multiselect__tags {
        background: transparent;
        border-radius: 0.25rem;
        height: 22px;
        min-height: unset;
        padding: 0px;
        margin: 0px;
        .multiselect__single {
            width: 135px;
        }
    }
    .multiselect__content-wrapper {
        width: 300px;
    }
}
</style>
