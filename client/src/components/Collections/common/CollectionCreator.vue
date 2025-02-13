<script setup lang="ts">
import { faPlus, faUpload } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BTab, BTabs } from "bootstrap-vue";
import { computed, ref, watch } from "vue";

import type { HDASummary } from "@/api";
import { COLLECTION_TYPE_TO_LABEL } from "@/components/History/adapters/buildCollectionModal";
import { useUploadConfigurations } from "@/composables/uploadConfigurations";
import localize from "@/utils/localization";

import CollectionCreatorFooterButtons from "./CollectionCreatorFooterButtons.vue";
import CollectionCreatorHelpHeader from "./CollectionCreatorHelpHeader.vue";
import CollectionCreatorNoItemsMessage from "./CollectionCreatorNoItemsMessage.vue";
import CollectionCreatorShowExtensions from "./CollectionCreatorShowExtensions.vue";
import CollectionCreatorSourceOptions from "./CollectionCreatorSourceOptions.vue";
import CollectionNameInput from "./CollectionNameInput.vue";
import DefaultBox from "@/components/Upload/DefaultBox.vue";

const Tabs = {
    create: 0,
    upload: 1,
};

interface Props {
    oncancel: () => void;
    historyId: string;
    hideSourceItems: boolean;
    suggestedName?: string;
    renderExtensionsToggle?: boolean;
    extensions?: string[];
    extensionsToggle?: boolean;
    noItems?: boolean;
    collectionType?: string;
    showUpload: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    suggestedName: "",
    extensions: undefined,
    extensionsToggle: false,
    showUpload: true,
    collectionType: undefined,
});

const emit = defineEmits<{
    (e: "remove-extensions-toggle"): void;
    (e: "clicked-create", value: string): void;
    (e: "onUpdateHideSourceItems", value: boolean): void;
    (e: "on-update-datatype-toggle", value: "all" | "datatype" | "ext"): void;
    (e: "add-uploaded-files", value: HDASummary[]): void;
}>();

const currentTab = ref(Tabs.create);
const collectionName = ref(props.suggestedName);
const localHideSourceItems = ref(props.hideSourceItems);

// Upload properties
const {
    configOptions,
    effectiveExtensions,
    listDbKeys,
    ready: uploadReady,
} = useUploadConfigurations(props.extensions);

const validInput = computed(() => {
    return collectionName.value.length > 0;
});

/** Plain language for what is being created */
const shortWhatIsBeingCreated = computed<string>(() => {
    return COLLECTION_TYPE_TO_LABEL[props.collectionType] || "collection";
});

function addUploadedFiles(value: HDASummary[]) {
    // TODO: We really need to wait for each of these items to get `state = 'ok'`
    //       before we can add them to the collection.
    emit("add-uploaded-files", value);
}

function cancelCreate() {
    props.oncancel();
}

function removeExtensionsToggle() {
    emit("remove-extensions-toggle");
}

watch(
    () => localHideSourceItems.value,
    () => {
        emit("onUpdateHideSourceItems", localHideSourceItems.value);
    }
);
</script>

