import type { IconDefinition } from "@fortawesome/fontawesome-svg-core";

import type { UploadCollectionConfig } from "@/composables/upload/collectionTypes";
import type { NewUploadItem } from "@/composables/upload/uploadItemTypes";
import type { ApiUploadItem } from "@/utils/upload";

export type UploadMethod =
    | "local-file"
    | "paste-content"
    | "paste-links"
    | "remote-files"
    | "data-library"
    | "explore-zip"
    | "data-source-tools"
    | "import-history"
    | "import-workflow"
    | "rule-based-import"
    | "composite-file";

export interface UploadMethodConfig {
    /**
     * Unique identifier for the upload method.
     *
     * This value is used for routing (e.g. `/upload/:id`) and must
     * correspond to a key in the upload method registry.
     */
    id: UploadMethod;

    /**
     * Human-readable name displayed in the upload method list.
     */
    name: string;

    /**
     * Short description explaining what this upload method does.
     * Used for search and discovery in the upload panel.
     */
    description: string;

    /**
     * FontAwesome icon used to visually represent the upload method.
     */
    icon: IconDefinition;

    /**
     * Label used for the primary action button when this upload method
     * is active (e.g. "Upload Files", "Import History").
     */
    headerAction: string;

    /**
     * Whether this upload method requires an active target history.
     *
     * If true and no history is available, the method may be disabled
     * or hidden by the upload panel.
     */
    requiresTargetHistory: boolean;

    /**
     * Vue component responsible for rendering and handling this
     * upload method's UI and logic.
     *
     * Note: typed as `any` until Vue 3 migration is complete.
     */
    // The following warning is disabled until Vue 3 migration is complete and types can be properly defined
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    component: any;

    /**
     * List of configuration keys that must be enabled for this upload
     * method to be available.
     *
     * Each entry is checked against the global Galaxy configuration.
     */
    requiresConfig?: string[];

    /**
     * When true, this upload method is only available when
     * upload advanced mode is enabled.
     *
     * This allows advanced or power-user features to be hidden by default
     * while remaining fully configurable and reactive.
     */
    requiresAdvancedMode?: boolean;

    /**
     * When true, the Start button in the footer will be shown.
     *
     * Set this to false for upload methods that handle their own submission
     * internally (e.g., wizards, embedded forms with their own submit buttons).
     *
     * @default true
     */
    showStartButton?: boolean;

    /**
     * Optional tip messages to display for this upload method.
     *
     * Tips provide contextual help, explaining non-obvious features,
     * common workflows, or best practices. Supports markdown formatting.
     *
     * Each string in the array represents a separate tip message.
     */
    tips?: string[];
}

/**
 * Upload data prepared by an upload method component, ready for API submission.
 * Returned by `UploadMethodComponent.prepareUpload()` and consumed by `useUploadSubmission`.
 */
export interface PreparedUpload {
    /** Items formatted for the Galaxy upload API. */
    apiItems: ApiUploadItem[];
    /** Optional dataset collection configuration for atomic collection creation. */
    collectionConfig?: UploadCollectionConfig;
    /** Items used for progress tracking in the upload state store. */
    uploadItems?: NewUploadItem[];
}

/**
 * Interface that upload method components must implement to be used in the upload panel.
 */
export interface UploadMethodComponent {
    /**
     * Returns prepared upload data for API submission, or null when there is
     * nothing to upload (e.g. no files selected or no content entered).
     */
    prepareUpload: () => PreparedUpload | null;
    /**
     * Clears transient UI state without remounting the component.
     * Called by the modal when it reopens so stale input is not carried over.
     */
    reset?: () => void;
}
