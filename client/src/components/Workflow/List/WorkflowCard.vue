<script setup lang="ts">
import { faPen } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BFormCheckbox, BLink } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";

import { type WorkflowSummary } from "@/api/workflows";
import { updateWorkflow } from "@/components/Workflow/workflows.services";
import { useUserStore } from "@/stores/userStore";

import TextSummary from "@/components/Common/TextSummary.vue";
import StatelessTags from "@/components/TagsMultiselect/StatelessTags.vue";
import WorkflowActions from "@/components/Workflow/List/WorkflowActions.vue";
import WorkflowActionsExtend from "@/components/Workflow/List/WorkflowActionsExtend.vue";
import WorkflowIndicators from "@/components/Workflow/List/WorkflowIndicators.vue";
import WorkflowInvocationsCount from "@/components/Workflow/WorkflowInvocationsCount.vue";

interface Props {
    workflow: WorkflowSummary;
    gridView?: boolean;
    hideRuns?: boolean;
    filterable?: boolean;
    publishedView?: boolean;
    editorView?: boolean;
    current?: boolean;
    selected?: boolean;
    selectable?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    gridView: false,
    publishedView: false,
    hideRuns: false,
    filterable: true,
    editorView: false,
    current: false,
    selected: false,
    selectable: false,
});

const emit = defineEmits<{
    (e: "select", workflow: any): void;
    (e: "tagClick", tag: string): void;
    (e: "refreshList", overlayLoading?: boolean, silent?: boolean): void;
    (e: "updateFilter", key: string, value: any): void;
    (e: "rename", id: string, name: string): void;
    (e: "preview", id: string): void;
    (e: "insert"): void;
    (e: "insertSteps"): void;
}>();

const userStore = useUserStore();

const { isAnonymous } = storeToRefs(userStore);

const workflow = computed(() => props.workflow);

const shared = computed(() => {
    return !userStore.matchesCurrentUsername(workflow.value.owner);
});

const description = computed(() => {
    if (workflow.value.annotations && workflow.value.annotations.length > 0) {
        return workflow.value.annotations[0]?.trim();
    } else {
        return null;
    }
});

async function onTagsUpdate(tags: string[]) {
    workflow.value.tags = tags;
    await updateWorkflow(workflow.value.id, { tags });
    emit("refreshList", true, true);
}

async function onTagClick(tag: string) {
    emit("tagClick", tag);
}

const dropdownOpen = ref(false);
</script>

<template>
    <div
        class="workflow-card"
        :class="{ 'dropdown-open': dropdownOpen }"
        :data-workflow-id="workflow.id"
        :data-workflow-name="workflow.name">
        <div
            class="workflow-card-container"
            :class="{
                'workflow-shared': workflow.published,
                'workflow-card-selected': props.selected,
            }">
            <div class="workflow-card-header">
                <BFormCheckbox
                    v-if="props.selectable && !shared"
                    v-b-tooltip.hover.noninteractive
                    :checked="props.selected"
                    class="workflow-card-select-checkbox"
                    title="Select for bulk actions"
                    @change="emit('select', workflow)" />

                <WorkflowIndicators
                    class="workflow-card-indicators"
                    :workflow="workflow"
                    :published-view="publishedView"
                    :filterable="props.filterable"
                    @updateFilter="(k, v) => emit('updateFilter', k, v)" />

                <div class="workflow-count-actions">
                    <WorkflowInvocationsCount
                        v-if="!props.hideRuns && !isAnonymous && !shared"
                        class="invocations-count mx-1"
                        :workflow="workflow" />

                    <WorkflowActions
                        :workflow="props.workflow"
                        :published="props.publishedView"
                        :editor="props.editorView"
                        :current="props.current"
                        @refreshList="emit('refreshList', true)"
                        @dropdown="(open) => (dropdownOpen = open)" />
                </div>

                <span class="workflow-name font-weight-bold">
                    <BLink
                        v-b-tooltip.hover.noninteractive
                        class="workflow-name-preview"
                        title="Preview Workflow"
                        @click.stop.prevent="emit('preview', props.workflow.id)">
                        {{ workflow.name }}
                    </BLink>

                    <BButton
                        v-if="!props.current && !shared && !workflow.deleted"
                        v-b-tooltip.hover.noninteractive
                        :data-workflow-rename="workflow.id"
                        class="inline-icon-button workflow-rename"
                        variant="link"
                        size="sm"
                        title="Rename"
                        @click="emit('rename', props.workflow.id, props.workflow.name)">
                        <FontAwesomeIcon :icon="faPen" fixed-width />
                    </BButton>
                </span>

                <TextSummary
                    v-if="description"
                    class="workflow-summary my-1"
                    :description="description"
                    :max-length="gridView ? 100 : 250" />
            </div>

            <div class="workflow-card-footer">
                <div class="workflow-card-tags">
                    <StatelessTags
                        clickable
                        :value="workflow.tags"
                        :disabled="props.current || isAnonymous || workflow.deleted || shared"
                        :max-visible-tags="gridView ? 2 : 8"
                        @input="onTagsUpdate($event)"
                        @tag-click="onTagClick($event)" />
                </div>

                <WorkflowActionsExtend
                    :workflow="workflow"
                    :published="publishedView"
                    :editor="editorView"
                    :current="props.current"
                    @refreshList="emit('refreshList', true)"
                    @insert="(...args) => emit('insert', ...args)"
                    @insertSteps="(...args) => emit('insertSteps', ...args)" />
            </div>
        </div>
    </div>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";
@import "_breakpoints.scss";

.workflow-card {
    container: workflow-card / inline-size;
    padding: 0 0.25rem 0.5rem 0.25rem;

    &.dropdown-open {
        z-index: 10;
    }

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
        border: 0.1rem solid $brand-secondary;

        &.workflow-card-selected {
            background-color: $brand-light;
            border: 0.1rem solid $brand-primary;
        }

        border-radius: 0.5rem;
        padding: 0.5rem;

        &.workflow-shared {
            border-left: 0.25rem solid $brand-primary;
        }

        .workflow-card-header {
            display: grid;
            position: relative;
            align-items: start;
            grid-template-areas:
                "i d b"
                "n n n"
                "s s s";

            grid-template-columns: auto 1fr auto;

            &:has(.invocations-count) {
                @container workflow-card (max-width: #{$breakpoint-xs}) {
                    grid-template-areas:
                        "i d b"
                        "n n b"
                        "s s s";
                }
            }

            .workflow-card-select-checkbox {
                grid-area: i;
                margin: 0%;
            }

            .workflow-card-indicators {
                grid-area: d;
            }

            .workflow-count-actions {
                grid-area: b;
                display: flex;
                align-items: center;
                flex-direction: row;
                justify-content: flex-end;

                @container workflow-card (max-width: #{$breakpoint-xs}) {
                    align-items: flex-end;
                    flex-direction: column-reverse;
                }
            }

            .workflow-name {
                grid-area: n;
                font-size: 1rem;
                font-weight: bold;
                word-break: break-all;
            }

            .workflow-summary {
                grid-area: s;
            }
        }

        .workflow-card-footer {
            display: flex;
            justify-content: space-between;
            align-items: flex-end;

            .workflow-card-tags {
                max-width: 60%;
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
    }
}
</style>
