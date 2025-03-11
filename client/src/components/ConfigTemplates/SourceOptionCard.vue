<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BSpinner } from "bootstrap-vue";
import { type IconDefinition } from "font-awesome-6";
import { computed } from "vue";

import { type UserConcreteObjectStoreModel } from "@/api";
import { type FileSourceTemplateSummary } from "@/api/fileSources";
import { type ObjectStoreTemplateSummary } from "@/api/objectStores.templates";
import { markup } from "@/components/ObjectStore/configurationMarkdown";
import { QuotaSourceUsageProvider } from "@/components/User/DiskUsage/Quota/QuotaUsageProvider.js";

import Heading from "@/components/Common/Heading.vue";
import TextSummary from "@/components/Common/TextSummary.vue";
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
        return Math.random().toString(36).substring(7);
    }
});
const buttonTitle = computed(() => {
    if (props.selectionMode) {
        return props.selected ? "Selected" : "Select as Default";
    }

    return props.submitButtonTooltip ?? "Select";
});
const buttonTooltip = computed(() => {
    if (props.selectionMode) {
        return props.selected ? "This is the preferred option" : "Select this option as the preferred one";
    }

    return props.submitButtonTooltip ?? "Select this option to create a new instance";
});
const quotaSourceLabel = computed(() => {
    if ("quota" in props.sourceOption && props.sourceOption.quota.enabled) {
        return props.sourceOption.quota.source;
    }

    return "";
});

function markdownToHTML(text: string) {
    return markup(text ?? "", true);
}
</script>

<template>
    <div
        :key="uniqueId"
        :data-source-option-card-id="uniqueId"
        class="source-option-card"
        :class="{ 'grid-view': props.gridView }">
        <div class="source-option-card-content" :class="{ 'source-option-card-selected': props.selected }">
            <div>
                <div class="source-option-card-header">
                    <Heading bold size="md" class="source-option-card-header-name">
                        {{ props.sourceOption.name }}

                        <BButton
                            v-if="props.optionType"
                            v-b-tooltip.hover.noninteractive
                            variant="outline-primary"
                            size="lg"
                            :title="props.optionType?.title"
                            class="inline-icon-button">
                            <FontAwesomeIcon :icon="props.optionType?.icon" />
                        </BButton>
                    </Heading>

                    <slot name="badges" class="source-option-card-header-type" />
                </div>

                <QuotaSourceUsageProvider
                    v-if="'quota' in props.sourceOption && props.sourceOption.quota.enabled"
                    ref="quotaUsageProvider"
                    v-slot="{ result: quotaUsage, loading: isLoadingUsage }"
                    :quota-source-label="quotaSourceLabel">
                    <BSpinner v-if="isLoadingUsage" />
                    <QuotaUsageBar v-else-if="quotaUsage" :quota-usage="quotaUsage" :embedded="true" />
                </QuotaSourceUsageProvider>

                <TextSummary
                    v-if="props.sourceOption.description"
                    class="source-option-card-description"
                    is-html
                    show-expand-text
                    :description="markdownToHTML(props.sourceOption.description) ?? ''"
                    :max-length="props.gridView ? 250 : 350" />
            </div>

            <BButton
                :id="`select-button-${uniqueId}`"
                v-b-tooltip.hover.noninteractive
                variant="outline-primary"
                class="source-option-card-select-button"
                :class="{ 'source-option-card-select-button-selected': props.selected }"
                :title="buttonTooltip"
                :to="props.selectRoute"
                @click="emit('select', props.sourceOption)">
                {{ buttonTitle }}
            </BButton>
        </div>
    </div>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";
@import "_breakpoints.scss";

.source-option-card {
    width: 100%;

    &.grid-view {
        width: calc(100% / 3);

        @container templates-list (max-width: #{$breakpoint-xl}) {
            width: calc(100% / 2);
        }

        @container templates-list (max-width: #{$breakpoint-sm}) {
            width: 100%;
        }
    }

    padding: 0 0.25rem 0.5rem 0.25rem;

    .source-option-card-content {
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        border: 1px solid $brand-secondary;
        border-radius: 0.5rem;
        padding: 0.75rem;
        height: 100%;

        &.source-option-card-selected {
            background-color: $brand-light;
            border: 0.1rem solid $brand-primary;
            border-left: 0.25rem solid $brand-primary;
        }

        .source-option-card-header {
            display: grid;
            grid-template-areas: "name type";
            align-items: baseline;
            gap: 0.5rem;

            .source-option-card-header-name {
                display: block;
            }
        }

        .source-option-card-description {
            position: relative;
            display: flex;
            flex-direction: column;

            :deep p {
                margin: 0;
            }
        }

        .source-option-card-select-button {
            width: fit-content;
            margin-top: auto;
            display: flex;
            align-self: flex-end;
            justify-content: center;

            &.source-option-card-select-button-selected {
                visibility: hidden;
            }
        }
    }
}
</style>
