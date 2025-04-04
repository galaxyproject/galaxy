import { type ROCrateEntity, type ROCrateImmutableView } from "ro-crate-zip-explorer";

interface Conforms {
    id: string;
    name: string;
    version: string;
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
    creators: Person[] | Organization[];
}

function isOfType(item: ROCrateEntity, type: string): boolean {
    if (Array.isArray(item["@type"])) {
        return item["@type"].includes(type);
    }
    return item["@type"] === type;
}

export function isCrate(crate: unknown): crate is ROCrateImmutableView {
    return typeof crate === "object" && crate !== null && "@graph" in crate;
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
        creators,
    };
}
