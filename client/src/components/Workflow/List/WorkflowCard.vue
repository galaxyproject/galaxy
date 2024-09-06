<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faEdit, faEye, faPen, faUpload } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BLink } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";

import { copyWorkflow, updateWorkflow } from "@/components/Workflow/workflows.services";
import { Toast } from "@/composables/toast";
import { useUserStore } from "@/stores/userStore";

import AsyncButton from "@/components/Common/AsyncButton.vue";
import TextSummary from "@/components/Common/TextSummary.vue";
import StatelessTags from "@/components/TagsMultiselect/StatelessTags.vue";
import WorkflowActions from "@/components/Workflow/List/WorkflowActions.vue";
import WorkflowActionsExtend from "@/components/Workflow/List/WorkflowActionsExtend.vue";
import WorkflowIndicators from "@/components/Workflow/List/WorkflowIndicators.vue";
import WorkflowRename from "@/components/Workflow/List/WorkflowRename.vue";
import WorkflowPublished from "@/components/Workflow/Published/WorkflowPublished.vue";
import WorkflowInvocationsCount from "@/components/Workflow/WorkflowInvocationsCount.vue";
import WorkflowRunButton from "@/components/Workflow/WorkflowRunButton.vue";

library.add(faEdit, faEye, faPen, faUpload);

interface Props {
    workflow: any;
    gridView?: boolean;
    publishedView?: boolean;
    allowWorkflowManagement?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    gridView: false,
    publishedView: false,
    allowWorkflowManagement: true,
});

const emit = defineEmits<{
    (e: "tagClick", tag: string): void;
    (e: "refreshList", overlayLoading?: boolean, b?: boolean): void;
    (e: "update-filter", key: string, value: any): void;
}>();

const userStore = useUserStore();

const { isAnonymous } = storeToRefs(userStore);

const showRename = ref(false);
const showPreview = ref(false);

const workflow = computed(() => props.workflow);

const shared = computed(() => {
    return !userStore.matchesCurrentUsername(workflow.value.owner);
});

const description = computed(() => {
    if (workflow.value.annotations && workflow.value.annotations.length > 0) {
        return workflow.value.annotations[0].trim();
    } else {
        return null;
    }
});
const editButtonTitle = computed(() => {
    if (isAnonymous.value) {
        return "Log in to edit Workflow";
    } else {
        if (workflow.value.deleted) {
            return "You cannot edit a deleted workflow. Restore it first.";
        } else {
            return "Edit Workflow";
        }
    }
});
const importedButtonTitle = computed(() => {
    if (isAnonymous.value) {
        return "Log in to import workflow";
    } else {
        return "Import this workflow to edit";
    }
});
const runButtonTitle = computed(() => {
    if (isAnonymous.value) {
        return "Log in to run workflow";
    } else {
        if (workflow.value.deleted) {
            return "You cannot run a deleted workflow. Restore it first.";
        } else {
            return "Run workflow";
        }
    }
});

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
    emit("refreshList", true, true);
}

async function onTagClick(tag: string) {
    emit("tagClick", tag);
}
</script>

