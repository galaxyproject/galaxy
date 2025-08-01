import { faLayerGroup, faList, faSpinner, faUser, faUsers } from "@fortawesome/free-solid-svg-icons";
import { storeToRefs } from "pinia";
import { computed, type Ref } from "vue";
import { useRouter } from "vue-router/composables";

import type { WorkflowSummary } from "@/api/workflows";
import type { CardBadge } from "@/components/Common/GCard.types";
import { useInvocationStore } from "@/stores/invocationStore";
import { useUserStore } from "@/stores/userStore";

export function useWorkflowCardBadges(
    workflow: Ref<WorkflowSummary>,
    publishedView: boolean,
    filterable: boolean,
    hideRuns: boolean,
    updateFilter: (key: string, value: string) => void
) {
    const router = useRouter();

    const invocationStore = useInvocationStore();

    const userStore = useUserStore();
    const { isAnonymous } = storeToRefs(userStore);

    const invocationCount = computed(() => invocationStore.getInvocationCountByWorkflowId(workflow.value.id));

    const shared = computed(() => {
        return !userStore.matchesCurrentUsername(workflow.value.owner);
    });

    const publishedTitle = computed(() => {
        if (workflow.value.published && !publishedView) {
            return "Published workflow" + (filterable ? ". Click to filter published workflows" : "");
        } else if (userStore.matchesCurrentUsername(workflow.value.owner)) {
            return "Published by you" + (filterable ? ". Click to view all published workflows by you" : "");
        } else {
            return (
                `Published by '${workflow.value.owner}'` +
                (filterable ? `. Click to view all published workflows by '${workflow.value.owner}'` : "")
            );
        }
    });

    const invocationText = computed(() => {
        if (invocationCount.value === null) {
            return "loading...";
        } else if (invocationCount.value === 0) {
            return "never run";
        } else {
            return `workflow runs: ${invocationCount.value}`;
        }
    });

    function onViewMySharedByUser() {
        router.push(`/workflows/list_shared_with_me?owner=${workflow.value.owner}`);
        updateFilter("user", `'${workflow.value.owner}'`);
    }

    function onViewUserPublished() {
        router.push(`/workflows/list_published?owner=${workflow.value.owner}`);
        updateFilter("user", `'${workflow.value.owner}'`);
    }

    const workflowCardBadges = computed<CardBadge[]>(() => [
        {
            id: "invocations-count-loading",
            label: invocationText.value,
            title: "Loading workflow invocation count",
            icon: faSpinner,
            spin: true,
            visible:
                !hideRuns &&
                !isAnonymous.value &&
                !shared.value &&
                !workflow.value.number_of_steps &&
                invocationCount.value === null,
            loading: true,
        },
        {
            id: "invocations-count-zero",
            label: invocationText.value,
            title: "This workflow has never been run",
            icon: faList,
            visible:
                !hideRuns &&
                !isAnonymous.value &&
                !shared.value &&
                !workflow.value.number_of_steps &&
                invocationCount.value !== null &&
                invocationCount.value === 0,
        },
        {
            id: "invocations-count",
            label: invocationText.value,
            title: "View workflow invocations",
            variant: "outline-primary",
            icon: faList,
            to: `/workflows/${workflow.value.id}/invocations`,
            visible:
                !hideRuns &&
                !isAnonymous.value &&
                !shared.value &&
                !workflow.value.number_of_steps &&
                invocationCount.value !== null &&
                invocationCount.value > 0,
        },
        {
            id: "step-count",
            label: `${workflow.value.number_of_steps} steps`,
            title: `This workflow has ${workflow.value.number_of_steps} steps`,
            icon: faLayerGroup,
            visible: !!workflow.value.number_of_steps,
        },
    ]);

    const workflowCardTitleBadges = computed<CardBadge[]>(() => [
        {
            id: "owner-shared",
            label: workflow.value.owner,
            title: `'${workflow.value.owner}' shared this workflow with you. Click to view all workflows shared with you by '${workflow.value.owner}'`,
            icon: faUsers,
            type: "badge",
            variant: "outline-secondary",
            handler: onViewMySharedByUser,
            visible: shared.value && !publishedView,
        },
        {
            id: "owner-published",
            label: workflow.value.owner,
            title: publishedTitle.value,
            icon: faUser,
            type: "badge",
            variant: "outline-secondary",
            handler: onViewUserPublished,
            visible: workflow.value.published && publishedView,
        },
    ]);

    return {
        workflowCardBadges,
        workflowCardTitleBadges,
    };
}
