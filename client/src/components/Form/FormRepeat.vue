<script setup>
import Draggable from "vuedraggable";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import FormCard from "./FormCard";
import { defineAsyncComponent, computed } from "vue";

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

const emit = defineEmits("insert", "delete", "changed");

const cache = computed({
    get() {
        return props.input.cache;
    },
    set(val) {
        emit("changed");
    },
});

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
</script>

<script>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faPlus, faTrashAlt } from "@fortawesome/free-solid-svg-icons";

library.add(faPlus, faTrashAlt);
</script>

<template>
    <div>
        <div v-if="!props.sustainRepeats || (cache && cache.length > 0)">
            <div class="font-weight-bold mb-2">{{ props.input.title }}</div>
            <div v-if="props.input.help" class="mb-2" data-description="repeat help">{{ props.input.help }}</div>
        </div>
        <Draggable v-model="cache" draggable="card">
            <FormCard
                v-for="(cache, cacheId) in cache"
                :key="cacheId"
                data-description="repeat block"
                class="card"
                :title="getTitle(cacheId)">
                <template v-slot:operations>
                    <b-button
                        v-if="!props.sustainRepeats"
                        v-b-tooltip.hover.bottom
                        role="button"
                        variant="link"
                        size="sm"
                        class="float-right"
                        @click="onDelete(cacheId)">
                        <FontAwesomeIcon icon="trash-alt" />
                    </b-button>
                </template>

                <template v-slot:body>
                    <FormNode v-bind="props.passthroughProps" :inputs="cache" :prefix="getPrefix(cacheId)" />
                </template>
            </FormCard>

            <b-button v-if="!props.sustainRepeats" slot="footer" @click="onInsert()">
                <font-awesome-icon icon="plus" class="mr-1" />
                <span data-description="repeat insert">Insert {{ props.input.title || "Repeat" }}</span>
            </b-button>
        </Draggable>
    </div>
</template>
