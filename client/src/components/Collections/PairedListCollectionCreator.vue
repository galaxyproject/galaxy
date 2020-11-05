<template>
    <div class="paired-list-collection-creator">
        <collection-creator
            :oncancel="oncancel"
            @hide-original-toggle="hideOriginalsToggle"
            @clicked-create="clickedCreate"
            :creationFn="creationFn"
        >
            <template v-slot:help-content
                ><p>
                    {{
                        l(
                            [
                                "Collections of paired datasets are ordered lists of dataset pairs (often forward and reverse reads). ",
                                "These collections can be passed to tools and workflows in order to have analyses done on each member of ",
                                "the entire group. This interface allows you to create a collection, choose which datasets are paired, ",
                                "and re-order the final collection.",
                            ].join("")
                        )
                    }}
                </p>
                <p>
                    {{ l("Unpaired datasets are shown in the") }}
                    <i data-target=".unpaired-columns">
                        {{ l("unpaired section") }}
                    </i>
                    {{ "." }}
                    {{ l("Paired datasets are shown in the") }}
                    <i data-target=".paired-columns">
                        {{ l("paired section") }}
                    </i>
                    {{ "." }}
                </p>
                <ul>
                    {{
                        l("To pair datasets, you can:")
                    }}
                    <li>
                        {{ l("Click a dataset in the") }}
                        <i data-target=".forward-column">
                            {{ l("forward column") }}
                        </i>
                        {{ l("to select it then click a dataset in the") }}
                        <i data-target=".reverse-column">
                            {{ l("reverse column") }}
                        </i>
                    </li>
                    <li>
                        {{
                            l(
                                "Click one of the Pair these datasets buttons in the middle column to pair the datasets in a particular row."
                            )
                        }}
                    </li>
                    <li>
                        {{ l("Click") }}
                        <i data-target=".autopair-link">
                            {{ l("Auto-pair") }}
                        </i>
                        {{ l("to have your datasets automatically paired based on name.") }}
                    </li>
                </ul>
                <ul>
                    {{
                        l("You can filter what is shown in the unpaired sections by:")
                    }}
                    <li>
                        {{ l("Entering partial dataset names in either the ") }}
                        <i data-target=".forward-unpaired-filter input">
                            {{ l("forward filter") }}
                        </i>
                        {{ l("or ") }}
                        <i data-target=".reverse-unpaired-filter input">
                            {{ l("reverse filter") }}
                        </i>
                        {{ "." }}
                    </li>
                    <li>
                        {{ l("Choosing from a list of preset filters by clicking the") }}
                        <i data-target=".choose-filters-link">
                            {{ l("Choose filters link") }}
                        </i>
                        {{ "." }}
                    </li>
                    <li>
                        {{ l("Entering regular expressions to match dataset names. See:") }}
                        <a
                            href="https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Regular_Expressions"
                            target="_blank"
                        >
                            {{ l("MDN's JavaScript Regular Expression Tutorial") }}</a
                        >
                        {{ l("Note: forward slashes (\\) are not needed.") }}
                    </li>
                    <li>
                        {{ l("Clearing the filters by clicking the ") }}
                        <i data-target=".clear-filters-link">
                            {{ l("Clear filters link") }}
                        </i>
                        {{ "." }}
                    </li>
                </ul>
                <p>
                    {{ l("To unpair individual dataset pairs, click the ") }}
                    <i data-target=".unpair-btn">
                        {{ l("unpair buttons (") }}
                        <span class="fa fa-unlink"></span>
                        {{ ")" }}
                    </i>
                    {{ l("Click the") }}
                    <i data-target=".unpair-all-link">
                        {{ l("Unpair all") }}
                    </i>
                    {{ l("link to unpair all pairs.") }}
                </p>
                <p>
                    {{
                        l(
                            'You can include or remove the file extensions (e.g. ".fastq") from your pair names by toggling the'
                        )
                    }}
                    <i data-target=".remove-extensions-prompt">
                        {{ l("Remove file extensions from pair names?") }}
                    </i>
                    {{ l("control.") }}
                </p>
                <p>
                    {{ l("Once your collection is complete, enter a") }}
                    <i data-target=".collection-name">
                        {{ l("name") }}
                    </i>
                    {{ l("and click ") }}
                    <i data-target=".create-collection">
                        {{ l("Create list") }}
                    </i>
                    {{ l(". (Note: you do not have to pair all unpaired datasets to finish.)") }}
                </p>
            </template>
            <template v-slot:middle-content>
                <div class="unpaired-columns flex-column-container scroll-container flex-row">
                    <div class="forward-column flex-column column">
                        <ol class="column-datasets"></ol>
                    </div>
                    <div class="paired-column flex-column no-flex column">
                        <ol class="column-datasets"></ol>
                    </div>
                    <div class="reverse-column flex-column column">
                        <ol class="column-datasets"></ol>
                    </div>
                </div>
                <div class="flexible-partition">
                    <div class="flexible-partition-drag" title="dragToChangeTitle"></div>
                    <div class="column-header">
                        <div class="column-title paired-column-title">
                            <span class="title"></span>
                        </div>
                        <a class="unpair-all-link" href="javascript:void(0);" role="button">
                            {{ l("Unpair all") }}
                        </a>
                    </div>
                </div>
                <div class="paired-columns flex-column-container scroll-container flex-row">
                    <ol class="column-datasets"></ol>
                </div>
            </template>
        </collection-creator>
    </div>
</template>
<script>
import _l from "utils/localization";
import CollectionCreator from "./common/CollectionCreator";
import DatasetCollectionElementView from "./PairedListDatasetCollectionElementView";
export default {
    created() {},
    components: { CollectionCreator, DatasetCollectionElementView }, //draggable?
    data: function () {
        return {
            state: "build", //error
            dragToChangeTitle: "Drag to change",
        };
    },
    props: {
        initialElements: {
            required: true,
            type: Array,
        },
        creationFn: {
            type: Function,
            required: true,
        },
        /** fn to call when the cancel button is clicked (scoped to this) - if falsy, no btn is displayed */
        oncancel: {
            type: Function,
            required: true,
        },
        oncreate: {
            type: Function,
            required: true,
        },
        defaultHideSourceItems: {
            type: Boolean,
            required: false,
            default: false,
        },
    },
    methods: {
        l(str) {
            // _l conflicts private methods of Vue internals, expose as l instead
            return _l(str);
        },
    },
};
</script>
<style scoped></style>
