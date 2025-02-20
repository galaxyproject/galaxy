<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";
import { type IconDefinition } from "font-awesome-6";

import type { FileSourceTemplateSummary } from "@/api/fileSources";
import type { ObjectStoreTemplateSummary } from "@/api/objectStores.templates";
import { markup } from "@/components/ObjectStore/configurationMarkdown";

import Heading from "@/components/Common/Heading.vue";
import TextSummary from "@/components/Common/TextSummary.vue";

interface Props {
    /** The source option to display */
    sourceOption: FileSourceTemplateSummary | ObjectStoreTemplateSummary;
    /** The route to navigate to when the user selects this option */
    selectRoute: string;
    /** The icon to display for the source option type */
    typeIcon?: IconDefinition;
    /** The title to display for the source option type */
    typeTitle?: string;
    /** Whether to display the card in a grid view */
    gridView?: boolean;
}

const props = defineProps<Props>();

function markdownToHTML(text: string) {
    return markup(text ?? "", true);
}
</script>

<template>
    <div :key="props.sourceOption.id" class="source-option-card" :class="{ 'grid-view': props.gridView }">
        <div class="source-option-card-content">
            <div>
                <div class="source-option-card-header">
                    <Heading bold size="md" class="source-option-card-header-name">
                        {{ props.sourceOption.name }}

                        <BButton
                            v-b-tooltip.hover.noninteractive
                            variant="outline-primary"
                            size="lg"
                            :title="props.typeTitle"
                            class="inline-icon-button">
                            <FontAwesomeIcon :icon="props.typeIcon" />
                        </BButton>
                    </Heading>

                    <slot name="badges" class="source-option-card-header-type" />
                </div>

                <TextSummary
                    v-if="props.sourceOption.description"
                    class="source-option-card-description"
                    is-html
                    show-expand-text
                    :description="markdownToHTML(props.sourceOption.description) ?? ''"
                    :max-length="props.gridView ? 250 : 350" />
            </div>

            <BButton
                v-b-tooltip.hover.noninteractive
                variant="outline-primary"
                class="source-option-card-select-button"
                :class="{ 'source-option-card-select-button-grid': props.gridView }"
                title="Select this option to create a new instance"
                :to="props.selectRoute">
                Select
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
        }
    }
}
</style>
