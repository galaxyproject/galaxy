<script setup lang="ts">
import { computed, onMounted, ref, type UnwrapRef, watch } from "vue";

import { type QuotaUsage } from "@/components/User/DiskUsage/Quota/model";
import { fetch } from "@/components/User/DiskUsage/Quota/services";
import { ValidFilter } from "@/utils/filtering";
import { errorMessageAsString } from "@/utils/simple-error";

import QuotaUsageBar from "@/components/User/DiskUsage/Quota/QuotaUsageBar.vue";

type QuotaUsageUnwrapped = UnwrapRef<QuotaUsage>;

type FilterType = QuotaUsageUnwrapped | string | boolean | undefined;

interface Props {
    name: string;
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

const quotaUsages = ref<QuotaUsage[]>([] as QuotaUsage[]);
const errorMessage = ref<string>();

async function loadQuotaUsages() {
    try {
        quotaUsages.value = await fetch();
    } catch (e) {
        errorMessage.value = errorMessageAsString(e);
    }
}

const hasMultipleQuotaSources = computed<boolean>(() => {
    return !!(quotaUsages.value && quotaUsages.value.length > 1);
});

onMounted(async () => {
    await loadQuotaUsages();
});

function isQuotaUsage(value: FilterType): value is QuotaUsageUnwrapped {
    return !!(value && value instanceof Object && "rawSourceLabel" in value);
}

const dropDownText = computed<string>(() => {
    if (isQuotaUsage(localValue.value)) {
        return localValue.value.sourceLabel;
    } else {
        return "(any)";
    }
});

function setValue(val: QuotaUsage | undefined) {
    localValue.value = val;
}
</script>

<template>
    <div v-if="hasMultipleQuotaSources">
        <small>Filter by {{ props.filter.placeholder }}:</small>
        <b-input-group :id="`${identifier}-advanced-filter-${props.name}`">
            <b-dropdown :text="dropDownText" block class="m-2" size="sm" boundary="window">
                <b-dropdown-item href="#" @click="setValue(undefined)"><i>(any)</i></b-dropdown-item>

                <b-dropdown-item
                    v-for="quotaUsage in quotaUsages"
                    :key="quotaUsage.id"
                    href="#"
                    @click="setValue(quotaUsage)">
                    {{ quotaUsage.sourceLabel }}
                    <QuotaUsageBar :quota-usage="quotaUsage" class="quota-usage-bar" :compact="true" :embedded="true" />
                </b-dropdown-item>
            </b-dropdown>
        </b-input-group>
    </div>
</template>
