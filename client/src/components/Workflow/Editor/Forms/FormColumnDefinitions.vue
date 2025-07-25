<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCaretDown, faCaretUp, faPlus, faTrashAlt } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BLink } from "bootstrap-vue";
import { computed } from "vue";

import type { SampleSheetColumnDefinition, SampleSheetColumnDefinitions } from "@/api";
import type { SampleSheetCollectionType } from "@/api/datasetCollections";
import { downloadWorkbook } from "@/components/Collections/sheet/workbooks";
import localize from "@/utils/localization";

import FormColumnDefinition from "./FormColumnDefinition.vue";
import DownloadWorkbookButton from "@/components/Collections/sheet/DownloadWorkbookButton.vue";
import FormCard from "@/components/Form/FormCard.vue";

library.add(faPlus, faTrashAlt, faCaretUp, faCaretDown);

interface Props {
    value: SampleSheetColumnDefinitions;
    collectionType: SampleSheetCollectionType;
}

const props = defineProps<Props>();

function addColumn() {
    const state = stateCopy();
    state.push({ type: "string", name: "column", optional: false, description: "" });
    emit("onChange", state);
}

function stateCopy(): SampleSheetColumnDefinition[] {
    return JSON.parse(JSON.stringify(props.value || []));
}

function onRemove(index: number) {
    const state = stateCopy();
    state.splice(index, 1);
    emit("onChange", state);
}

function titleForColumnDefinition(index: number) {
    return `Column ${index + 1}`;
}

function getPrefix(index: number) {
    const name = `column_definition_${index}`;
    return name;
}

function getButtonId(index: number, direction: "up" | "down") {
    const prefix = getPrefix(index);
    return `${prefix}_${direction}`;
}

function swap(index: number, swapWith: number, direction: "up" | "down") {
    // the FormRepeat version does cool highlighting - probably worth implementing
    // on next pass
    const state = stateCopy();
    if (swapWith >= 0 && swapWith < state.length && index >= 0 && index < state.length) {
        const wasSwapped = state[swapWith] as SampleSheetColumnDefinition;
        state[swapWith] = state[index] as SampleSheetColumnDefinition;
        state[index] = wasSwapped;
    }
    emit("onChange", state);
}

function onChildUpdate(childState: SampleSheetColumnDefinition, index: number) {
    const state = stateCopy();
    state[index] = childState;
    emit("onChange", state);
}

const deleteTooltip = computed(() => {
    return localize(`Click to delete column definition`);
});

const saveTooltip = computed(() => {
    return localize(`Click to download an example workbook (xlsx file) for these columns`);
});

const emit = defineEmits(["onChange"]);
</script>

<template>
    <div class="ui-form-element section-row" data-description="edit column definitions">
        <div class="ui-form-title">
            <span class="ui-form-title-text">Column definitions</span>
            <span v-b-tooltip.hover.bottom :title="saveTooltip">
                <DownloadWorkbookButton
                    title="download example workbook"
                    @click="downloadWorkbook(value, props.collectionType)" />
            </span>
        </div>
        <FormCard
            v-for="(columnDefinition, index) in value"
            v-bind:key="index"
            data-description="column definition block"
            class="card"
            :title="titleForColumnDefinition(index)">
            <template v-slot:operations>
                <!-- code modelled after FormRepeat -->
                <span class="float-right">
                    <b-button-group>
                        <b-button
                            :id="getButtonId(index, 'up')"
                            v-b-tooltip.hover.bottom
                            title="move up"
                            role="button"
                            variant="link"
                            size="sm"
                            class="ml-0"
                            @click="() => swap(index, index - 1, 'up')">
                            <FontAwesomeIcon icon="caret-up" />
                        </b-button>
                        <b-button
                            :id="getButtonId(index, 'down')"
                            v-b-tooltip.hover.bottom
                            title="move down"
                            role="button"
                            variant="link"
                            size="sm"
                            class="ml-0"
                            @click="() => swap(index, index + 1, 'down')">
                            <FontAwesomeIcon icon="caret-down" />
                        </b-button>
                    </b-button-group>

                    <span v-b-tooltip.hover.bottom :title="deleteTooltip">
                        <b-button
                            title="delete"
                            role="button"
                            variant="link"
                            size="sm"
                            class="ml-0"
                            @click="() => onRemove(index)">
                            <FontAwesomeIcon icon="trash-alt" />
                        </b-button>
                    </span>
                </span>
            </template>
            <template v-slot:body>
                <FormColumnDefinition
                    :index="index"
                    :value="columnDefinition"
                    :prefix="getPrefix(index)"
                    @onChange="onChildUpdate" />
            </template>
        </FormCard>
        <BLink data-description="edit column definitions add" @click="addColumn">Add column.</BLink>
    </div>
</template>

<style lang="scss" scoped>
@import "../../../Form/_form-elements.scss";

.column-definition-list {
    padding: 0px;
    list-style-type: none;
}
</style>