<template>
    <span>
        <span v-if="!showUpload" class="collection-creator">
            <div v-if="props.noItems">
                <CollectionCreatorNoItemsMessage @click-upload="currentTab = Tabs.upload" />
            </div>
            <div v-else>
                <CollectionCreatorHelpHeader>
                    <slot name="help-content"></slot>
                </CollectionCreatorHelpHeader>

                <div class="middle flex-row flex-row-container">
                    <slot name="middle-content"></slot>
                </div>

                <div class="footer flex-row">
                    <div class="vertically-spaced">
                        <CollectionCreatorShowExtensions :extensions="extensions" />

                        <div class="d-flex align-items-center justify-content-between">
                            <CollectionCreatorSourceOptions
                                v-model="localHideSourceItems"
                                :render-extensions-toggle="renderExtensionsToggle"
                                :extensions-toggle="extensionsToggle"
                                @remove-extensions-toggle="removeExtensionsToggle" />
                            <CollectionNameInput
                                v-model="collectionName"
                                :short-what-is-being-created="shortWhatIsBeingCreated" />
                        </div>
                    </div>

                    <CollectionCreatorFooterButtons
                        :short-what-is-being-created="shortWhatIsBeingCreated"
                        :valid-input="validInput"
                        @clicked-cancel="cancelCreate"
                        @clicked-create="emit('clicked-create', collectionName)" />
                </div>
            </div>
        </span>
        <BTabs v-else v-model="currentTab" fill justified>
            <BTab class="collection-creator" :title="localize('Create Collection')">
                <div v-if="props.noItems">
                    <CollectionCreatorNoItemsMessage @click-upload="currentTab = Tabs.upload" />
                </div>
                <div v-else>
                    <CollectionCreatorHelpHeader>
                        <slot name="help-content"></slot>
                    </CollectionCreatorHelpHeader>

                    <div class="middle flex-row flex-row-container">
                        <slot name="middle-content"></slot>
                    </div>

                    <div class="footer flex-row">
                        <div class="vertically-spaced">
                            <CollectionCreatorShowExtensions :extensions="extensions" />

                            <div class="d-flex align-items-center justify-content-between">
                                <CollectionCreatorSourceOptions
                                    v-model="localHideSourceItems"
                                    :render-extensions-toggle="renderExtensionsToggle"
                                    :extensions-toggle="extensionsToggle" />
                                <CollectionNameInput
                                    v-model="collectionName"
                                    :short-what-is-being-created="shortWhatIsBeingCreated" />
                            </div>
                        </div>

                        <CollectionCreatorFooterButtons
                            :short-what-is-being-created="shortWhatIsBeingCreated"
                            :valid-input="validInput"
                            @clicked-cancel="cancelCreate"
                            @clicked-create="emit('clicked-create', collectionName)" />
                    </div>
                </div>
            </BTab>
            <BTab>
                <template v-slot:title>
                    <FontAwesomeIcon :icon="faUpload" fixed-width />
                    <span>{{ localize("Upload Files to Add to Collection") }}</span>
                </template>
                <DefaultBox
                    v-if="uploadReady"
                    :effective-extensions="effectiveExtensions"
                    v-bind="configOptions"
                    :has-callback="false"
                    :history-id="historyId"
                    :list-db-keys="listDbKeys"
                    disable-footer
                    emit-uploaded
                    @uploaded="addUploadedFiles"
                    @dismiss="currentTab = Tabs.create">
                    <template v-slot:footer>
                        <CollectionCreatorShowExtensions :extensions="extensions" upload />
                    </template>
                    <template v-slot:emit-btn-txt>
                        <FontAwesomeIcon :icon="faPlus" fixed-width />
                        {{ localize("Add Uploaded") }}
                    </template>
                </DefaultBox>
            </BTab>
        </BTabs>
    </span>
</template>

