import { getFakePageSummary } from "@tests/test-data/pages";

export const FAKE_PAGE_SUMMARY = getFakePageSummary({
    id: "page-1",
    history_id: "history-1",
    title: "My Analysis",
    latest_revision_id: "rev-1",
    revision_ids: ["rev-1"],
});

export const FAKE_PAGE_UNTITLED = getFakePageSummary({
    ...FAKE_PAGE_SUMMARY,
    id: "page-2",
    title: "",
});
