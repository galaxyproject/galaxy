<script setup>
import { computed, ref } from "vue";
import Multiselect from "vue-multiselect";

import { rankBySearch } from "@/utils/searchRanking";
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

const searchQuery = ref("");

/** Options filtered by the search query, with exact and prefix matches listed first. */
const rankedOptions = computed(() => rankBySearch(props.options, searchQuery.value, ["text", "id"]));

function onSearchChange(query) {
    searchQuery.value = query;
}

const currentValue = computed({
    get: () => props.options.find((option) => option.id === props.value),
    set(newValue) {
        if (newValue) {
            emit("input", newValue.id);
        }
    },
});
</script>

<template>
    <Multiselect
        :id="id"
        v-model="currentValue"
        :allow-empty="false"
        class="upload-settings-select rounded"
        deselect-label=""
        :disabled="disabled"
        :searchable="searchable"
        :internal-search="false"
        label="text"
        :options="rankedOptions"
        :placeholder="placeholder"
        select-label=""
        selected-label=""
        track-by="id"
        @search-change="onSearchChange">
        <span slot="noResult" v-localize>No matching {{ what }}s found.</span>
        <span slot="singleLabel" slot-scope="{ option }" :class="{ 'selection-warning': warn }">
            {{ option.text }}
        </span>
    </Multiselect>
</template>

<style lang="scss">
@import "@/style/scss/theme/blue.scss";
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
