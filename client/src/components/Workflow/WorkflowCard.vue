<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faEdit, faEye, faPen, faUpload } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";
import { computed, ref } from "vue";
import { useRouter } from "vue-router/composables";

import { copyWorkflow, updateWorkflow } from "@/components/Workflow/workflows.services";
import { Toast } from "@/composables/toast";
import { useUserStore } from "@/stores/userStore";

import TextSummary from "@/components/Common/TextSummary.vue";
import StatelessTags from "@/components/Tags/StatelessTags.vue";
import WorkflowActions from "@/components/Workflow/WorkflowActions.vue";
import WorkflowActionsExtend from "@/components/Workflow/WorkflowActionsExtend.vue";
import WorkflowIndicators from "@/components/Workflow/WorkflowIndicators.vue";
import WorkflowInvocationsCount from "@/components/Workflow/WorkflowInvocationsCount.vue";
import WorkflowQuickView from "@/components/Workflow/WorkflowQuickView.vue";
import WorkflowRename from "@/components/Workflow/WorkflowRename.vue";
import WorkflowRunButton from "@/components/Workflow/WorkflowRunButton.vue";

library.add(faEdit, faEye, faPen, faUpload);

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
    (e: "refreshList", a?: boolean, b?: boolean): void;
    (e: "tagClick", a: { text: string }): void;
}>();

const router = useRouter();
const userStore = useUserStore();

const showRename = ref(false);
const showPreview = ref(false);

const workflow = computed(() => props.workflow);
const shared = computed(() => {
    if (userStore.currentUser) {
        return userStore.currentUser.username !== workflow.value.owner;
    } else {
        return false;
    }
});
const description = computed(() => {
    if (workflow.value.annotations && workflow.value.annotations.length > 0) {
        return workflow.value.annotations[0].trim();
    } else {
        return null;
    }
});

function onEdit() {
    router.push(`/workflows/edit?id=${workflow.value.id}`);
}

async function onImport() {
    await copyWorkflow(workflow.value.id, workflow.value.owner);
    Toast.success("Workflow imported successfully");
}

function onRenameClose(e: any) {
    showRename.value = false;
    emit("refreshList", true);
}

function toggleShowPreview(val: boolean = false) {
    showPreview.value = val;
}

async function onTagsUpdate(tags: string[]) {
    workflow.value.tags = tags;
    await updateWorkflow(workflow.value.id, { tags });
    emit("refreshList", false, true);
}
</script>

