import { faLayerGroup, faList, faUser, faUsers } from "@fortawesome/free-solid-svg-icons";
import { storeToRefs } from "pinia";
import { computed, onMounted, type Ref, ref } from "vue";
import { useRouter } from "vue-router/composables";

import { GalaxyApi } from "@/api";
import { type WorkflowSummary } from "@/api/workflows";
import { type CardBadge } from "@/components/Common/GCard.types";
import { useUserStore } from "@/stores/userStore";
import { rethrowSimple } from "@/utils/simple-error";

export function useWorkflowCardBadges(
    workflow: Ref<WorkflowSummary>,
    publishedView: boolean,
    filterable: boolean,
    hideRuns: boolean,
    updateFilter: (key: string, value: string) => void
) {
    const router = useRouter();

    const userStore = useUserStore();
    const { isAnonymous } = storeToRefs(userStore);

    const invocationCount = ref(0);

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
        if (invocationCount.value === 0) {
            return "never run";
        } else {
            return `workflow runs: ${invocationCount.value}`;
        }
    });

    async function initCounts() {
        const { data, error } = await GalaxyApi().GET("/api/workflows/{workflow_id}/counts", {
            params: { path: { workflow_id: workflow.value.id } },
        });

        if (error) {
            rethrowSimple(error);
        }

        let allCounts = 0;
        for (const stateCount of Object.values(data)) {
            if (stateCount) {
                allCounts += stateCount;
            }
        }

        return allCounts;
    }

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
            id: "step-count",
            label: invocationText.value,
            title: "This workflow has never been run",
            icon: faList,
            visible:
                !hideRuns &&
                !isAnonymous.value &&
                !shared.value &&
                !workflow.value.number_of_steps &&
                invocationCount.value !== undefined &&
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
                invocationCount.value !== undefined &&
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

    onMounted(async () => {
        invocationCount.value = await initCounts();
    });

    return {
        workflowCardBadges,
        workflowCardTitleBadges,
    };
}
