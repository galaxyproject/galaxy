import type { HistoryPageSummary } from "@/api/pages";

export const FAKE_PAGE_SUMMARY: HistoryPageSummary = {
    id: "page-1",
    history_id: "history-1",
    title: "My Analysis",
    slug: null,
    source_invocation_id: null,
    published: false,
    importable: false,
    deleted: false,
    latest_revision_id: "rev-1",
    revision_ids: ["rev-1"],
    create_time: "2025-06-15T10:30:00Z",
    update_time: "2025-06-15T12:45:00Z",
    username: "test",
    email_hash: "",
    author_deleted: false,
    model_class: "Page",
    tags: [],
};

export const FAKE_PAGE_UNTITLED: HistoryPageSummary = {
    ...FAKE_PAGE_SUMMARY,
    id: "page-2",
    title: "",
};
