// TODO: consider moving these types and logic to ro-crate-zip-explorer
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
    type: "Person";
}

interface Organization {
    id: string;
    name: string;
    type: "Organization";
}

type Creator = Person | Organization;

export interface ROCrateSummary {
    name: string;
    description: string;
    publicationDate: Date;
    conformsTo: Conforms[];
    license: string;
    creators: Creator[];
    identifier?: string;
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

    // Try to get the root dataset name, if not available, try to get the mainEntity name
    const name =
        root.name ??
        (typeof root.mainEntity === "object" && root.mainEntity && "name" in root.mainEntity
            ? String(root.mainEntity.name)
            : "Unknown");

    const publicationDate = new Date(root.datePublished);

    let identifier = root.identifier;
    if (typeof identifier === "object") {
        identifier = identifier["@id"];
    }

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

    let license = root.license ? String(root.license) : "Unknown";
    if (typeof root.license === "object") {
        license = root.license["@id"];
        const licenseEntity = crate.getEntity(license);
        if (licenseEntity && "name" in licenseEntity) {
            license = String(licenseEntity.name);
        }
    }

    const creators = crate.graph
        .filter((item) => isOfType(item, "Person") || isOfType(item, "Organization"))
        .map((creator) => {
            if (isOfType(creator, "Person")) {
                const person: Person = {
                    id: creator["@id"],
                    name: String(creator.name),
                    email: String(creator.email),
                    identifier: String(creator.identifier),
                    type: "Person",
                };
                return person;
            }
            const organization: Organization = {
                id: creator["@id"],
                name: String(creator.name),
                type: "Organization",
            };
            return organization;
        });

    return {
        name,
        description: root.description,
        publicationDate,
        conformsTo,
        license,
        creators,
        identifier,
    };
}
