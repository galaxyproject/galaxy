<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import {
    faEdit,
    faEye,
    faGlobe,
    faLink,
    faPen,
    faShieldAlt,
    faSitemap,
    faUser,
    faUsers,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";
import { computed, ref } from "vue";
import { useRouter } from "vue-router/composables";

import { useUserStore } from "@/stores/userStore";

import TextSummary from "@/components/Common/TextSummary.vue";
import StatelessTags from "@/components/Tags/StatelessTags.vue";
import WorkflowActions from "@/components/Workflow/WorkflowActions.vue";
import WorkflowIndicators from "@/components/Workflow/WorkflowIndicators.vue";
import WorkflowInvocationsCount from "@/components/Workflow/WorkflowInvocationsCount.vue";
import WorkflowQuickView from "@/components/Workflow/WorkflowQuickView.vue";
import WorkflowRename from "@/components/Workflow/WorkflowRename.vue";
import WorkflowRunButton from "@/components/Workflow/WorkflowRunButton.vue";

library.add(faEdit, faEye, faGlobe, faLink, faPen, faShieldAlt, faSitemap, faUser, faUsers);

interface Props {
    workflow: any;
    gridView?: boolean;
    publishedView?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    gridView: false,
    publishedView: false,
});

const emit = defineEmits<{
    (e: "refreshList", a?: boolean): void;
    (e: "tagClick", a: { text: string }): void;
}>();

const router = useRouter();
const userStore = useUserStore();

const showRename = ref(false);
const showPreview = ref(false);
const showControls = ref(false);

const shared = computed(() => {
    if (userStore.currentUser) {
        return userStore.currentUser.username !== props.workflow.owner;
    } else {
        return false;
    }
});
const description = computed(() => {
    if (props.workflow.annotations && props.workflow.annotations.length > 0) {
        return props.workflow.annotations[0].trim();
    } else {
        return null;
    }
});

function onEdit() {
    router.push(`/workflows/edit?id=${props.workflow.id}`);
}

function onRenameClose(newName: string) {
    showRename.value = false;
    emit("refreshList", true);
}

function toggleShowPreview(val: boolean = false) {
    showPreview.value = val;
}
</script>

<template>
    <div class="workflow-card" @mouseenter="showControls = true" @mouseleave="showControls = false">
        <BRow class="align-items-center" align-v="baseline" no-gutters>
            <BCol cols="12" md="9">
                <BRow align-v="center" no-gutters>
                    <WorkflowIndicators :workflow="workflow" :published-view="publishedView" />
                </BRow>

                <BRow no-gutters>
                    <span class="workflow-name font-weight-bold"> {{ workflow.name }} </span>

                    <BButton
                        v-if="!shared && !workflow.deleted"
                        id="rename-button"
                        v-b-tooltip.top
                        :class="{ 'mouse-out': !showControls }"
                        variant="link"
                        size="sm"
                        title="Rename workflow"
                        @click="showRename = !showRename">
                        <FontAwesomeIcon :icon="faPen" />
                    </BButton>
                </BRow>
            </BCol>

            <BCol>
                <BRow align-h="end" justify="end" no-gutters>
                    <BCol>
                        <BRow align-h="end" no-gutters>
                            <WorkflowActions
                                :workflow="workflow"
                                :show-controls="showControls"
                                @refreshList="emit('refreshList', true)"
                                @toggleShowPreview="toggleShowPreview" />
                        </BRow>

                        <BRow v-if="gridView" class="pb-2" align-h="end" no-gutters>
                            <BButton
                                id="view-button"
                                v-b-tooltip.top
                                :class="{ 'mouse-out': !showControls }"
                                variant="link"
                                size="sm"
                                title="View workflow"
                                @click="toggleShowPreview(true)">
                                <FontAwesomeIcon :icon="faEye" />
                            </BButton>
                        </BRow>

                        <BRow align-h="end" no-gutters>
                            <WorkflowInvocationsCount :workflow="workflow" />
                        </BRow>
                    </BCol>
                </BRow>
            </BCol>
        </BRow>

        <BRow v-if="description" class="text-summary" no-gutters>
            <TextSummary :description="description" :max-length="gridView ? 100 : 250" />
        </BRow>

        <BRow no-gutters>
            <BCol class="d-flex align-items-center" sm="6" cols="8">
                <BRow align-h="end" no-gutters>
                    <StatelessTags
                        clickable
                        :value="workflow.tags"
                        :disabled="workflow.deleted"
                        :max-visible-tags="gridView ? 2 : 8"
                        @tag-click="emit('tagClick', $event)" />
                </BRow>
            </BCol>

            <BCol align-self="end" class="text-right" sm="6" cols="4">
                <BButton
                    v-if="!shared && !workflow.deleted"
                    v-b-tooltip.hover
                    size="sm"
                    class="mx-2"
                    title="Edit workflow"
                    variant="outline-primary"
                    @click="onEdit">
                    <FontAwesomeIcon :icon="faEdit" />
                    Edit
                </BButton>

                <WorkflowRunButton :id="workflow.id" />
            </BCol>
        </BRow>

        <WorkflowRename
            v-if="!shared && !workflow.deleted"
            :id="workflow.id"
            :show="showRename"
            :name="workflow.name"
            @close="onRenameClose" />

        <BModal
            v-model="showPreview"
            ok-only
            size="xl"
            hide-header
            modal-class="workflow-preview-modal"
            dialog-class="workflow-preview-modal w-auto"
            centered>
            <WorkflowQuickView :id="workflow.id" :show="showPreview" @ok="toggleShowPreview(false)" />
        </BModal>
    </div>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";

.workflow-card {
    background-color: white;
    border: 1px solid #e5e5e5;
    border-radius: 0.5rem;
    padding: 0.5rem;
    margin: 0rem 0.5rem;

    .text-summary {
        height: inherit;
    }

    .workflow-name {
        font-size: 1rem;
    }

    .mouse-out {
        opacity: 0.5;
    }

    .workflow-preview-modal {
        min-width: max-content;
    }
}
</style>
