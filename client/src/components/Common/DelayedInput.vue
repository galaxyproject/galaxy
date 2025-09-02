<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faAngleDoubleDown, faAngleDoubleUp, faSpinner, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { watchImmediate } from "@vueuse/core";
import { BInputGroup, BInputGroupAppend } from "bootstrap-vue";
import { ref, watch } from "vue";

import localize from "@/utils/localization";

import GFormInput from "../BaseComponents/Form/GFormInput.vue";
import GButton from "../BaseComponents/GButton.vue";

library.add(faAngleDoubleDown, faAngleDoubleUp, faSpinner, faTimes);

interface Props {
    value?: string;
    delay?: number;
    loading?: boolean;
    placeholder?: string;
    showAdvanced?: boolean;
    enableAdvanced?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    value: "",
    delay: 1000,
    loading: false,
    placeholder: "Enter your search term here.",
    showAdvanced: false,
    enableAdvanced: false,
});

const emit = defineEmits<{
    (e: "input", value: string): void;
    (e: "change", value: string): void;
    (e: "onToggle", showAdvanced: boolean): void;
}>();

const queryInput = ref<string>();
const queryTimer = ref<ReturnType<typeof setTimeout> | null>(null);
const titleClear = ref("Clear Search (esc)");
const titleAdvanced = ref("Toggle Advanced Search");
const toolInput = ref<HTMLInputElement | null>(null);

function clearTimer() {
    if (queryTimer.value) {
        clearTimeout(queryTimer.value);
    }
}

function delayQuery(query: string) {
    clearTimer();
    if (query) {
        queryTimer.value = setTimeout(() => {
            setQuery(query);
        }, props.delay);
    } else {
        setQuery(query);
    }
}

function setQuery(queryNew: string) {
    emit("input", queryNew);
    emit("change", queryNew);
}

watch(
    () => queryInput.value,
    () => delayQuery(queryInput.value ?? ""),
);

function clearBox() {
    queryInput.value = "";
    toolInput.value?.focus();
}

function onToggle() {
    emit("onToggle", !props.showAdvanced);
}

watchImmediate(
    () => props.value,
    (newQuery) => {
        queryInput.value = newQuery;
    },
);
</script>

<template>
    <BInputGroup>
        <GFormInput
            ref="toolInput"
            v-model="queryInput"
            class="search-query form-control"
            autocomplete="off"
            :placeholder="placeholder"
            data-description="filter text input"
            @keydown.esc="clearBox" />

        <BInputGroupAppend>
            <GButton
                v-if="enableAdvanced"
                tooltip
                aria-haspopup="true"
                size="small"
                :pressed="showAdvanced"
                :color="showAdvanced ? 'blue' : 'grey'"
                :title="localize(titleAdvanced)"
                data-description="toggle advanced search"
                @click="onToggle">
                <FontAwesomeIcon v-if="showAdvanced" fixed-width :icon="faAngleDoubleUp" />
                <FontAwesomeIcon v-else fixed-width :icon="faAngleDoubleDown" />
            </GButton>

            <GButton
                tooltip
                aria-haspopup="true"
                class="search-clear"
                size="small"
                :title="localize(titleClear)"
                data-description="reset query"
                @click="clearBox">
                <FontAwesomeIcon v-if="loading" fixed-width :icon="faSpinner" spin />
                <FontAwesomeIcon v-else fixed-width :icon="faTimes" />
            </GButton>
        </BInputGroupAppend>
    </BInputGroup>
</template>