<style lang="scss">
$fa-font-path: "../../../../node_modules/@fortawesome/fontawesome-free/webfonts/";
@import "~@fortawesome/fontawesome-free/scss/_variables";
@import "~@fortawesome/fontawesome-free/scss/solid";
@import "~@fortawesome/fontawesome-free/scss/fontawesome";
@import "~@fortawesome/fontawesome-free/scss/brands";
.collection-creator {
    height: 100%;
    overflow: hidden;
    // ------------------------------------------------------------------------ general
    ol,
    li {
        list-style: none;
        padding: 0;
        margin: 0;
    }
    > *:not(.popover) {
        padding: 0px 8px 0px 8px;
    }
    .btn {
        border-color: #bfbfbf;
    }
    .vertically-spaced {
        margin-top: 8px;
    }
    .scroll-container {
        overflow: auto;
        //overflow-y: scroll;
    }
    .truncate {
        overflow: hidden;
        white-space: nowrap;
        text-overflow: ellipsis;
    }
    .empty-message {
        color: grey;
        font-style: italic;
    }
    // ------------------------------------------------------------------------ flex
    &.flex-row-container,
    .flex-row-container,
    .flex-column-container {
        display: -webkit-box;
        display: -webkit-flex;
        display: -ms-flexbox;
        display: flex;
        -webkit-align-items: stretch;
        -ms-align-items: stretch;
        align-items: stretch;
        -webkit-align-content: stretch;
        -ms-align-content: stretch;
        align-content: stretch;
    }
    // a series of vertical elements that will expand to fill available space
    // Tried to drop the important here but we have divs with classes of the form:
    //    flex-column-container scroll-container flex-row
    // and flex-row specifies a row direction with important. I was unable to separate
    // this into two separate divs and get the styling right but that'd probably be a
    // better way to go longer term.
    &.flex-row-container,
    .flex-row-container {
        -webkit-flex-direction: column !important;
        -ms-flex-direction: column !important;
        flex-direction: column !important;
    }
    .flex-row {
        -webkit-flex: 1 auto;
        -ms-flex: 1 auto;
        flex: 1 0 auto;
    }
    .flex-row.no-flex {
        -webkit-flex: 0 auto;
        -ms-flex: 0 auto;
        flex: 0 0 auto;
    }
    // a series of horizontal elements that will expand to fill available space
    .flex-column-container {
        -webkit-flex-direction: row;
        -ms-flex-direction: row;
        flex-direction: row;
    }
    .flex-column {
        -webkit-flex: 1 auto;
        -ms-flex: 1 auto;
        flex: 1 1 auto;
    }
    .flex-column.no-flex {
        -webkit-flex: 0 auto;
        -ms-flex: 0 auto;
        flex: 0 0 auto;
    }
    // ------------------------------------------------------------------------ sub-components
    .choose-filters {
        .help {
            margin-bottom: 2px;
            font-size: 90%;
            color: grey;
        }
        button {
            width: 100%;
            margin-top: 2px;
        }
    }
    .header .alert {
        display: none;
        li {
            list-style: circle;
            margin-left: 32px;
        }
    }
    // ------------------------------------------------------------------------ columns
    .column {
        width: 30%;
    }
    .column-title {
        height: 22px;
        line-height: 22px;
        overflow: hidden;
        &:hover {
            text-decoration: underline;
            cursor: pointer;
        }
        .title {
            font-weight: bold;
        }
        .title-info {
            color: grey;
            &:before {
                content: " - ";
            }
        }
    }
    // ------------------------------------------------------------------------ header
    .header {
        .main-help {
            margin-bottom: 17px;
            overflow: hidden;
            padding: 15px;
            &:not(.expanded) {
                // chosen to match alert - dependent on line height and .alert padding
                max-height: 49px;
                .help-content {
                    p:first-child {
                        overflow: hidden;
                        white-space: nowrap;
                        text-overflow: ellipsis;
                    }
                    > *:not(:first-child) {
                        display: none;
                    }
                }
            }
            &.expanded {
                max-height: none;
            }
            .help-content {
                i {
                    cursor: help;
                    border-bottom: 1px dotted grey;
                    font-style: normal;
                    //font-weight: bold;
                    //text-decoration: underline;
                    //text-decoration-style: dashed;
                }
                ul,
                li {
                    list-style: circle;
                    margin-left: 16px;
                }
                .scss-help {
                    display: inline-block;
                    width: 100%;
                    text-align: right;
                }
            }
            .more-help {
                //display: inline-block;
                float: right;
            }
        }
        .column-headers {
            .column-header {
                //min-height: 45px;
                .unpaired-filter {
                    width: 100%;
                    .search-query {
                        width: 100%;
                        height: 22px;
                    }
                }
            }
        }
        .paired-column a:not(:last-child) {
            margin-right: 8px;
        }
        .reverse-column .column-title {
            text-align: right;
        }
    }
    // ------------------------------------------------------------------------ middle
    // ---- all
    // macro
    .flex-bordered-vertically {
        // huh! - giving these any static height will pull them in
        height: 0;
        // NOT setting the above will give a full-height page
        border: 1px solid lightgrey;
        border-width: 1px 0 1px 0;
    }
    .element-drop-placeholder {
        width: 60px;
        height: 3px;
        margin: 2px 0px 0px 14px;
        background: black;
        &:before {
            @extend .fas;
            float: left;
            font-size: 120%;
            margin: -9px 0px 0px -8px;
            content: fa-content($fa-var-caret-right);
        }
        &:last-child {
            margin-bottom: 8px;
        }
    }
    // ------------------------------------------------------------------------ footer
    .footer {
        .inputs-form-group > div {
            width: 100%;
            display: flex;
            align-items: center;
            column-gap: 0.25rem;
        }
        .actions {
            .other-options > * {
                // do not display the links to create other collections yet
                display: none;
                margin-left: 4px;
            }
        }
        padding-bottom: 8px;
    }
}
</style>
