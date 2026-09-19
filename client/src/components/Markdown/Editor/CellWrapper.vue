<template>
    <div tabindex="0" role="presentation" @mouseenter="hover = true" @mouseleave="hover = false">
        <div class="d-flex">
            <div class="d-flex flex-column justify-content-end px-1" :class="{ 'cell-wrapper-hover': hover }">
                <GButtonGroup vertical class="py-1">
                    <GButton
                        transparent
                        :pressed="toggle"
                        color="blue"
                        icon-only
                        tooltip
                        tooltip-placement="right"
                        :title="toggle ? 'Collapse Editor' : 'Edit Cell'"
                        @click="$emit('toggle')">
                        <FontAwesomeIcon :icon="toggle ? faAngleDoubleUp : faEdit" fixed-width />
                    </GButton>
                    <CellAdd title="Insert Cell Below" @click="$emit('add-after', $event)" />
                </GButtonGroup>
            </div>
            <SectionWrapper
                class="m-2 w-100"
                :name="name"
                :content="content"
                :labels="labels"
                @change="$emit('change', $event)" />
        </div>
        <div v-if="toggle" class="d-flex">
            <GButtonGroup vertical class="py-1 px-1" :class="{ 'cell-wrapper-hover': hover }">
                <GButton
                    v-if="configurable"
                    transparent
                    color="blue"
                    icon-only
                    tooltip
                    tooltip-placement="right"
                    title="Attach Data"
                    :pressed="configure"
                    @click="$emit('configure')">
                    <FontAwesomeIcon :icon="faPaperclip" fixed-width />
                </GButton>
                <CellAction
                    :name="name"
                    :cell-index="cellIndex"
                    :cell-total="cellTotal"
                    :configurable="configurable"
                    @clone="$emit('clone')"
                    @configure="$emit('configure')"
                    @delete="$emit('delete')"
                    @move="$emit('move', $event)" />
            </GButtonGroup>
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
import { faAngleDoubleUp, faEdit, faPaperclip } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, ref } from "vue";

import type { WorkflowLabel } from "./types";

import CellAction from "./CellAction.vue";
import CellAdd from "./CellAdd.vue";
import ConfigureGalaxy from "./Configurations/ConfigureGalaxy.vue";
import ConfigureVisualization from "./Configurations/ConfigureVisualization.vue";
import ConfigureVitessce from "./Configurations/ConfigureVitessce.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import GButtonGroup from "@/components/BaseComponents/GButtonGroup.vue";
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

const emit = defineEmits(["add-after", "change", "clone", "configure", "delete", "move", "toggle"]);

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
@import "@/style/scss/theme/blue.scss";

.cell-wrapper-hover {
    background-color: $gray-100;
}

.cell-wrapper-type {
    bottom: 0;
    color: $gray-500;
    right: 0;
}
</style>
