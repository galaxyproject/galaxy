/**
 * Centralized user-facing strings for pages/notebooks/reports.
 *
 * Backend uses "page" everywhere — that's an implementation detail.
 * Frontend terminology:
 *   - "Galaxy Notebook" — history-attached pages (the working document)
 *   - "Report"          — standalone pages (the publishable artifact)
 *
 * Change strings here to rename across the entire UI.
 */
import type { PageEditorMode } from "@/stores/pageEditorStore";

/** Per-mode labels used by the page editor, history page list, chat panel, etc. */
export const PAGE_LABELS: Record<
    PageEditorMode,
    {
        entityName: string;
        entityNamePlural: string;
        defaultTitle: string;
        editorBackLabel: string;
        newButton: string;
        emptyStateTitle: string;
        emptyStateDescription: string;
        viewButton: string;
        createButton: string;
        historyCounterTooltip: string;
        assistantName: string;
        assistantWelcome: string;
        chatPlaceholder: string;
        newConversation: string;
    }
> = {
    history: {
        entityName: "Galaxy Notebook",
        entityNamePlural: "Galaxy Notebooks",
        defaultTitle: "Untitled Notebook",
        editorBackLabel: "This History's Notebooks",
        newButton: "New Notebook",
        emptyStateTitle: "No notebooks yet",
        emptyStateDescription:
            "Create a notebook to document your analysis with rich markdown, embedded datasets, and visualizations.",
        viewButton: "View notebook",
        createButton: "Create Notebook",
        historyCounterTooltip: "Galaxy Notebooks",
        assistantName: "Markdown Assistant",
        assistantWelcome:
            "I'm the Markdown Assistant. I can help you edit this notebook — " +
            "ask me to rewrite sections, add content, fix formatting, or analyze your history datasets.",
        chatPlaceholder: "Ask about your history or request notebook edits...",
        newConversation: "Starting a new conversation. How can I help with this notebook?",
    },
    standalone: {
        entityName: "Report",
        entityNamePlural: "Reports",
        defaultTitle: "Untitled Report",
        editorBackLabel: "Back to Reports",
        newButton: "Create Report",
        emptyStateTitle: "No reports yet",
        emptyStateDescription: "Create a report to publish your analysis.",
        viewButton: "View report",
        createButton: "Create Report",
        historyCounterTooltip: "",
        assistantName: "Markdown Assistant",
        assistantWelcome:
            "I'm the Markdown Assistant. I can help you edit this report — " +
            "ask me to rewrite sections, add content, fix formatting, " +
            "or browse your current history's datasets.",
        chatPlaceholder: "Ask about your history or request report edits...",
        newConversation: "Starting a new conversation. How can I help with this report?",
    },
} as const;

/** Grid page (lists standalone reports). */
export const GRID_LABELS = {
    heading: "Reports",
    createButton: "Create Report",
    myTab: "My Reports",
    publicTab: "Public Reports",
    loginRequired: "Manage your Reports",
    savedTitle: "Saved Reports",
    publishedTitle: "Published Reports",
    gridPlural: "Reports",
    deleteConfirm: "Are you sure that you want to delete the selected report?",
    restoreConfirm: "Are you sure that you want to restore the selected report?",
    windowTitle: (title: unknown) => `Report: ${title}`,
} as const;

/** Activity bar entry. */
export const ACTIVITY_LABELS = {
    title: "Reports",
    description: "Display and create new reports.",
    tooltip: "Show all reports",
} as const;

/** Agent type registry. */
export const AGENT_LABELS = {
    pageAssistantLabel: "Markdown Assistant",
    pageAssistantDescription: "Markdown editing assistant",
} as const;

/** Error messages (store) — generic since they apply to both types. */
export const ERROR_MESSAGES = {
    loadList: "Failed to load pages",
    loadPage: "Failed to load page",
    createPage: "Failed to create page",
    savePage: "Failed to save page",
    deletePage: "Failed to delete page",
    loadRevisions: "Failed to load revisions",
    loadRevision: "Failed to load revision",
    restoreRevision: "Failed to restore revision",
} as const;

/** Published page view. */
export const PUBLISHED_LABELS = {
    editButton: "Edit Report",
    loadingMessage: "Loading Report",
    errorHeading: "Failed to load Report",
    modelClass: "Report",
} as const;

/** Page form (create/edit standalone reports). */
export const FORM_LABELS = {
    createTitle: "Create a new Report",
    editTitle: "Edit Report",
} as const;

/** Embed labels. */
export const EMBED_LABELS = {
    iframeTitle: "Galaxy Report Embed",
    showTitle: "Show report title",
} as const;

/** Object permissions modal. */
export const PERMISSIONS_LABELS = {
    modalTitle: "Report Object Permissions",
} as const;
