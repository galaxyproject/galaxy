<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";
import { faNetworkWired } from "font-awesome-6";

import type { FileSourceTemplateSummary, FileSourceTypes, FileSourceTypesDetail } from "@/api/fileSources";
import { markup } from "@/components/ObjectStore/configurationMarkdown";

import Heading from "@/components/Common/Heading.vue";
import TextSummary from "@/components/Common/TextSummary.vue";

interface Props {
    /** The file source template to display */
    fileSourceTemplate: FileSourceTemplateSummary;
    /** The available file source template types */
    templateTypes: FileSourceTypesDetail;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "typeFilter", t: FileSourceTypes): void;
}>();

function markdownToHTML(text: string) {
    return markup(text ?? "", true);
}

function getTypeIcon(t: FileSourceTypes) {
    return props.templateTypes[t].icon ?? faNetworkWired;
}
</script>

<template>
    <div :key="props.fileSourceTemplate.id" class="file-source-template-card">
        <div>
            <div class="file-source-template-card-header">
                <Heading bold size="md">{{ props.fileSourceTemplate.name }}</Heading>

                <div class="file-source-template-card-header-type">
                    <BButton
                        v-b-tooltip.hover.noninteractive
                        variant="outline-primary"
                        size="sm"
                        :title="
                            props.templateTypes[props.fileSourceTemplate.type].message +
                            ' (click to filter by this type)'
                        "
                        class="inline-icon-button"
                        @click="emit('typeFilter', props.fileSourceTemplate.type)">
                        <FontAwesomeIcon :icon="getTypeIcon(props.fileSourceTemplate.type)" />
                        {{ props.fileSourceTemplate.type }}
                    </BButton>
                </div>
            </div>

            <TextSummary
                v-if="props.fileSourceTemplate.description"
                class="file-source-template-card-description"
                is-html
                show-expand-text
                :description="markdownToHTML(props.fileSourceTemplate.description) ?? ''"
                :max-length="200" />
        </div>

        <BButton
            v-b-tooltip.hover.noninteractive
            variant="outline-primary"
            class="file-source-template-card-select-button"
            title="Select this template to create a new file source instance"
            :to="`/file_source_templates/${props.fileSourceTemplate.id}/new`">
            Select
        </BButton>
    </div>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";
@import "breakpoints.scss";

.file-source-template-card {
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

    .file-source-template-card-header {
        display: grid;
        grid-template-areas: "name type";
        align-items: baseline;

        .file-source-template-card-header-type {
            display: flex;
            align-self: start;
            justify-content: flex-end;
        }
    }

    .file-source-template-card-description {
        position: relative;
        display: flex;
        flex-direction: column;

        :deep p {
            margin: 0;
        }
    }

    .file-source-template-card-select-button {
        display: flex;
        margin-top: auto;
        justify-content: center;
        width: 100%;
    }
}
</style>
