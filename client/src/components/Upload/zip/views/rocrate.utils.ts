import { type ROCrateEntity, type ROCrateImmutableView } from "ro-crate-zip-explorer";

import { GALAXY_EXPORT_METADATA_FILES } from "../utils";

interface Conforms {
    id: string;
    name: string;
    version: string;
}

export interface ROCrateFile {
    id: string;
    name: string;
    path: string;
    type: string;
}

interface Person {
    id: string;
    name: string;
    email?: string;
    identifier?: string;
}

interface Organization {
    id: string;
    name: string;
}

export interface ROCrateSummary {
    publicationDate: Date;
    conformsTo: Conforms[];
    license: string;
    workflows: ROCrateFile[];
    files: ROCrateFile[];
    creators: Person[] | Organization[];
}

function isOfType(item: ROCrateEntity, type: string): boolean {
    if (Array.isArray(item["@type"])) {
        return item["@type"].includes(type);
    }
    return item["@type"] === type;
}

function shouldBeIgnored(item: ROCrateEntity): boolean {
    return GALAXY_EXPORT_METADATA_FILES.some((ignoredFile) => item["@id"].includes(ignoredFile));
}

function isWorkflow(item: ROCrateEntity): boolean {
    return isOfType(item, "ComputationalWorkflow") && item["@id"].endsWith(".gxwf.yml");
}

function isFile(item: ROCrateEntity): boolean {
    return (
        isOfType(item, "File") &&
        !shouldBeIgnored(item) &&
        !isOfType(item, "ComputationalWorkflow") &&
        !item["@id"].startsWith("workflows/")
    );
}

export function isCrate(crate: unknown): crate is ROCrateImmutableView {
    return typeof crate === "object" && crate !== null && "@graph" in crate;
}

export function isWorkflowFile(rocrateFile: ROCrateFile): boolean {
    return rocrateFile.type === "ComputationalWorkflow";
}

export async function extractROCrateSummary(crate: ROCrateImmutableView): Promise<ROCrateSummary> {
    const root = crate.rootDataset;
    if (!root) {
        throw new Error("Invalid RO-Crate file");
    }

    const publicationDate = new Date(root.datePublished);

    let conformsTo: Conforms[] = [];
    if ("conformsTo" in root && Array.isArray(root.conformsTo)) {
        conformsTo = root.conformsTo.map((conform) => {
            const id = conform["@id"];
            const item = crate.graph.find((item) => item["@id"] === id);
            if (!item) {
                throw new Error("Invalid RO-Crate file");
            }
            return {
                id: item["@id"],
                name: String(item.name),
                version: String(item.version),
            };
        });
    }

    const license = String(root.license);

    // TODO: Handle main entity

    const workflows = crate.graph
        .filter((item) => isWorkflow(item))
        .map((workflow) => ({
            id: workflow["@id"],
            name: String(workflow.name),
            type: "ComputationalWorkflow",
            path: workflow["@id"],
        }));

    const files = crate.graph
        .filter((item) => isFile(item))
        .map((dataset) => ({
            id: dataset["@id"],
            name: String(dataset.name),
            type: String(dataset.encodingFormat),
            path: dataset["@id"],
        }));

    // TODO: Handle collections?

    const creators = crate.graph
        .filter((item) => isOfType(item, "Person") || isOfType(item, "Organization"))
        .map((creator) => {
            if (isOfType(creator, "Person")) {
                return {
                    id: creator["@id"],
                    name: String(creator.name),
                    email: String(creator.email),
                    identifier: String(creator.identifier),
                };
            }
            return {
                id: creator["@id"],
                name: String(creator.name),
            };
        });

    return {
        publicationDate,
        conformsTo,
        license,
        workflows,
        files,
        creators,
    };
}
