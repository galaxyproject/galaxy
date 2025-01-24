<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faQuestion } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import {
    BButton,
    BFormDatalist,
    BFormDatepicker,
    BFormInput,
    BInputGroup,
    BInputGroupAppend,
    BModal,
} from "bootstrap-vue";
import { capitalize } from "lodash";
import { computed, ref, watch } from "vue";

import { type ValidFilter } from "@/utils/filtering";

library.add(faQuestion);

type FilterType = string | boolean | undefined;

interface Props {
    name: string;
    identifier: any;
    error?: string;
    filter: ValidFilter<any>;
    filters: {
        [k: string]: FilterType;
    };
    disabled?: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "change", name: string, value: FilterType): void;
    (e: "on-enter"): void;
    (e: "on-esc"): void;
}>();

const propValue = computed(() => props.filters[props.name]);

const localValue = ref(propValue.value);

const helpToggle = ref(false);
const modalTitle = `${capitalize(props.filter.placeholder)} Help`;

function onHelp(_: string, value: string) {
    helpToggle.value = false;

    if (!props.disabled) {
        localValue.value = value;
    }
}

watch(
    () => localValue.value,
    (newFilter) => {
        emit("change", props.name, newFilter);
    },
    { immediate: true }
);

watch(
    () => propValue.value,
    (newFilter) => {
        localValue.value = newFilter;
    }
);
</script>

<template>
    <div>
        <small>Filter by {{ props.filter.placeholder }}:</small>

        <BInputGroup>
            <BFormInput
                :id="`${identifier}-advanced-filter-${props.name}`"
                ref="filterMenuInput"
                v-model="localValue"
                v-b-tooltip.focus.v-danger="props.error"
                class="mw-100"
                size="sm"
                :state="props.error ? false : null"
                :placeholder="`any ${props.filter.placeholder}`"
                :disabled="props.disabled"
                :list="props.filter.datalist ? `${identifier}-${props.name}-selectList` : null"
                @keyup.enter="emit('on-enter')"
                @keyup.esc="emit('on-esc')" />

            <BFormDatalist
                v-if="props.filter.datalist"
                :id="`${identifier}-${props.name}-selectList`"
                :options="props.filter.datalist" />

            <!-- append Help Modal for filter if included or/and datepciker if type: Date -->
            <BInputGroupAppend>
                <BButton v-if="props.filter.helpInfo" :title="modalTitle" size="sm" @click="helpToggle = true">
                    <FontAwesomeIcon :icon="faQuestion" />
                </BButton>

                <BFormDatepicker
                    v-if="props.filter.type == Date"
                    v-model="localValue"
                    reset-button
                    button-only
                    :disabled="props.disabled"
                    size="sm" />
            </BInputGroupAppend>
        </BInputGroup>

        <!-- if a filter has help component, place it within a modal -->
        <span v-if="props.filter.helpInfo">
            <BModal v-model="helpToggle" :title="modalTitle" ok-only>
                <component
                    :is="props.filter.helpInfo"
                    v-if="typeof props.filter.helpInfo == 'object'"
                    @set-filter="onHelp" />
                <div v-else-if="typeof props.filter.helpInfo == 'string'">
                    <p>{{ props.filter.helpInfo }}</p>
                </div>
            </BModal>
        </span>
    </div>
</template>
