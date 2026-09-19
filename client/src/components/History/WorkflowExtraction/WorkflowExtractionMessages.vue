<script setup lang="ts">
import { faExclamationTriangle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BPopover } from "bootstrap-vue";
import { ref } from "vue";

import GButton from "@/components/BaseComponents/GButton.vue";

const props = defineProps<{
    warnings: string[];
}>();

const showWarningsPopover = ref(false);
const warningsContext = ref<"alert" | "popover">("alert");

// TODO: Replace with GPopover when that is implemented
</script>

<template>
    <div>
        <div class="my-2 d-flex flex-gapx-1 align-items-start">
            <span>
                The following list contains each tool that was run to create the datasets in your current history.
                Please select those that you wish to include in the workflow.
            </span>

            <GButton
                v-if="props.warnings.length && warningsContext === 'popover'"
                id="workflow-extraction-warnings-popover"
                color="orange"
                icon-only
                transparent
                inline
                style="cursor: help"
                @click="showWarningsPopover = !showWarningsPopover">
                <FontAwesomeIcon :icon="faExclamationTriangle" fixed-width />
            </GButton>
            <BPopover
                v-if="props.warnings.length && warningsContext === 'popover'"
                :show.sync="showWarningsPopover"
                boundary="window"
                placement="bottom"
                target="workflow-extraction-warnings-popover"
                triggers="hover">
                <div class="d-flex flex-column flex-gapy-1 text-center">
                    <div v-for="(warning, index) in props.warnings" :key="index">{{ warning }}</div>
                </div>
            </BPopover>
        </div>
        <BAlert
            v-if="props.warnings.length && warningsContext === 'alert'"
            variant="warning"
            fade
            show
            dismissible
            @dismissed="warningsContext = 'popover'">
            <div v-for="(warning, index) in props.warnings" :key="index">{{ warning }}</div>
        </BAlert>
    </div>
</template>
