import { faFileImport, faGlobe, faShieldAlt } from "@fortawesome/free-solid-svg-icons";
import { computed, type Ref } from "vue";

import { type WorkflowSummary } from "@/api/workflows";
import { type CardAttributes } from "@/components/Common/GCard.types";
import { useToast } from "@/composables/toast";
import { useUserStore } from "@/stores/userStore";
import { copy } from "@/utils/clipboard";

export function useWorkflowCardIndicators(
    workflow: Ref<WorkflowSummary>,
    publishedView: boolean,
    filterable: boolean,
    updateFilter: (key: string, value: boolean) => void
) {
    const userStore = useUserStore();

    const { success } = useToast();

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

    const sourceType = computed(() => {
        const { url, trs_server, trs_tool_id } = workflow.value.source_metadata || {};
        const trs = trs_server || trs_tool_id;
        if (url) {
            return "url";
        } else if (trs) {
            return `trs_${trs}`;
        } else {
            return "";
        }
    });

    const sourceTitle = computed(() => {
        if (sourceType.value.includes("trs")) {
            return `Imported from TRS ID (version: ${workflow.value.source_metadata?.trs_version_id}). Click to copy ID`;
        } else if (sourceType.value == "url") {
            return `Imported from ${workflow.value.source_metadata?.url}. Click to copy link`;
        } else {
            return `Imported from ${workflow.value.source_type || "unknown"}`;
        }
    });

    function onCopyLink() {
        if (sourceType.value == "url") {
            copy(workflow.value.source_metadata?.url);
            success("URL copied");
        } else if (sourceType.value.includes("trs")) {
            copy(workflow.value.source_metadata?.trs_tool_id);
            success("TRS ID copied");
        }
    }

    const workflowCardIndicators: CardAttributes[] = [
        {
            id: "workflow-invocations",
            label: "",
            title: publishedTitle.value,
            icon: faGlobe,
            handler: () => updateFilter("published", true),
            disabled: publishedView,
            visible: workflow.value.published,
        },
        {
            id: "workflow-source-trs",
            label: "",
            title: sourceTitle.value,
            icon: faShieldAlt,
            handler: onCopyLink,
            visible: sourceType.value.includes("trs"),
        },
        {
            id: "workflow-source-url",
            label: "",
            title: sourceTitle.value,
            icon: faFileImport,
            visible: sourceType.value == "url",
        },
    ];

    return {
        workflowCardIndicators,
    };
}