<template>
    <div class="workflow-card" :data-workflow-id="workflow.id">
        <div
            class="workflow-card-container"
            :class="{
                'workflow-shared': workflow.published,
            }">
            <div class="workflow-card-header">
                <WorkflowIndicators
                    :workflow="workflow"
                    :published-view="publishedView"
                    @update-filter="(k, v) => emit('update-filter', k, v)" />

                <div class="workflow-count-actions">
                    <WorkflowInvocationsCount v-if="!isAnonymous && !shared" class="mx-1" :workflow="workflow" />

                    <WorkflowActions
                        :workflow="workflow"
                        :published="publishedView"
                        :allow-workflow-management="allowWorkflowManagement"
                        @refreshList="emit('refreshList', true)"
                        @toggleShowPreview="toggleShowPreview" />
                </div>

                <span class="workflow-name font-weight-bold">
                    <BLink
                        v-b-tooltip.hover.noninteractive
                        class="workflow-name-preview"
                        title="Preview Workflow"
                        @click.stop.prevent="toggleShowPreview(true)"
                        >{{ workflow.name }}</BLink
                    >
                    <BButton
                        v-if="!shared && !workflow.deleted"
                        v-b-tooltip.hover.noninteractive
                        :data-workflow-rename="workflow.id"
                        class="inline-icon-button workflow-rename"
                        variant="link"
                        size="sm"
                        title="Rename"
                        @click="showRename = !showRename">
                        <FontAwesomeIcon :icon="faPen" fixed-width />
                    </BButton>
                </span>

                <TextSummary
                    v-if="description"
                    class="my-1"
                    :description="description"
                    :max-length="gridView ? 100 : 250" />
            </div>

            <div class="workflow-card-footer">
                <div class="workflow-card-tags">
                    <StatelessTags
                        clickable
                        :value="workflow.tags"
                        :disabled="isAnonymous || workflow.deleted || shared"
                        :max-visible-tags="gridView ? 2 : 8"
                        @input="onTagsUpdate($event)"
                        @tag-click="onTagClick($event)" />
                </div>

                <div class="workflow-card-actions">
                    <WorkflowActionsExtend
                        :workflow="workflow"
                        :published="publishedView"
                        @refreshList="emit('refreshList', true)" />

                    <div class="workflow-edit-run-buttons">
                        <BButton
                            v-if="!isAnonymous && !shared && allowWorkflowManagement"
                            v-b-tooltip.hover.noninteractive
                            :disabled="workflow.deleted"
                            size="sm"
                            class="workflow-edit-button"
                            :title="editButtonTitle"
                            variant="outline-primary"
                            :to="`/workflows/edit?id=${workflow.id}`">
                            <FontAwesomeIcon :icon="faEdit" fixed-width />
                            Edit
                        </BButton>

                        <AsyncButton
                            v-else-if="allowWorkflowManagement"
                            v-b-tooltip.hover.noninteractive
                            size="sm"
                            :disabled="isAnonymous"
                            :title="importedButtonTitle"
                            :icon="faUpload"
                            variant="outline-primary"
                            :action="onImport">
                            Import
                        </AsyncButton>

                        <WorkflowRunButton
                            :id="workflow.id"
                            :disabled="isAnonymous || workflow.deleted"
                            :title="runButtonTitle" />
                    </div>
                </div>
            </div>

            <WorkflowRename
                v-if="!isAnonymous && !shared && !workflow.deleted"
                :id="workflow.id"
                :show="showRename"
                :name="workflow.name"
                @close="onRenameClose" />

            <BModal
                v-model="showPreview"
                ok-only
                size="xl"
                hide-header
                dialog-class="workflow-card-preview-modal w-auto"
                centered>
                <WorkflowPublished v-if="showPreview" :id="workflow.id" quick-view />
            </BModal>
        </div>
    </div>
</template>

<style lang="scss">
.workflow-card-preview-modal {
    max-width: min(1400px, calc(100% - 200px));

    .modal-content {
        height: min(800px, calc(100vh - 80px));
    }
}
</style>

<style scoped lang="scss">
@import "theme/blue.scss";
@import "breakpoints.scss";

.workflow-card {
    container: workflow-card / inline-size;
    padding: 0 0.25rem 0.5rem 0.25rem;

    .workflow-rename {
        opacity: 0;
    }

    &:hover,
    &:focus-within {
        .workflow-rename {
            opacity: 1;
        }
    }

    .workflow-card-container {
        height: 100%;
        display: flex;
        gap: 0.5rem;
        flex-direction: column;
        justify-content: space-between;
        border: 1px solid $brand-secondary;
        border-radius: 0.5rem;
        padding: 0.5rem;

        &.workflow-shared {
            border-left: 0.25rem solid $brand-primary;
        }

        .workflow-card-header {
            display: grid;

            .workflow-count-actions {
                display: flex;
                align-items: center;
                flex-direction: row;
                position: absolute;
                right: 0.5rem;
            }

            .workflow-name {
                font-size: 1rem;
                font-weight: bold;
                word-break: break-all;
            }
        }

        .workflow-card-footer {
            display: flex;
            justify-content: space-between;
            align-items: end;

            .workflow-card-tags {
                max-width: 60%;
            }

            .workflow-card-actions {
                display: flex;
                gap: 0.25rem;
                margin-top: 0.25rem;
                align-items: center;
                justify-content: end;
            }
        }

        @container workflow-card (max-width: #{$breakpoint-sm}) {
            .workflow-card-footer {
                display: inline-block;

                .workflow-card-tags {
                    max-width: 100%;
                }
            }
        }

        @container workflow-card (max-width: #{$breakpoint-sm}) {
            .workflow-card-actions {
                justify-content: space-between;
            }
        }

        @container workflow-card (min-width: #{$breakpoint-sm}, max-width: #{$breakpoint-md}) {
            .workflow-card-actions {
                justify-content: end;
            }
        }
    }

    @container workflow-card (max-width: #{$breakpoint-md}) {
        .workflow-count-actions {
            align-items: baseline;
            justify-content: end;
        }
    }

    @container workflow-card (min-width: #{$breakpoint-md}) {
        .workflow-count-actions {
            align-items: end;
            flex-direction: column-reverse;
        }
    }
}
</style>
