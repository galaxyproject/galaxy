<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faChevronDown, faChevronUp } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, ref } from "vue";

import WorkflowCard from "@/components/Workflow/List/WorkflowCard.vue";

library.add(faChevronDown, faChevronUp);

const props = defineProps({
    model: {
        type: Object,
        required: true,
    },
});

const expandAnnotations = ref(true);

const workflow = computed(() => {
    return {
        id: props.model.runData.id,
        name: props.model.runData.name,
        owner: props.model.runData.owner,
        tags: props.model.runData.annotation.tags.map((t: { user_tname: string }) => t.user_tname),
        annotations: [props.model.runData.annotation.annotation],
        update_time: props.model.runData.annotation.update_time,
    };
});
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
                <FontAwesomeIcon :icon="expandAnnotations ? faChevronUp : faChevronDown" fixed-width />
            </span>
        </div>
        <div class="portlet-content" :style="expandAnnotations ? 'display: none;' : ''">
            <WorkflowCard
                :workflow="workflow"
                :published-view="true"
                :grid-view="true"
                :show-actions="false"
                :class="'grid-view'" />
        </div>
    </div>
</template>
