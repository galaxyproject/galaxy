<script setup lang="ts">
import { BButton } from "bootstrap-vue";

import type { FileSourceTemplateSummary } from "@/api/fileSources";
import type { ObjectStoreTemplateSummary } from "@/api/objectStores.templates";
import { markup } from "@/components/ObjectStore/configurationMarkdown";

import Heading from "@/components/Common/Heading.vue";
import TextSummary from "@/components/Common/TextSummary.vue";

interface Props {
    /** The file source template to display */
    sourceTemplate: FileSourceTemplateSummary | ObjectStoreTemplateSummary;
    /** The route to navigate to when the user selects this template */
    selectRoute: string;
}

const props = defineProps<Props>();

function markdownToHTML(text: string) {
    return markup(text ?? "", true);
}
</script>

<template>
    <div :key="props.sourceTemplate.id" class="source-template-card">
        <div>
            <div class="source-template-card-header">
                <Heading bold size="md">{{ props.sourceTemplate.name }}</Heading>

                <slot name="badges" class="source-template-card-header-type" />
            </div>

            <TextSummary
                v-if="props.sourceTemplate.description"
                class="source-template-card-description"
                is-html
                show-expand-text
                :description="markdownToHTML(props.sourceTemplate.description) ?? ''"
                :max-length="200" />
        </div>

        <BButton
            v-b-tooltip.hover.noninteractive
            variant="outline-primary"
            class="source-template-card-select-button"
            title="Select this template to create a new instance"
            :to="props.selectRoute">
            Select
        </BButton>
    </div>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";
@import "breakpoints.scss";

.source-template-card {
    width: calc(100% / 3 - 1rem);

    @container templates-list (max-width: #{$breakpoint-xl}) {
        width: calc(100% / 2 - 1rem);
    }

    @container templates-list (max-width: #{$breakpoint-sm}) {
        width: 100%;
    }

    display: flex;
    gap: 0.5rem;
    flex-direction: column;
    justify-content: space-between;
    border: 1px solid $brand-secondary;
    border-radius: 0.5rem;
    padding: 0.75rem;

    .source-template-card-header {
        display: grid;
        grid-template-areas: "name type";
        align-items: baseline;
    }

    .source-template-card-description {
        position: relative;
        display: flex;
        flex-direction: column;

        :deep p {
            margin: 0;
        }
    }

    .source-template-card-select-button {
        display: flex;
        margin-top: auto;
        justify-content: center;
        width: 100%;
    }
}
</style>
