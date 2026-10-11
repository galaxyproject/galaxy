import { faSitemap } from "@fortawesome/free-solid-svg-icons";

import { useWorkflowStore } from "@/stores/workflowStore";

import { PALETTE_LIMITS } from "./limits";
import { defineListingProvider } from "./listingProvider";
import { storeFirstItems } from "./storeFirst";
import { itemId, runUrl, WORKFLOW_RECENT_TYPE, workflowItem, workflowList } from "./workflowRows";

export const workflowsProvider = defineListingProvider<"shared" | "published">({
    id: "workflows",
    title: "Workflows",
    variants: ["shared", "published"],
    rootListings: { anonymous: ["published"], signedIn: ["shared", "published"] },
    list: workflowList,
    async searchListing(variant, query) {
        const found = await useWorkflowStore().fetchWorkflowList(variant, query, { limit: PALETTE_LIMITS.page });
        return found.map((workflow) => workflowItem(workflow, variant));
    },
    recentRows() {
        const workflowStore = useWorkflowStore();
        return {
            type: WORKFLOW_RECENT_TYPE,
            stored: (entry) => {
                const summary = workflowStore.getWorkflowSummaryById(entry.id);
                return summary ? workflowItem(summary, "recent") : undefined;
            },
            fallback: (entry) => ({ id: itemId("recent", entry.id), icon: faSitemap, to: runUrl(entry.id) }),
        };
    },
    // `w:` leads with the bookmarks, which only filter locally
    async leadingSections(query) {
        const items = await storeFirstItems(workflowList("bookmarked"), query, PALETTE_LIMITS.section);
        return [{ id: "bookmarked", items, title: "Bookmarked" }];
    },
});
