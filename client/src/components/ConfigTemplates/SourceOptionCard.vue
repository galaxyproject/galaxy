<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import type { IconDefinition } from "font-awesome-6";
import { computed } from "vue";

import type { UserConcreteObjectStoreModel } from "@/api";
import type { FileSourceTemplateSummary } from "@/api/fileSources";
import type { ObjectStoreTemplateSummary } from "@/api/objectStores.templates";
import type { CardAction } from "@/components/Common/GCard.types";
import { QuotaSourceUsageProvider } from "@/components/User/DiskUsage/Quota/QuotaUsageProvider.js";

import GButton from "@/components/BaseComponents/GButton.vue";
import GCard from "@/components/Common/GCard.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import QuotaUsageBar from "@/components/User/DiskUsage/Quota/QuotaUsageBar.vue";

type SourceOption = FileSourceTemplateSummary | ObjectStoreTemplateSummary | UserConcreteObjectStoreModel;

type OptionType = {
    icon: IconDefinition;
    title: string;
};

interface Props {
    /** The source option to display */
    sourceOption: SourceOption;
    /** The route to navigate to when the user selects this option */
    selectRoute?: string;
    /** The type of the source option */
    optionType?: OptionType;
    /** Whether to display the card in a grid view */
    gridView?: boolean;
    /** Whether the card is selected */
    selected?: boolean;
    /** The title of the submit button */
    submitButtonTooltip?: string;
    /** Whether to show the selection mode */
    selectionMode?: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "select", sourceOption: SourceOption): void;
}>();

const uniqueId = computed(() => {
    if ("id" in props.sourceOption) {
        return props.sourceOption.id;
    } else if ("object_store_id" in props.sourceOption && props.sourceOption.object_store_id) {
        return props.sourceOption.object_store_id;
    } else {
        return undefined;
    }
});
const buttonTitle = computed(() => {
    if (props.selectionMode) {
        return props.selected ? "Current preferred option" : "Select as the preferred one";
    }

    return props.submitButtonTooltip ?? "Select";
});
const buttonTooltip = computed(() => {
    if (props.selectionMode) {
        return props.selected ? "Current preferred option" : "Select as the preferred one";
    }

    return props.submitButtonTooltip ?? "Select this option to create a new instance";
});
const quotaSourceLabel = computed(() => {
    if ("quota" in props.sourceOption && props.sourceOption.quota.enabled) {
        return props.sourceOption.quota.source;
    }

    return "";
});

const primaryActions = computed<CardAction[]>(() => [
    {
        id: "select",
        label: buttonTitle.value,
        title: buttonTooltip.value,
        variant: "outline-primary",
        to: props.selectRoute,
        handler: () => emit("select", props.sourceOption),
        visible: !props.selected,
    },
]);
</script>

<template>
    <GCard
        :id="uniqueId"
        :data-source-option-card-id="uniqueId"
        :title="props.sourceOption.name ?? ''"
        full-description
        :description="props.sourceOption.description ?? ''"
        :primary-actions="primaryActions"
        :grid-view="props.gridView"
        :selected="props.selected">
        <template v-slot:titleActions>
            <GButton
                v-if="props.optionType?.icon"
                tooltip
                transparent
                inline
                icon-only
                color="blue"
                size="large"
                :title="props.optionType?.title"
                class="inline-icon-button">
                <FontAwesomeIcon :icon="props.optionType.icon" />
            </GButton>
        </template>

        <template v-slot:extra-actions>
            <slot name="badges" />
        </template>

        <template v-if="'quota' in props.sourceOption && props.sourceOption.quota.enabled" v-slot:tags>
            <QuotaSourceUsageProvider
                ref="quotaUsageProvider"
                v-slot="{ result: quotaUsage, loading: isLoadingUsage }"
                class="w-100"
                :quota-source-label="quotaSourceLabel">
                <LoadingSpan v-if="isLoadingUsage" message="Loading usage" />
                <QuotaUsageBar v-else-if="quotaUsage" :quota-usage="quotaUsage" :embedded="true" />
            </QuotaSourceUsageProvider>
        </template>
    </GCard>
</template>
