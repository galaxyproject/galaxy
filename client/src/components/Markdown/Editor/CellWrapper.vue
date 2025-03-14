<template>
    <div @mouseenter="hover = true" @mouseleave="hover = false">
        <div class="d-flex">
            <div class="d-flex flex-column cursor-pointer" :class="{ 'cell-hover': hover }" @click="$emit('toggle')">
                <CellButton v-if="toggle" title="Collapse" :icon="faAngleDoubleUp" />
                <CellButton v-else title="Expand" :icon="faAngleDoubleDown" />
            </div>
            <div class="w-100">
                <div class="m-2">
                    <MarkdownDefault v-if="name === 'markdown'" :content="content" />
                    <MarkdownGalaxy v-else-if="name === 'galaxy'" :content="content" />
                    <b-alert v-else variant="danger" show> This cell type `{{ name }}` is not available. </b-alert>
                </div>
            </div>
        </div>
        <div v-if="toggle" class="d-flex">
            <div class="d-flex flex-column" :class="{ 'cell-hover': hover }">
                <CellButton
                    v-if="name !== 'markdown'"
                    title="Attach Data"
                    :active="configure"
                    :icon="faPaperclip"
                    :show="hover"
                    @click="$emit('configure')" />
                <CellButton title="Clone Cell" :show="hover" :icon="faClone" @click="$emit('clone')" />
                <CellButton title="Delete Cell" :show="hover" :icon="faTrash" @click="confirmDelete = true" />
                <CellButton
                    title="Move Up"
                    :disabled="cellIndex < 1"
                    :icon="faArrowUp"
                    :show="hover"
                    @click="$emit('move', 'up')" />
                <CellButton
                    title="Move Down"
                    :disabled="cellTotal - cellIndex < 2"
                    :icon="faArrowDown"
                    :show="hover"
                    @click="$emit('move', 'down')" />
            </div>
            <div class="w-100">
                <hr class="solid m-0" />
                <ConfigureGalaxy
                    v-if="name === 'galaxy' && configure"
                    :name="name"
                    :content="content"
                    @cancel="$emit('configure')"
                    @change="handleConfigure($event)" />
                <CellCode :key="name" class="mt-1" :value="content" :mode="mode" @change="$emit('change', $event)" />
            </div>
        </div>
        <BModal v-model="confirmDelete" title="Delete Cell" title-tag="h2" @ok="$emit('delete')">
            <p v-localize>Are you sure you want to delete this cell?</p>
        </BModal>
    </div>
</template>

<script setup lang="ts">
import {
    faAngleDoubleDown,
    faAngleDoubleUp,
    faArrowDown,
    faArrowUp,
    faClone,
    faPaperclip,
    faTrash,
} from "@fortawesome/free-solid-svg-icons";
import { BModal } from "bootstrap-vue";
import { computed, ref } from "vue";

import MarkdownDefault from "../Sections/MarkdownDefault.vue";
import MarkdownGalaxy from "../Sections/MarkdownGalaxy.vue";
import CellButton from "./CellButton.vue";
import CellCode from "./CellCode.vue";
import ConfigureGalaxy from "./Configurations/ConfigureGalaxy.vue";

const props = defineProps<{
    cellIndex: number;
    cellTotal: number;
    configure?: boolean;
    content: string;
    name: string;
    toggle?: boolean;
}>();

const emit = defineEmits(["change", "clone", "configure", "delete", "move", "toggle"]);

const confirmDelete = ref(false);
const hover = ref(false);

const mode = computed(() => {
    switch (props.name) {
        case "galaxy":
            return "python";
        case "markdown":
            return "markdown";
    }
    return "json";
});

function handleConfigure(newValue: string) {
    emit("change", newValue);
    emit("configure");
}
</script>

<style lang="scss">
@import "theme/blue.scss";

.cell-hover {
    background-color: $gray-100;
}
</style>
