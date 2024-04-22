<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faQuestion } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BDropdown, BDropdownItem, BInputGroup, BInputGroupAppend, BModal } from "bootstrap-vue";
import { capitalize } from "lodash";
import { computed, ref, watch } from "vue";

import { type ValidFilter } from "@/utils/filtering";

library.add(faQuestion);

type FilterType = string | boolean | undefined;
type DatalistItem = { value: string; text: string };

interface Props {
    name: string;
    error?: string;
    filter: ValidFilter<any>;
    filters: {
        [k: string]: FilterType;
    };
    identifier: string;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "change", name: string, value: FilterType): void;
}>();

const propValue = computed<FilterType>(() => props.filters[props.name]);

const localValue = ref<FilterType>(propValue.value);

// datalist refs
const datalist = computed<(DatalistItem[] | string[]) | undefined>(() => props.filter.datalist);
const stringDatalist = computed<string[]>(() => {
    if (datalist.value && typeof datalist.value[0] === "string") {
        return datalist.value as string[];
    }
    return [];
});
const objectDatalist = computed<DatalistItem[]>(() => {
    if (datalist.value && typeof datalist.value[0] !== "string") {
        return datalist.value as DatalistItem[];
    }
    return [];
});

// help modal button refs
const helpToggle = ref(false);
const modalTitle = `${capitalize(props.filter.placeholder)} Help`;
function onHelp(_: string, value: string) {
    helpToggle.value = false;
    localValue.value = value;
}

watch(
    () => localValue.value,
    () => {
        emit("change", props.name, localValue.value);
    }
);
watch(
    () => propValue.value,
    () => {
        localValue.value = propValue.value;
    }
);

const dropDownText = computed<string>(() => {
    if (localValue.value) {
        const stringMatch = stringDatalist.value.find((item) => item === localValue.value);
        const objectMatch = objectDatalist.value.find((item) => item.value === localValue.value);
        if (stringMatch) {
            return stringMatch;
        } else if (objectMatch) {
            return objectMatch.text;
        }
    }
    return "(any)";
});

function setValue(val: string | undefined) {
    localValue.value = val;
}
</script>

<template>
    <div v-if="datalist">
        <small>Filter by {{ props.filter.placeholder }}:</small>
        <BInputGroup :id="`${identifier}-advanced-filter-${props.name}`" class="flex-nowrap">
            <BDropdown
                :text="dropDownText"
                block
                class="w-100"
                menu-class="w-100"
                size="sm"
                boundary="window"
                :toggle-class="props.error ? 'text-danger' : ''">
                <BDropdownItem href="#" @click="setValue(undefined)"><i>(any)</i></BDropdownItem>

                <span v-if="stringDatalist.length > 0">
                    <BDropdownItem
                        v-for="listItem in stringDatalist"
                        :key="listItem"
                        href="#"
                        @click="setValue(listItem)">
                        {{ listItem }}
                    </BDropdownItem>
                </span>
                <span v-else-if="objectDatalist.length > 0">
                    <BDropdownItem
                        v-for="listItem in objectDatalist"
                        :key="listItem.value"
                        href="#"
                        @click="setValue(listItem.value)">
                        {{ listItem.text }}
                    </BDropdownItem>
                </span>
            </BDropdown>
            <BInputGroupAppend>
                <!-- append Help Modal toggle for filter if included -->
                <BButton v-if="props.filter.helpInfo" :title="modalTitle" size="sm" @click="helpToggle = true">
                    <FontAwesomeIcon :icon="faQuestion" />
                </BButton>
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
