import { getFakePageRevisionDetails, getFakePageSummary } from "@tests/test-data/pages";

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

export const FAKE_PAGE_REVISION = getFakePageRevisionDetails({
    id: "rev-1",
    page_id: "page-1",
    title: "My Analysis",
    content: "# Analysis report\nReads processed: 12000\nReference build: hg19",
    content_editor: "# Analysis report\nReads processed: 12000\nReference build: hg19",
});

export const PAGE_CURRENT_CONTENT =
    "# Analysis report\nReads processed: 16000\nReference build: hg38\nAligner: Bowtie2";

export const PAGE_PREVIOUS_CONTENT = "# Analysis report\nReads processed: 8000";
