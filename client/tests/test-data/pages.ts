import type { HistoryPageDetails, HistoryPageSummary } from "@/api/pages";

export function getFakePageSummary(overrides: Partial<HistoryPageSummary> = {}): HistoryPageSummary {
    return {
        id: "def456pageid",
        history_id: "abc123historyid",
        title: "My Analysis Notes",
        slug: null,
        source_invocation_id: null,
        published: false,
        importable: false,
        deleted: false,
        latest_revision_id: "rev789revisionid",
        revision_ids: ["rev789revisionid"],
        create_time: "2025-06-15T10:30:00Z",
        update_time: "2025-06-15T12:45:00Z",
        username: "test",
        email_hash: "",
        author_deleted: false,
        model_class: "Page",
        tags: [],
        ...overrides,
    };
}

export function getFakePageDetails(overrides: Partial<HistoryPageDetails> = {}): HistoryPageDetails {
    return {
        ...getFakePageSummary(),
        content: "# Analysis\n\nSome markdown content here.",
        content_editor: "# Analysis\n\nSome markdown content here.",
        content_format: "markdown",
        edit_source: "user",
        annotation: null,
        ...overrides,
    };
}
