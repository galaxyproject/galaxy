import { useHistoryBreadCrumbsTo } from "@/composables/historyBreadcrumbs";

jest.mock("composables/historyBreadcrumbs");

export function setupMockHistoryBreadcrumbs() {
    const breadcrumbItems = [{ title: "Histories", to: "/histories/list" }];
    return useHistoryBreadCrumbsTo.mockReturnValue({
        breadcrumbItems,
    });
}
