<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import type { IconDefinition } from "font-awesome-6";

import type { FileSourceTemplateSummary } from "@/api/fileSources";
import type { ObjectStoreTemplateSummary } from "@/api/objectStores.templates";
import type { CardAttributes } from "@/components/Common/GCard.types";
import { markup } from "@/components/ObjectStore/configurationMarkdown";

import GButton from "@/components/BaseComponents/GButton.vue";
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

const secondaryActions: CardAttributes[] = [
    {
        id: "view-request",
        label: "View Request JSON",
        title: "View the raw request JSON for this data import request",
        visible: true,
    },
];
</script>

<template>
    <GCard
        :id="props.sourceOption.id"
        :title="props.sourceOption.name ?? ''"
        :description="description"
        :secondary-actions="secondaryActions"
        :grid-view="props.gridView">
        <template v-slot:titleActions>
            <GButton
                tooltip
                transparent
                inline
                icon-only
                color="blue"
                size="large"
                :title="props.optionType?.title"
                class="inline-icon-button">
                <FontAwesomeIcon :icon="props.optionType?.icon" />
            </GButton>
        </template>

        <template v-slot:extra-actions>
            <slot name="badges" />
        </template>
    </GCard>
</template>
