export function validateLocalZipFile(file?: File | null): string {
    if (!file) {
        return "No file selected";
    }

    if (file.type !== "application/zip") {
        return "Invalid file type. Please select a ZIP file.";
    }

    return "";
}

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
    datasets: ROCrateFile[];
    creators: Person[] | Organization[];
}

function isOfType(item: unknown, type: string): boolean {
    if (typeof item === "object" && item !== null && "@type" in item) {
        if (Array.isArray(item["@type"])) {
            return item["@type"].includes(type);
        }
        return item["@type"] === type;
    }
    return false;
}

interface GraphItem {
    "@id": string;
    "@type": string | string[];
    [key: string]: unknown;
}

interface HasGraph {
    "@context": string[];
    "@graph": GraphItem[];
}

export function isCrate(crate: unknown): crate is HasGraph {
    return typeof crate === "object" && crate !== null && "@graph" in crate;
}

export async function extractROCrateSummary(crate: HasGraph): Promise<ROCrateSummary> {
    const root = crate["@graph"].find((item: GraphItem) => item["@id"] === "./");
    if (!root) {
        throw new Error("Invalid RO-Crate file");
    }

    const publicationDate = new Date(root.datePublished as string);

    let conformsTo: Conforms[] = [];
    if ("conformsTo" in root && Array.isArray(root.conformsTo)) {
        conformsTo = root.conformsTo.map((conform) => {
            const id = conform["@id"];
            const item = crate["@graph"].find((item) => item["@id"] === id);
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

    const workflows = crate["@graph"]
        .filter((item) => isOfType(item, "ComputationalWorkflow"))
        .map((workflow) => ({
            id: workflow["@id"],
            name: String(workflow.name),
            type: "ComputationalWorkflow",
            path: workflow["@id"],
        }));

    const datasets = crate["@graph"]
        .filter((item) => isOfType(item, "File"))
        .map((dataset) => ({
            id: dataset["@id"],
            name: String(dataset.name),
            type: String(dataset.encodingFormat),
            path: dataset["@id"],
        }));

    const creators = crate["@graph"]
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
        datasets,
        creators,
    };
}
