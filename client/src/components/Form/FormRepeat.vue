<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCaretDown, faCaretUp, faPlus, faTrashAlt } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { defineAsyncComponent, nextTick, type PropType } from "vue";
import { computed } from "vue";

import { useKeyedObjects } from "@/composables/keyedObjects";
import localize from "@/utils/localization";

import FormCard from "./FormCard.vue";

const FormNode = defineAsyncComponent(() => import("./FormInputs.vue"));

interface Input {
    name: string;
    title: string;
    min: number;
    default: number;
    max: number | string;
    help?: string;
    cache: Array<Record<string, unknown>>;
}

const maxRepeats = computed(() => {
    return typeof props.input.max === "number" ? props.input.cache?.length >= props.input.max : false;
});

const minRepeats = computed(() => {
    return typeof props.input.min === "number" ? props.input.cache?.length > props.input.min : true;
});

const buttonTooltip = computed(() => {
    return maxRepeats.value
        ? localize(`Maximum number of ${props.input.title || "Repeat"} fields reached`)
        : localize(`Click to add ${props.input.title || "Repeat"} fields`);
});

const deleteTooltip = computed(() => {
    return !minRepeats.value
        ? localize(`Minimum number of ${props.input.title || "Repeat"} fields reached`)
        : localize(`Click to delete ${props.input.title || "Repeat"} fields`);
});

const props = defineProps({
    input: {
        type: Object as PropType<Input>,
        required: true,
    },
    sustainRepeats: {
        type: Boolean,
        default: false,
    },
    passthroughProps: {
        type: Object,
        required: true,
    },
    prefix: {
        type: String,
        default: null,
    },
});

const emit = defineEmits<{
    (e: "insert"): void;
    (e: "delete", index: number): void;
    (e: "swap", a: number, b: number): void;
}>();

// @ts-ignore: bad library types
library.add(faPlus, faTrashAlt, faCaretUp, faCaretDown);

function onInsert() {
    emit("insert");
}

function onDelete(index: number) {
    emit("delete", index);
}

function getPrefix(index: number) {
    const name = `${props.input.name}_${index}`;

    if (props.prefix) {
        return `${props.prefix}|${name}`;
    } else {
        return name;
    }
}

function getTitle(index: number) {
    return `${index + 1}: ${props.input.title}`;
}

/** swap blocks if possible */
async function swap(index: number, swapWith: number, direction: "up" | "down") {
    if (swapWith >= 0 && swapWith < props.input.cache?.length) {
        emit("swap", index, swapWith);

        await nextTick();

        const buttonId = getButtonId(swapWith, direction);
        document.getElementById(buttonId)?.focus();
    }
}

/** get a uid for the up/down button */
function getButtonId(index: number, direction: "up" | "down") {
    const prefix = getPrefix(index);
    return `${prefix}_${direction}`;
}

const { keyObject } = useKeyedObjects();
</script>

<template>
    <div>
        <div v-if="!props.sustainRepeats || props.input.cache?.length > 0">
            <div class="font-weight-bold mb-2">{{ props.input.title }}</div>
            <div v-if="props.input.help" class="mb-2" data-description="repeat help">{{ props.input.help }}</div>
        </div>

        <FormCard
            v-for="(cache, cacheId) in props.input.cache"
            :key="keyObject(cache)"
            data-description="repeat block"
            class="card"
            :title="getTitle(cacheId)">
            <template v-slot:operations>
                <span v-if="!props.sustainRepeats" class="float-right">
                    <b-button-group>
                        <b-button
                            :id="getButtonId(cacheId, 'up')"
                            v-b-tooltip.hover.bottom
                            title="move up"
                            role="button"
                            variant="link"
                            size="sm"
                            class="ml-0"
                            @click="() => swap(cacheId, cacheId - 1, 'up')">
                            <FontAwesomeIcon icon="caret-up" />
                        </b-button>
                        <b-button
                            :id="getButtonId(cacheId, 'down')"
                            v-b-tooltip.hover.bottom
                            title="move down"
                            role="button"
                            variant="link"
                            size="sm"
                            class="ml-0"
                            @click="() => swap(cacheId, cacheId + 1, 'down')">
                            <FontAwesomeIcon icon="caret-down" />
                        </b-button>
                    </b-button-group>

                    <span v-b-tooltip.hover.bottom :title="deleteTooltip">
                        <b-button
                            :disabled="!minRepeats"
                            title="delete"
                            role="button"
                            variant="link"
                            size="sm"
                            class="ml-0"
                            @click="() => onDelete(cacheId)">
                            <FontAwesomeIcon icon="trash-alt" />
                        </b-button>
                    </span>
                </span>
            </template>

            <template v-slot:body>
                <FormNode v-bind="props.passthroughProps" :inputs="cache" :prefix="getPrefix(cacheId)" />
            </template>
        </FormCard>

        <span v-b-tooltip.hover :title="buttonTooltip">
            <b-button v-if="!props.sustainRepeats" :disabled="maxRepeats" @click="onInsert">
                <FontAwesomeIcon icon="plus" class="mr-1" />
                <span data-description="repeat insert">Insert {{ props.input.title || "Repeat" }}</span>
            </b-button>
        </span>
    </div>
</template>
