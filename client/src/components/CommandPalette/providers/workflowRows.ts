/** Workflow rows and store-first lists, shared by the workflows provider and the "Run workflow" action */
import { faSitemap } from "@fortawesome/free-solid-svg-icons";

import type { WorkflowSummary } from "@/api/workflows";
import { useUserStore } from "@/stores/userStore";
import { useWorkflowStore, type WorkflowListVariant } from "@/stores/workflowStore";
import { relativeUpdatedLabel } from "@/utils/dates";

import type { PaletteItem } from "../types";
import { PALETTE_LIMITS } from "./limits";
import { storeFirstItems, type StoreFirstList } from "./storeFirst";

/** Entity type the workflow rows record in the palette MRU (`useRecentPaletteItems`) */
export const WORKFLOW_RECENT_TYPE = "workflow";

export function runUrl(workflowId: string): string {
    return `/workflows/run?id=${workflowId}`;
}

function editUrl(workflowId: string): string {
    return `/workflows/edit?id=${workflowId}`;
}

/** Section scoped item id, so the same workflow may appear in several sections */
export function itemId(sectionId: string, workflowId: string): string {
    return `workflows:${sectionId}:${workflowId}`;
}

/**
 * One result row. Enter runs the workflow; workflows the current user owns
 * additionally offer their editor on shift+enter.
 */
export function workflowItem(workflow: WorkflowSummary, sectionId: string): PaletteItem {
    const userStore = useUserStore();
    const owned = userStore.matchesCurrentUsername(workflow.owner);
    // the owner is only worth a line for workflows that are not the user's own
    const subtitle = [
        owned ? undefined : workflow.owner && `by ${workflow.owner}`,
        relativeUpdatedLabel(workflow.update_time),
    ]
        .filter(Boolean)
        .join(" · ");
    return {
        id: itemId(sectionId, workflow.id),
        icon: faSitemap,
        keywords: [workflow.owner, ...(workflow.tags ?? [])].filter(Boolean).join(" "),
        mru: { type: WORKFLOW_RECENT_TYPE, id: workflow.id },
        title: workflow.name,
        to: runUrl(workflow.id),
        ...(subtitle ? { subtitle } : {}),
        ...(owned ? { secondaryAction: { label: "Edit workflow", to: editUrl(workflow.id) } } : {}),
    };
}

/** Rows of one cached list, newest first so an empty query renders "Latest" as promised */
function workflowRows(workflows: WorkflowSummary[], variant: WorkflowListVariant): PaletteItem[] {
    return [...workflows]
        .sort((a, b) => (b.update_time ?? "").localeCompare(a.update_time ?? ""))
        .map((workflow) => workflowItem(workflow, variant));
}

/** One workflow list, store first; a search reads back its own list, the bookmarks only filter locally */
export function workflowList(variant: WorkflowListVariant): StoreFirstList {
    const workflowStore = useWorkflowStore();
    return {
        key: `workflows:${variant}`,
        isLoaded: () => workflowStore.isWorkflowListLoaded(variant),
        fetchListing: () => workflowStore.fetchWorkflowList(variant, "", { limit: PALETTE_LIMITS.page }),
        cachedItems: () => workflowRows(workflowStore.getWorkflowList(variant), variant),
        isComplete: () => workflowStore.getWorkflowList(variant).length < PALETTE_LIMITS.page,
        searchItems:
            variant === "bookmarked"
                ? undefined
                : async (query) => {
                      await workflowStore.fetchWorkflowList(variant, query, { limit: PALETTE_LIMITS.page });
                      return workflowStore
                          .getWorkflowList(variant, query)
                          .map((workflow) => workflowItem(workflow, variant));
                  },
    };
}

/**
 * The user's own workflows as run rows, store first like the `w:` scope. Used by
 * the "Run workflow" action, which collects its workflow as an argument.
 */
export function myWorkflowItems(query: string, limit = PALETTE_LIMITS.section): Promise<PaletteItem[]> {
    return storeFirstItems(workflowList("my"), query.trim(), limit);
}
