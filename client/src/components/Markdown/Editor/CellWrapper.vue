<template>
    <div tabindex="0" role="presentation" @mouseenter="hover = true" @mouseleave="hover = false">
        <div class="d-flex">
            <ButtonPlain class="d-flex" :class="{ 'cell-wrapper-hover': hover }" @click="$emit('toggle')">
                <div class="align-self-end">
                    <CellButton v-if="toggle" title="Collapse" :icon="faAngleDoubleUp" />
                    <CellButton v-else title="Expand" :icon="faAngleDoubleDown" />
                </div>
            </ButtonPlain>
            <SectionWrapper
                class="m-2 w-100"
                :name="name"
                :content="content"
                :labels="labels"
                @change="$emit('change', $event)" />
        </div>
        <div v-if="toggle" class="d-flex">
            <div class="d-flex flex-column" :class="{ 'cell-wrapper-hover': hover }">
                <CellButton
                    v-if="configurable"
                    title="Attach Data"
                    :icon="faPaperclip"
                    :active="configure"
                    @click="$emit('configure')" />
                <CellAction
                    :name="name"
                    :cell-index="cellIndex"
                    :cell-total="cellTotal"
                    :configurable="configurable"
                    @clone="$emit('clone')"
                    @configure="$emit('configure')"
                    @delete="$emit('delete')"
                    @move="$emit('move', $event)" />
            </div>
            <div class="w-100 position-relative">
                <hr v-if="!configure" class="solid m-0" />
                <component
                    :is="configureComponent"
                    v-if="configure"
                    :class="{ 'cell-wrapper-hover': hover }"
                    :name="name"
                    :content="content"
                    :labels="labels"
                    @cancel="$emit('configure')"
                    @change="handleConfigure($event)" />
                <CellCode
                    v-else
                    :key="name"
                    class="mt-1"
                    :value="content"
                    :max-lines="30"
                    :mode="mode"
                    @change="$emit('change', $event)" />
                <small class="cell-wrapper-type position-absolute">
                    {{ VALID_TYPES.includes(name) ? name : "unknown" }}
                </small>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { faAngleDoubleDown, faAngleDoubleUp, faPaperclip } from "@fortawesome/free-solid-svg-icons";
import { computed, ref } from "vue";

import type { WorkflowLabel } from "./types";

import CellAction from "./CellAction.vue";
import CellButton from "./CellButton.vue";
import ConfigureGalaxy from "./Configurations/ConfigureGalaxy.vue";
import ConfigureVisualization from "./Configurations/ConfigureVisualization.vue";
import ConfigureVitessce from "./Configurations/ConfigureVitessce.vue";
import ButtonPlain from "@/components/Common/ButtonPlain.vue";
import SectionWrapper from "@/components/Markdown/Sections/SectionWrapper.vue";

const CellCode = () => import("./CellCode.vue");

const VALID_TYPES = ["galaxy", "markdown", "vega", "visualization", "vitessce"];

const props = defineProps<{
    cellIndex: number;
    cellTotal: number;
    configure?: boolean;
    content: string;
    labels?: Array<WorkflowLabel>;
    name: string;
    toggle?: boolean;
}>();

const emit = defineEmits(["change", "clone", "configure", "delete", "move", "toggle"]);

const hover = ref(false);

const configurable = computed(() => configureComponent.value !== undefined);

const configureComponent = computed(() => {
    switch (props.name) {
        case "galaxy":
            return ConfigureGalaxy;
        case "visualization":
            return ConfigureVisualization;
        case "vitessce":
            return ConfigureVitessce;
    }
    return undefined;
});

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

.cell-wrapper-hover {
    background-color: $gray-100;
}

.cell-wrapper-type {
    bottom: 0;
    color: $gray-500;
    right: 0;
}
</style>
