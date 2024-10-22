<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faChevronDown, faChevronUp } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, ref, watch } from "vue";

import localize from "@/utils/localization";

library.add(faChevronDown, faChevronUp);

interface Props {
    oncancel: () => void;
    hideSourceItems: boolean;
    suggestedName?: string;
    renderExtensionsToggle?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    suggestedName: "",
});

const emit = defineEmits<{
    (e: "remove-extensions-toggle"): void;
    (e: "clicked-create", value: string): void;
    (e: "onUpdateHideSourceItems", value: boolean): void;
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

        <div class="footer flex-row no-flex">
            <div class="attributes clear">
                <div class="clear">
                    <label v-if="renderExtensionsToggle" class="setting-prompt float-right">
                        {{ localize("Remove file extensions?") }}
                        <input
                            class="remove-extensions float-right"
                            type="checkbox"
                            checked
                            @click="emit('remove-extensions-toggle')" />
                    </label>

                    <label class="setting-prompt float-right">
                        {{ localize("Hide original elements?") }}
                        <input v-model="localHideSourceItems" class="hide-originals float-right" type="checkbox" />
                    </label>
                </div>

                <div class="clear">
                    <input
                        v-model="collectionName"
                        class="collection-name form-control float-right"
                        :placeholder="localize('Enter a name for your new collection')" />

                    <div class="collection-name-prompt float-right">
                        {{ localize("Name:") }}
                    </div>
                </div>
            </div>

            <div class="actions clear vertically-spaced">
                <div class="float-left">
                    <button class="cancel-create btn" tabindex="-1" @click="cancelCreate">
                        {{ localize("Cancel") }}
                    </button>
                </div>

                <div class="main-options float-right">
                    <button
                        class="create-collection btn btn-primary"
                        :disabled="!validInput"
                        @click="emit('clicked-create', collectionName)">
                        {{ localize("Create collection") }}
                    </button>
                </div>
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
        .attributes {
            .setting-prompt {
                //margin-right: 32px;
                line-height: 32px;
                padding-left: 10px;
                .remove-extensions {
                    display: inline-block;
                    width: 24px;
                    height: 24px;
                }
                .hide-originals {
                    display: inline-block;
                    width: 24px;
                    height: 24px;
                }
            }
            // actually appears/floats to the left of the input
            .collection-name-prompt {
                margin: 5px 4px 0 0;
            }
            .collection-name-prompt.validation-warning:before {
                //TODO: localize (somehow)
                content: "(required)";
                margin-right: 4px;
                color: red;
            }
            .collection-name {
                width: 50%;
                &.validation-warning {
                    border-color: red;
                }
            }
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
