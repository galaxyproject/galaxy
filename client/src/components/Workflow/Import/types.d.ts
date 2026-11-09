export interface TrsSelection {
    id: string;
    label: string;
    link_url: string;
    doc: string;
}

export interface TrsToolVersion {
    id: string;
    name: string;
}

/** The fields of a workflow refactor action that address a version on a TRS server. */
export interface TrsVersionReference {
    trs_server: string;
    trs_tool_id: string;
    trs_version_id: string;
}

export interface TrsTool {
    id: string;
    name: string;
    description: string;
    organization: string;
    versions: TrsToolVersion[];
}
