<script setup>
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import FormCard from "./FormCard";
import { defineAsyncComponent } from "vue";

const FormNode = defineAsyncComponent(() => import("./FormInputs.vue"));

const props = defineProps({
    input: {
        type: Object,
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

const emit = defineEmits("insert", "delete", "swap");

function onInsert() {
    emit("insert");
}

function onDelete(index) {
    emit("delete", index);
}

function getPrefix(index) {
    const name = `${props.input.name}_${index}`;

    if (props.prefix) {
        return `${props.prefix}|${name}`;
    } else {
        return name;
    }
}

function getTitle(index) {
    return `${parseInt(index) + 1}: ${props.input.title}`;
}

/** swap blocks if possible */
function swap(index, swapWith, up) {
    if (swapWith >= 0 && swapWith < props.input.cache?.length) {
        emit("swap", index, swapWith);

        const buttonId = getButtonId(swapWith, up);
        document.getElementById(buttonId).focus();
    }
}

/** get a uid for the up/down button */
function getButtonId(index, up) {
    const prefix = getPrefix(index);
    return `${prefix}_${up ? "up" : "down"}`;
}
</script>

<script>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faPlus, faTrashAlt, faCaretUp, faCaretDown } from "@fortawesome/free-solid-svg-icons";

library.add(faPlus, faTrashAlt, faCaretUp, faCaretDown);
</script>

<template>
    <div>
        <div v-if="!props.sustainRepeats || props.input.cache?.length > 0">
            <div class="font-weight-bold mb-2">{{ props.input.title }}</div>
            <div v-if="props.input.help" class="mb-2" data-description="repeat help">{{ props.input.help }}</div>
        </div>

        <FormCard
            v-for="(cache, cacheId) in props.input.cache"
            :key="cacheId"
            data-description="repeat block"
            class="card"
            :title="getTitle(cacheId)">
            <template v-slot:operations>
                <span v-if="!props.sustainRepeats" class="float-right">
                    <b-button-group>
                        <b-button
                            v-b-tooltip.hover.bottom
                            title="move up"
                            role="button"
                            variant="link"
                            size="sm"
                            class="ml-0"
                            :id="getButtonId(cacheId, true)"
                            @click="() => swap(cacheId, cacheId - 1, true)">
                            <FontAwesomeIcon icon="caret-up" />
                        </b-button>
                        <b-button
                            v-b-tooltip.hover.bottom
                            title="move down"
                            role="button"
                            variant="link"
                            size="sm"
                            class="ml-0"
                            :id="getButtonId(cacheId, false)"
                            @click="() => swap(cacheId, cacheId + 1, false)">
                            <FontAwesomeIcon icon="caret-down" />
                        </b-button>
                    </b-button-group>

                    <b-button
                        v-b-tooltip.hover.bottom
                        title="delete"
                        role="button"
                        variant="link"
                        size="sm"
                        class="ml-0"
                        @click="() => onDelete(cacheId)">
                        <FontAwesomeIcon icon="trash-alt" />
                    </b-button>
                </span>
            </template>

            <template v-slot:body>
                <FormNode v-bind="props.passthroughProps" :inputs="cache" :prefix="getPrefix(cacheId)" />
            </template>
        </FormCard>

        <b-button v-if="!props.sustainRepeats" @click="onInsert">
            <font-awesome-icon icon="plus" class="mr-1" />
            <span data-description="repeat insert">Insert {{ props.input.title || "Repeat" }}</span>
        </b-button>
    </div>
</template>
