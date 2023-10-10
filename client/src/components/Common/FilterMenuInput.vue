<script setup lang="ts">
import { capitalize } from "lodash";
import { computed, type PropType, ref, watch } from "vue";

import { ValidFilter } from "@/utils/filtering";

const props = defineProps({
    name: { type: String, required: true },
    filter: { type: Object as PropType<ValidFilter<any>>, required: true },
    filters: { type: Object, required: true },
    error: { type: Object, default: null },
    identifier: { type: String, required: true },
});

const emit = defineEmits<{
    (e: "change", name: string, value: string): void;
    (e: "on-enter"): void;
    (e: "on-esc"): void;
}>();

const propValue = computed(() => props.filters[props.name]);

const localValue = ref(propValue.value);

const helpToggle = ref(false);
const modalTitle = `${capitalize(props.filter.placeholder)} Help`;

watch(
    () => localValue.value,
    (newFilter: string) => {
        emit("change", props.name, newFilter);
    }
);
watch(
    () => propValue.value,
    (newFilter: string) => {
        localValue.value = newFilter;
    }
);

function hasError(field: string) {
    if (props.error && props.error.index == field) {
        return props.error.typeError || props.error.msg;
    }
    return "";
}

function onHelp(_: string, value: string) {
    helpToggle.value = false;
    localValue.value = value;
}
</script>

<template>
    <div>
        <small>Filter by {{ props.filter.placeholder }}:</small>
        <b-input-group>
            <b-form-input
                :id="`${identifier}-advanced-filter-${props.name}`"
                ref="filterMenuInput"
                v-model="localValue"
                v-b-tooltip.focus.v-danger="hasError(props.name)"
                size="sm"
                :state="hasError(props.name) ? false : null"
                :placeholder="`any ${props.filter.placeholder}`"
                :list="props.filter.datalist ? `${identifier}-${props.name}-selectList` : null"
                @keyup.enter="emit('on-enter')"
                @keyup.esc="emit('on-esc')" />
            <b-form-datalist
                v-if="props.filter.datalist"
                :id="`${identifier}-${props.name}-selectList`"
                :options="props.filter.datalist"></b-form-datalist>
            <!-- append Help Modal for filter if included or/and datepciker if type: Date -->
            <b-input-group-append>
                <b-button v-if="props.filter.helpInfo" :title="modalTitle" size="sm" @click="helpToggle = true">
                    <icon icon="question" />
                </b-button>
                <b-form-datepicker
                    v-if="props.filter.type == Date"
                    v-model="localValue"
                    reset-button
                    button-only
                    size="sm" />
            </b-input-group-append>
        </b-input-group>
        <!-- if a filter has help component, place it within a modal -->
        <span v-if="props.filter.helpInfo">
            <b-modal v-model="helpToggle" :title="modalTitle" ok-only>
                <component
                    :is="props.filter.helpInfo"
                    v-if="typeof props.filter.helpInfo == 'object'"
                    @set-filter="onHelp" />
                <div v-else-if="typeof props.filter.helpInfo == 'string'">
                    <p>{{ props.filter.helpInfo }}</p>
                </div>
            </b-modal>
        </span>
    </div>
</template>
