<script setup lang="ts">
import { faCaretDown, faCaretUp, faTrashAlt } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BLink } from "bootstrap-vue";
import { computed } from "vue";

import type { FieldDict } from "@/api";
import localize from "@/utils/localization";

import FormRecordFieldDefinition from "./FormRecordFieldDefinition.vue";
import FormCard from "@/components/Form/FormCard.vue";

type FieldDefinitions = FieldDict[];

interface Props {
    value: FieldDefinitions;
}

const props = defineProps<Props>();

function addField() {
    const state = stateCopy();
    state.push({ type: "File", name: "field" });
    emit("onChange", state);
}

function stateCopy(): FieldDict[] {
    return JSON.parse(JSON.stringify(props.value || []));
}

function onRemove(index: number) {
    const state = stateCopy();
    state.splice(index, 1);
    emit("onChange", state);
}

function titleForFieldDefinition(index: number) {
    return `Field ${index + 1}`;
}

function getPrefix(index: number) {
    const name = `field_definition_${index}`;
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
        const wasSwapped = state[swapWith] as FieldDict;
        state[swapWith] = state[index] as FieldDict;
        state[index] = wasSwapped;
    }
    emit("onChange", state);
}

function onChildUpdate(childState: FieldDict, index: number) {
    const state = stateCopy();
    state[index] = childState;
    emit("onChange", state);
}

const deleteTooltip = computed(() => {
    return localize(`Click to delete field definition`);
});

const emit = defineEmits(["onChange"]);
</script>

<template>
    <div class="ui-form-element section-row">
        <div class="ui-form-title">
            <span class="ui-form-title-text">Record Fields</span>
        </div>
        <FormCard
            v-for="(fieldDefinition, index) in value"
            :key="index"
            data-description="field definition block"
            class="card"
            :title="titleForFieldDefinition(index)">
            <template v-slot:operations>
                <!-- code modelled after FormRepeat -->
                <span class="float-right">
                    <b-button-group>
                        <span v-b-tooltip.hover.bottom title="move down">
                            <b-button
                                :id="getButtonId(index, 'up')"
                                v-b-tooltip.hover.bottom
                                title="move up"
                                role="button"
                                variant="link"
                                size="sm"
                                class="ml-0"
                                @click="() => swap(index, index - 1, 'up')">
                                <FontAwesomeIcon :icon="faCaretUp" />
                            </b-button>
                        </span>
                        <span v-b-tooltip.hover.bottom title="move down">
                            <b-button
                                :id="getButtonId(index, 'down')"
                                v-b-tooltip.hover.bottom
                                title="move down"
                                role="button"
                                variant="link"
                                size="sm"
                                class="ml-0"
                                @click="() => swap(index, index + 1, 'down')">
                                <FontAwesomeIcon :icon="faCaretDown" />
                            </b-button>
                        </span>
                    </b-button-group>
                    <span v-b-tooltip.hover.bottom :title="deleteTooltip">
                        <b-button
                            title="delete"
                            role="button"
                            variant="link"
                            size="sm"
                            class="ml-0"
                            @click="() => onRemove(index)">
                            <FontAwesomeIcon :icon="faTrashAlt" />
                        </b-button>
                    </span>
                </span>
            </template>
            <template v-slot:body>
                <FormRecordFieldDefinition
                    :index="index"
                    :value="fieldDefinition"
                    :prefix="getPrefix(index)"
                    @onChange="onChildUpdate" />
            </template>
        </FormCard>
        <BLink @click="addField">Add field.</BLink>
    </div>
</template>

<style lang="scss" scoped>
@import "../../../Form/_form-elements.scss";
</style>
