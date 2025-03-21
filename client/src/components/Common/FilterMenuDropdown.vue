<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faQuestion } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BDropdown, BDropdownItem, BInputGroup, BInputGroupAppend, BModal } from "bootstrap-vue";
import { capitalize } from "lodash";
import { computed, onMounted, ref, watch } from "vue";

import { fetchCurrentUserQuotaUsages, type QuotaUsage } from "@/api/users";
import { type FilterType, type ValidFilter } from "@/utils/filtering";
import { errorMessageAsString } from "@/utils/simple-error";

import QuotaUsageBar from "@/components/User/DiskUsage/Quota/QuotaUsageBar.vue";

library.add(faQuestion);

type FilterValue = QuotaUsage | string | boolean | undefined;

type DatalistItem = { value: string; text: string };

interface Props {
    type?: FilterType;
    name: string;
    error?: string;
    filter: ValidFilter<any>;
    filters: {
        [k: string]: FilterValue;
    };
    identifier: string;
    disabled?: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "change", name: string, value: FilterValue): void;
}>();

const propValue = computed<FilterValue>(() => props.filters[props.name]);

const localValue = ref<FilterValue>(propValue.value);

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
const modalTitle = `${capitalize(props.filter.placeholder)} 帮助`;
function onHelp(_: string, value: string) {
    helpToggle.value = false;
    if (!props.disabled) {
        localValue.value = value;
    }
}

// Quota Source refs and operations
const quotaUsages = ref<QuotaUsage[]>([]);
const errorMessage = ref<string>();
async function loadQuotaUsages() {
    try {
        quotaUsages.value = await fetchCurrentUserQuotaUsages();

        // if the propValue is a string, find the corresponding QuotaUsage object and update the localValue
        if (propValue.value && typeof propValue.value === "string") {
            localValue.value = quotaUsages.value.find(
                (quotaUsage) => props.filter.handler.converter!(quotaUsage) === propValue.value
            );
        }
    } catch (e) {
        errorMessage.value = errorMessageAsString(e);
    }
}

const hasMultipleQuotaSources = computed<boolean>(() => {
    return !!(quotaUsages.value && quotaUsages.value.length > 1);
});

onMounted(async () => {
    if (props.type === "QuotaSource") {
        await loadQuotaUsages();
    }
});

function isQuotaUsage(value: FilterValue): value is QuotaUsage {
    return !!(value && value instanceof Object && "rawSourceLabel" in value);
}

const dropDownText = computed<string>(() => {
    if (props.type === "QuotaSource" && isQuotaUsage(localValue.value)) {
        return localValue.value.sourceLabel;
    }
    if (localValue.value) {
        const stringMatch = stringDatalist.value.find((item) => item === localValue.value);
        const objectMatch = objectDatalist.value.find((item) => item.value === localValue.value);
        if (stringMatch) {
            return stringMatch;
        } else if (objectMatch) {
            return objectMatch.text;
        }
    }
    return "(任何)";
});

function setValue(val: FilterValue) {
    localValue.value = val;
}
</script>

<template>
    <div v-if="datalist || hasMultipleQuotaSources">
        <small>通过 {{ props.filter.placeholder }} 筛选:</small>
        <BInputGroup :id="`${identifier}-advanced-filter-${props.name}`" class="flex-nowrap">
            <BDropdown
                :text="dropDownText"
                block
                class="w-100"
                menu-class="w-100"
                size="sm"
                boundary="window"
                :disabled="props.disabled"
                :toggle-class="props.error ? 'text-danger' : ''">
                <BDropdownItem href="#" @click="setValue(undefined)"><i>(任何)</i></BDropdownItem>

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
                <span v-else-if="props.type === 'QuotaSource'">
                    <BDropdownItem
                        v-for="quotaUsage in quotaUsages"
                        :key="quotaUsage.sourceLabel"
                        href="#"
                        @click="setValue(quotaUsage)">
                        {{ quotaUsage.sourceLabel }}
                        <QuotaUsageBar
                            :quota-usage="quotaUsage"
                            class="quota-usage-bar"
                            :compact="true"
                            :embedded="true" />
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
