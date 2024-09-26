<script setup lang="ts">
import { faChevronDown, faChevronUp } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton, BFormCheckbox, BFormGroup, BFormInput, BFormRadioGroup } from "bootstrap-vue";
import { computed, ref, watch } from "vue";

import localize from "@/utils/localization";
import { orList } from "@/utils/strings";

import HelpText from "@/components/Help/HelpText.vue";

interface Props {
    oncancel: () => void;
    hideSourceItems: boolean;
    suggestedName?: string;
    renderExtensionsToggle?: boolean;
    extensions?: string[];
    extensionsToggle?: boolean;
    datatypeToggle?: "all" | "datatype" | "ext";
    datatypeToggleOptions?: { text: string; value: string }[];
}

const props = withDefaults(defineProps<Props>(), {
    suggestedName: "",
    extensions: undefined,
    extensionsToggle: false,
    datatypeToggle: undefined,
    datatypeToggleOptions: undefined,
});

const emit = defineEmits<{
    (e: "remove-extensions-toggle"): void;
    (e: "clicked-create", value: string): void;
    (e: "onUpdateHideSourceItems", value: boolean): void;
    (e: "on-update-datatype-toggle", value: "all" | "datatype" | "ext"): void;
}>();

const isExpanded = ref(false);
const collectionName = ref(props.suggestedName);
const localHideSourceItems = ref(props.hideSourceItems);

const validInput = computed(() => {
    return collectionName.value.length > 0;
});

function clickForHelp() {
    isExpanded.value = !isExpanded.value;
    return isExpanded.value;
}

function cancelCreate() {
    props.oncancel();
}

watch(
    () => localHideSourceItems.value,
    () => {
        emit("onUpdateHideSourceItems", localHideSourceItems.value);
    }
);

const localDatatypeToggle = computed({
    get: () => {
        return props.datatypeToggle;
    },
    set: (newVal) => {
        emit("on-update-datatype-toggle", newVal);
    },
});
</script>

<template>
    <div class="collection-creator">
        <div class="header flex-row no-flex">
            <div class="main-help well clear" :class="{ expanded: isExpanded }">
                <a
                    class="more-help"
                    href="javascript:void(0);"
                    role="button"
                    :title="localize('Expand or Close Help')"
                    @click="clickForHelp">
                    <div v-if="!isExpanded">
                        <FontAwesomeIcon :icon="faChevronDown" />
                    </div>
                    <div v-else>
                        <FontAwesomeIcon :icon="faChevronUp" />
                    </div>
                </a>

                <div class="help-content">
                    <!-- each collection that extends this will add their own help content -->
                    <slot name="help-content"></slot>

                    <a
                        class="more-help"
                        href="javascript:void(0);"
                        role="button"
                        :title="localize('Expand or Close Help')"
                        @click="clickForHelp">
                    </a>
                </div>
            </div>
        </div>

        <div class="middle flex-row flex-row-container">
            <slot name="middle-content"></slot>
        </div>

        <div class="footer flex-row">
            <div class="vertically-spaced">
                <div class="d-flex align-items-center justify-content-between">
                    <BFormGroup
                        v-if="datatypeToggle"
                        class="flex-gapx-1 d-flex align-items-center"
                        label-for="datatype-toggle">
                        <template v-slot:label>
                            <HelpText
                                uri="galaxy.collections.collectionBuilder.filterForDatatypes"
                                :text="localize('Filter for Datatypes?')" />
                        </template>
                        <BFormRadioGroup
                            id="datatype-toggle"
                            v-model="localDatatypeToggle"
                            :options="datatypeToggleOptions"
                            size="sm"
                            buttons />
                    </BFormGroup>

                    <BAlert
                        v-if="extensions && localDatatypeToggle === 'ext'"
                        class="w-50 py-0"
                        variant="secondary"
                        show>
                        Filtered extensions: <strong>{{ orList(extensions) }}</strong>
                    </BAlert>
                </div>

                <div class="d-flex align-items-center justify-content-between">
                    <BFormGroup class="inputs-form-group">
                        <BFormCheckbox
                            v-if="renderExtensionsToggle"
                            name="remove-extensions"
                            switch
                            :checked="extensionsToggle"
                            @input="emit('remove-extensions-toggle')">
                            {{ localize("Remove file extensions?") }}
                        </BFormCheckbox>

                        <BFormCheckbox v-model="localHideSourceItems" name="hide-originals" switch>
                            <HelpText
                                uri="galaxy.collections.collectionBuilder.hideOriginalElements"
                                :text="localize('Hide original elements')" />
                        </BFormCheckbox>
                    </BFormGroup>

                    <BFormGroup
                        class="flex-gapx-1 d-flex align-items-center w-50 inputs-form-group"
                        :label="localize('Name:')"
                        label-for="collection-name">
                        <BFormInput
                            id="collection-name"
                            v-model="collectionName"
                            :placeholder="localize('Enter a name for your new collection')"
                            size="sm"
                            required
                            :state="!collectionName ? false : null" />
                    </BFormGroup>
                </div>
            </div>

            <div class="actions vertically-spaced d-flex justify-content-between">
                <BButton tabindex="-1" @click="cancelCreate">
                    {{ localize("Cancel") }}
                </BButton>

                <BButton
                    class="create-collection"
                    variant="primary"
                    :disabled="!validInput"
                    @click="emit('clicked-create', collectionName)">
                    {{ localize("Create collection") }}
                </BButton>
            </div>
        </div>
    </div>
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
    -webkit-user-select: none;
    -moz-user-select: none;
    -ms-user-select: none;
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
