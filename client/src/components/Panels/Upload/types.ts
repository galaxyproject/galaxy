import type { IconDefinition } from "@fortawesome/fontawesome-svg-core";

export type UploadMode =
    | "local-file"
    | "paste-content"
    | "paste-links"
    | "remote-files"
    | "data-library"
    | "explore-zip"
    | "import-history"
    | "import-workflow";

export interface UploadMethodConfig {
    id: UploadMode;
    name: string;
    description: string;
    icon: IconDefinition;
    headerAction: string;
    requiresTargetHistory: boolean;
    // The following warning is disabled until Vue 3 migration is complete and types can be properly defined
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    component: any;
    requiresAuth?: boolean;
    requiresConfig?: string[];
}
