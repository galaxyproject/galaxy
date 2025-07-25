<script setup lang="ts">
import { computed } from "vue";

import type { DatasetTransform } from "@/api";

const TRANSFORM_ACTION_DESCRIPTIONS = {
    to_posix_lines: {
        short: "Normalized new line characters",
        long: "Many Galaxy tools expect data to contain 'posix' newline characters in text files and not the newline format used by the Windows operating system. Additionally, most tools expect a newline at the end of plain text files. This file was converted to use these line endings or add a newline to the end of the file.",
    },
    spaces_to_tabs: {
        short: "Normalized spaces to tabs",
        long: "In order to convert the referenced data source to tabular data, spaces in the file contents were converted to tab characters to indicate column separations.",
    },
    datatype_groom: {
        short: "Datatype-specific grooming",
        long: "The Galaxy datatype class indicated the source data required 'groooming' and Galaxy applied datatype specific cleaning of the supplied data.",
    },
};

const DATATYPE_GROOMING_DESCRIPTIONS = new Map<string, string>([
    ["bam", "The supplied BAM was coordinate-sorted using pysam."],
    ["qname_sorted.bam", "The supplied BAM was 'queryname' sorted using pysam."],
    ["qname_input_sorted.bam", "The supplied BAM was 'queryname' sorted using pysam."],
    ["isa-tab", "The supplied compressed file was converted to an ISA-TAB composite dataset."],
    ["isa-json", "The supplied compressed file was converted to an ISA-JSON composite dataset."],
]);

const UNKNOWN_ACTION_DESCRIPTION = {
    short: "Unknown action.",
    long: "",
};

interface Props {
    transform: DatasetTransform[];
}

const props = defineProps<Props>();

const actions = computed(() => {
    return props.transform.length > 1 ? "actions" : "action";
});

function actionDescription(transformAction: DatasetTransform) {
    return TRANSFORM_ACTION_DESCRIPTIONS[transformAction.action] || UNKNOWN_ACTION_DESCRIPTION;
}

function actionShortDescription(transformAction: DatasetTransform) {
    return actionDescription(transformAction).short || "Unknown action.";
}

function actionLongDescription(transformAction: DatasetTransform) {
    let longDescription = actionDescription(transformAction).long || "";
    const datatypeExt = transformAction.datatype_ext;
    if (transformAction.action == "datatype_groom" && datatypeExt && DATATYPE_GROOMING_DESCRIPTIONS.has(datatypeExt)) {
        const datatypeDescription: string | undefined = DATATYPE_GROOMING_DESCRIPTIONS.get(datatypeExt);

        if (datatypeDescription) {
            longDescription += " " + datatypeDescription;
        }
    }

    return longDescription;
}
</script>

<template>
    <span class="dataset-source-transform-display">
        <div v-if="transform && transform.length > 0">
            Upon ingestion into the Galaxy, the following {{ actions }} were performed that modified the dataset
            contents:
            <ul>
                <li v-for="(transformAction, index) in transform" :key="index">
                    <span
                        v-b-tooltip.hover.noninteractive.nofade.bottom
                        :title="actionLongDescription(transformAction)"
                        class="dataset-source-transform-element"
                        :data-transform-action="transformAction.action">
                        {{ actionShortDescription(transformAction) }}
                    </span>
                </li>
            </ul>
        </div>
    </span>
</template>

<style scoped>
.dataset-source-transform-element {
    text-decoration: underline;
    text-decoration-style: dashed;
}
</style>
