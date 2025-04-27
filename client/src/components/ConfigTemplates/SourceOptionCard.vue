<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";
import { type IconDefinition } from "font-awesome-6";

import type { FileSourceTemplateSummary } from "@/api/fileSources";
import type { ObjectStoreTemplateSummary } from "@/api/objectStores.templates";
import type { CardAttributes } from "@/components/Common/GCard.types";
import { markup } from "@/components/ObjectStore/configurationMarkdown";

import GCard from "@/components/Common/GCard.vue";

type OptionType = {
    icon: IconDefinition;
    title: string;
};

interface Props {
    /** The source option to display */
    sourceOption: FileSourceTemplateSummary | ObjectStoreTemplateSummary;
    /** The route to navigate to when the user selects this option */
    selectRoute: string;
    /** The type of the source option */
    optionType: OptionType;
    /** Whether to display the card in a grid view */
    gridView?: boolean;
}

const props = defineProps<Props>();

const description = markup(props.sourceOption.description ?? "", true) ?? undefined;

const primaryActions: CardAttributes[] = [
    {
        id: "select",
        label: "Select",
        title: "Select this option to create a new instance",
        variant: "outline-primary",
        to: props.selectRoute,
        visible: true,
    },
];
</script>

<template>
    <GCard
        :id="props.sourceOption.id"
        :title="props.sourceOption.name ?? ''"
        :description="description"
        :primary-actions="primaryActions"
        :grid-view="props.gridView">
        <template v-slot:titleActions>
            <BButton
                v-b-tooltip.hover.noninteractive
                variant="outline-primary"
                size="lg"
                :title="props.optionType?.title"
                class="inline-icon-button">
                <FontAwesomeIcon :icon="props.optionType?.icon" />
            </BButton>
        </template>

        <template v-slot:extra-actions>
            <slot name="badges" />
        </template>
    </GCard>
</template>
