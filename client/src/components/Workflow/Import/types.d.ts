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

export interface TrsTool {
    id: string;
    name: string;
    description: string;
    organization: string;
    versions: TrsToolVersion[];
}
