import { vi } from "vitest";

import { useHistoryBreadCrumbsTo } from "@/composables/historyBreadcrumbs";

vi.mock("@/composables/historyBreadcrumbs");

export function setupMockHistoryBreadcrumbs() {
    const breadcrumbItems = [{ title: "Histories", to: "/histories/list" }];
    return useHistoryBreadCrumbsTo.mockReturnValue({
        breadcrumbItems,
    });
}
