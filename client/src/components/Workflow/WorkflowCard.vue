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

import AsyncButton from "@/components/Common/AsyncButton.vue";
import TextSummary from "@/components/Common/TextSummary.vue";
import StatelessTags from "@/components/TagsMultiselect/StatelessTags.vue";
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
    (e: "tagClick", a: string): void;
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
            <div>
                <div class="d-flex justify-content-between align-items-center mb-1">
                    <div>
                        <WorkflowIndicators :workflow="workflow" :published-view="publishedView" />

                        <span class="workflow-name font-weight-bold">
                            {{ workflow.name }}
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
                    </div>

                    <div class="workflow-count-actions">
                        <WorkflowInvocationsCount class="mx-1" :workflow="workflow" />

                        <WorkflowActions
                            :workflow="workflow"
                            :published="publishedView"
                            @refreshList="emit('refreshList', true)"
                            @toggleShowPreview="toggleShowPreview" />
                    </div>
                </div>

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
                        :disabled="workflow.deleted"
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
                            v-if="!shared"
                            v-b-tooltip.hover.noninteractive
                            :disabled="workflow.deleted"
                            size="sm"
                            class="workflow-edit-button"
                            :title="
                                workflow.deleted
                                    ? 'You cannot edit a deleted workflow. Restore it first.'
                                    : 'Edit workflow'
                            "
                            variant="outline-primary"
                            @click="onEdit">
                            <FontAwesomeIcon :icon="faEdit" fixed-width />
                            Edit
                        </BButton>

                        <AsyncButton
                            v-else
                            v-b-tooltip.hover.noninteractive
                            size="sm"
                            title="Import this workflow to edit"
                            :icon="faUpload"
                            variant="outline-primary"
                            :action="onImport">
                            Import
                        </AsyncButton>

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
                dialog-class="workflow-card-preview-modal w-auto"
                centered>
                <WorkflowQuickView :id="workflow.id" :show="showPreview" @ok="toggleShowPreview(false)" />
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

        .workflow-count-actions {
            display: flex;
            align-self: baseline;
            align-items: center;
            flex-direction: row;
        }

        .text-summary {
            height: inherit;
        }

        .workflow-name {
            font-size: 1rem;
            font-weight: bold;
        }

        .workflow-card-actions {
            display: flex;
            gap: 0.25rem;
            margin-top: 0.25rem;
            align-items: center;
            justify-content: end;
        }

        .workflow-card-footer {
            display: flex;
            justify-content: space-between;
            align-items: end;
        }

        .workflow-card-tags {
            max-width: 60%;
        }

        @container workflow-card (max-width: #{$breakpoint-sm}) {
            .workflow-card-footer {
                display: inline-block;
            }

            .workflow-card-tags {
                max-width: 100%;
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

    .workflow-shared {
        border-left: 0.25rem solid $brand-primary;
    }

    @container workflow-card (max-width: #{$breakpoint-md}) {
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

    @container workflow-card (min-width: #{$breakpoint-md}) {
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
