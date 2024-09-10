<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert } from "bootstrap-vue";
import { onMounted, ref } from "vue";

import { getWorkflowInfo } from "@/components/Workflow/workflows.services";

import { errorMessageAsString } from "../../../utils/simple-error";

import WorkflowInformation from "@/components/Workflow/Published/WorkflowInformation.vue";

const props = defineProps({
    model: {
        type: Object,
        required: true,
    },
});

const loading = ref(true);
const messageText = ref<string | null>(null);
const messageVariant = ref<string | null>(null);
const expandAnnotations = ref(true);
const workflowInfoData = ref(null);

onMounted(() => {
    loadAnnotation();
});

async function loadAnnotation() {
    loading.value = true;

    try {
        const workflowInfoDataPromise = getWorkflowInfo(props.model.runData.id);
        workflowInfoData.value = await workflowInfoDataPromise;
    } catch (e) {
        messageVariant.value = "danger";
        messageText.value = errorMessageAsString(e, "Failed to fetch Workflow Annotation.");
    } finally {
        loading.value = false;
    }
}
</script>

<template>
    <div class="ui-portlet-section w-100">
        <div
            class="portlet-header cursor-pointer"
            role="button"
            :tabindex="0"
            @keyup.enter="expandAnnotations = !expandAnnotations"
            @click="expandAnnotations = !expandAnnotations">
            <b class="portlet-operations portlet-title-text">
                <span v-localize class="font-weight-bold">About This Workflow</span>
            </b>
            <span v-b-tooltip.hover.bottom title="Collapse/Expand" variant="link" size="sm" class="float-right">
                <FontAwesomeIcon :icon="expandAnnotations ? 'chevron-up' : 'chevron-down'" class="fa-fw" />
            </span>
        </div>
        <div class="portlet-content" :style="expandAnnotations ? 'display: none;' : ''">
            <WorkflowInformation
                v-if="workflowInfoData"
                class="workflow-information-container"
                :workflow-info="workflowInfoData"
                :embedded="false" />
            <BAlert v-else :show="messageText" :variant="messageVariant">
                {{ messageText }}
            </BAlert>
        </div>
    </div>
</template>
