<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faAngleDoubleDown, faAngleDoubleUp, faSpinner, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { watchImmediate } from "@vueuse/core";
import { BButton, BFormInput, BInputGroup, BInputGroupAppend } from "bootstrap-vue";
import { ref, watch } from "vue";

import localize from "@/utils/localization";

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
    placeholder: "输入你要搜索的内容.",
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
const titleClear = ref("清除搜索 (esc)");
const titleAdvanced = ref("切换高级搜索");
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
    () => delayQuery(queryInput.value ?? "")
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
    }
);
</script>

<template>
    <BInputGroup>
        <BFormInput
            ref="toolInput"
            v-model="queryInput"
            class="search-query"
            size="sm"
            autocomplete="off"
            :placeholder="placeholder"
            data-description="过滤文本输入框"
            @keydown.esc="clearBox" />

        <BInputGroupAppend>
            <BButton
                v-if="enableAdvanced"
                v-b-tooltip.hover.bottom.noninteractive
                aria-haspopup="true"
                size="sm"
                :pressed="showAdvanced"
                :variant="showAdvanced ? 'info' : 'secondary'"
                :title="localize(titleAdvanced)"
                data-description="切换高级搜索"
                @click="onToggle">
                <FontAwesomeIcon v-if="showAdvanced" fixed-width :icon="faAngleDoubleUp" />
                <FontAwesomeIcon v-else fixed-width :icon="faAngleDoubleDown" />
            </BButton>

            <BButton
                v-b-tooltip.hover.bottom.noninteractive
                aria-haspopup="true"
                class="search-clear"
                size="sm"
                :title="localize(titleClear)"
                data-description="重置查询"
                @click="clearBox">
                <FontAwesomeIcon v-if="loading" fixed-width :icon="faSpinner" spin />
                <FontAwesomeIcon v-else fixed-width :icon="faTimes" />
            </BButton>
        </BInputGroupAppend>
    </BInputGroup>
</template>