<template>
    <div class="workflow-card" :data-workflow-id="workflow.id">
        <div
            class="workflow-card-container"
            :class="{ 'workflow-shared-trs': !publishedView && (workflow.source_metadata || workflow.published) }">
            <div>
                <div class="d-flex justify-content-between align-items-center mb-1">
                    <div>
                        <WorkflowIndicators :workflow="workflow" :published-view="publishedView" />

                        <span class="workflow-name hide-in-card font-weight-bold">
                            {{ workflow.name }}
                            <BButton
                                v-if="!shared && !workflow.deleted"
                                id="rename-button"
                                v-b-tooltip.top
                                class="inline-icon-button workflow-rename"
                                variant="link"
                                size="sm"
                                title="Rename"
                                @click="showRename = !showRename">
                                <FontAwesomeIcon :icon="faPen" fixed-width />
                            </BButton>
                        </span>
                    </div>

                    <div class="workflow-count-actions">
                        <WorkflowInvocationsCount class="ml-1" :workflow="workflow" />

                        <WorkflowActions
                            :workflow="workflow"
                            :published="publishedView"
                            @refreshList="emit('refreshList', true)"
                            @toggleShowPreview="toggleShowPreview" />
                    </div>
                </div>

                <div>
                    <span class="workflow-name show-in-card">
                        {{ workflow.name }}
                        <BButton
                            v-if="!shared && !workflow.deleted"
                            id="rename-button"
                            v-b-tooltip.top
                            variant="link"
                            size="sm"
                            class="inline-icon-button workflow-rename"
                            title="Rename"
                            @click="showRename = !showRename">
                            <FontAwesomeIcon :icon="faPen" fixed-width />
                        </BButton>
                    </span>
                </div>

                <TextSummary
                    v-if="description"
                    class="my-1"
                    :description="description"
                    :max-length="gridView ? 100 : 250" />
            </div>

            <div class="workflow-card-footer">
                <div>
                    <StatelessTags
                        clickable
                        :value="workflow.tags"
                        :disabled="workflow.deleted"
                        :max-visible-tags="gridView ? 2 : 8"
                        @input="(tags) => onTagsUpdate(tags)"
                        @tag-click="emit('tagClick', $event)" />
                </div>

                <div class="workflow-card-actions">
                    <WorkflowActionsExtend
                        class="mr-2"
                        :workflow="workflow"
                        :published="publishedView"
                        @refreshList="emit('refreshList', true)" />

                    <div class="workflow-edit-run-buttons">
                        <BButton
                            v-if="!shared"
                            v-b-tooltip.hover
                            :disabled="workflow.deleted"
                            size="sm"
                            class="mr-2"
                            :title="workflow.deleted ? 'You cannot edit a deleted workflow' : 'Edit'"
                            variant="outline-primary"
                            @click="onEdit">
                            <FontAwesomeIcon :icon="faEdit" />
                            Edit
                        </BButton>

                        <BButton
                            v-else
                            v-b-tooltip.hover
                            size="sm"
                            class="mr-2"
                            title="Import this workflow to edit"
                            variant="outline-primary"
                            @click="onImport">
                            <FontAwesomeIcon :icon="faUpload" />
                            Import
                        </BButton>

                        <WorkflowRunButton :id="workflow.id" />
                    </div>
                </div>
            </div>

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
    </div>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";

.workflow-card {
    container: workflow-card / inline-size;

    .workflow-rename {
        display: none;
    }

    &:hover {
        .workflow-rename {
            display: inline-block;
        }
    }

    .workflow-card-container {
        display: flex;
        gap: 0.5rem;
        flex-direction: column;
        justify-content: space-between;
        background-color: white;
        border: 1px solid #e5e5e5;
        border-radius: 0.5rem;
        padding: 0.5rem;
        margin: 0 0.25rem 0.5rem 0.25rem;

        .workflow-count-actions {
            display: flex;
            align-self: baseline;
            gap: 0.5rem;
        }

        .text-summary {
            height: inherit;
        }

        .workflow-name {
            font-size: 1rem;
            font-weight: bold;
        }

        .workflow-preview-modal {
            min-width: max-content;
        }

        .workflow-card-actions {
            display: flex;
            margin-top: 0.5rem;
            justify-content: end;
        }

        @container (max-width: 576px) {
            .workflow-card-footer {
                gap: 0.5rem;
                flex-wrap: wrap;
                align-items: center;
                justify-content: space-between;
            }

            .workflow-card-actions {
                display: flex;
                gap: 0.5rem;
                align-items: center;
                justify-content: space-between;
            }
        }

        @container (min-width: 576px, max-width: 768px) {
            .workflow-card-actions {
                justify-content: end;
            }
        }
    }

    .workflow-shared-trs {
        border-left: 0.25rem solid $brand-primary;
    }

    @container (max-width: 768px) {
        .hide-in-card {
            display: none !important;
        }

        .show-in-card {
            display: inline-block !important;
        }

        .workflow-count-actions {
            align-items: baseline;
            justify-content: end;
        }
    }

    @container (min-width: 768px) {
        .workflow-count-actions {
            align-items: end;
            flex-direction: column-reverse;
        }

        .hide-in-card {
            display: inline-block !important;
        }

        .show-in-card {
            display: none !important;
        }
    }
}
</style>
