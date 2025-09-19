<script setup lang="ts">
// TODO: configure pairing link...
import { faGripHorizontal, faLink, faTimes, faUndo, faUnlink } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BCol, BRow } from "bootstrap-vue";
import { computed } from "vue";

import type { SupportedPairedOrPairedBuilderCollectionTypes } from "./common/useCollectionCreator";

interface Props {
    fromSelection?: boolean;
    collectionType: SupportedPairedOrPairedBuilderCollectionTypes;
    mode: "wizard" | "modal";
}

const props = defineProps<Props>();

const usesPairing = computed(() => {
    return props.collectionType.indexOf("paired") !== -1;
});
const requiresPairing = computed(() => {
    return props.collectionType.endsWith("paired");
});
</script>

<template>
    <BRow>
        <BCol>
            <p v-if="collectionType == 'list:paired'" data-description="what is being built">
                This interface allows you to build a new Galaxy list of pairs. List of pairs are an ordered list of
                individual datasets paired together in their own paired collection (often forward and reverse reads).
            </p>
            <p v-else-if="collectionType == 'list:list:paired'" data-description="what is being built">
                This interface allows you to build a new Galaxy nested list of pairs. A nested list of pairs are a
                nested list of individual lists. Each these inner lists consists of elements which are datasets paired
                together in their own paired collection (often forward and reverse reads).
            </p>
            <p v-else-if="collectionType == 'list:list'" data-description="what is being built">
                This interface allows you to build a new Galaxy nested list. A nested list is a list where each element
                is in turn a list of datasets. Each dataset in this structure has an inner and outer element identifier
                that together uniquely identify it and these identifiers are preserved through an analysis.
            </p>
            <p v-else-if="collectionType == 'list:paired_or_unpaired'" data-description="what is being built">
                This interface allows you to build a new Galaxy list of mixed paired and unpaired datasets. In general,
                tools are better at using a flat list or a list of pairs, so this mixed version should only be used if
                you have an analysis and data that requires paired and unpaired data to be processed together in a
                uniform way.
            </p>
            <p data-description="info about lists">
                These lists can be passed to tools and workflows in order to have analyses done on each member of the
                entire group. This interface allows you to create such a list, choose the structure, assign list
                identifiers, and re-order the final collection.
            </p>
            <p v-if="usesPairing">
                Any rows corresponding to datasets or pairs of datasets that should not be included in the resulting
                list can be discarded by click the <FontAwesomeIcon :icon="faTimes" />
                icon in that row.
            </p>
            <p v-else>
                Any datasets that should not be included in the resulting list can be discarded by click the
                <FontAwesomeIcon :icon="faTimes" /> icon in that row.
            </p>
            <p data-description="what is included in the final collection">
                <span v-if="usesPairing">
                    Each row in the table below corresponds to a dataset or a pair of datasets. Galaxy attempts to
                    auto-pair your datasets but this can be controlled or pairing can be done manually using the
                    controls below.
                    <span v-if="requiresPairing">
                        Any individual datasets that are unmatched will not be included in the final list.
                    </span>
                    <span v-else>
                        Any individual datasets that are unmatched will be included in the final list as a single
                        'unpaired' dataset.
                    </span>
                </span>
                <span v-else>
                    Each row in the table corresponds to a dataset. Any datasets not discarded will be a member of the
                    resulting collection.
                </span>
            </p>
            <p data-description="more about pairing">
                If the Galaxy auto-pairing is off, it can be configured using regular expressions by clicking on the
                "configure auto-pairing" link in the summary box above the grid
                <span v-if="mode == 'modal'"> below or just navigating to the previous step of this wizard. </span>
                <span v-else> below. </span>
                <span>
                    If your datasets are not named with a pattern that would allow doing this, the pairing can be
                    configured manually. This can be done by clicking the
                    <FontAwesomeIcon :icon="faLink" /> on one dataset and dragging on top of the
                    <FontAwesomeIcon :icon="faLink" /> of the other dataset to be paired. If the pairing direction is
                    wrong, the forward is labelled reverse or the first and second dataset are wrong - this can be
                    corrected by simply clicking the <FontAwesomeIcon :icon="faUndo" /> icon to swap them. If datasets
                    are mis-paired, either automatically by Galaxy or by mis-clicking, simply click the
                    <FontAwesomeIcon :icon="faUnlink" />
                    to unlink the row and turn a dataset pair into two individual datasets.
                </span>
            </p>
            <p data-description="element identifiers">
                Each element of the final list should have a unique list identifier. This builder will warn you if there
                are duplicate identifiers found and will require you to fix them before a list can be created. You can
                change guessed list identifier by double clicking on the value in the grid and changing the text. This
                list identifier is preserved as you run tools over the elements of your collection - so it is best to
                strip extensions like <code>.fq</code>, <code>.bam</code>, etc. from your collection identifiers.
            </p>
            <p data-description="element order">
                The order of elements in the collection will also be preserved as your run tools over the collection and
                some tools and workflows will consume multiple collections together and expect elements to match up in
                specific ways. If any of these are concerns for your data, you can sort the list. The order in the grid
                below will be the order they appear in the final collection. You can sort by list identifier by clicking
                on the column header for that column. Alternatively, you can manually reorder a row by clicking on the
                <FontAwesomeIcon :icon="faGripHorizontal" /> and dragging the row up or down to the desired location.
            </p>
        </BCol>
    </BRow>
</template>
