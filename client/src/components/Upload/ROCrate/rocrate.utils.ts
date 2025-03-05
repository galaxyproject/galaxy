export function validateLocalZipFile(file?: File | null): string {
    if (!file) {
        return "No file selected";
    }

    if (file.type !== "application/zip") {
        return "Invalid file type. Please select a ZIP file.";
    }

    return "";
}

const KNOWN_IGNORED_FILES = [
    "collections_attrs.txt",
    "datasets_attrs.txt",
    "datasets_attrs.txt.provenance",
    "export_attrs.txt",
    "implicit_collection_jobs_attrs.txt",
    "implicit_dataset_conversions.txt",
    "invocation_attrs.txt",
    "jobs_attrs.txt",
    "libraries_attrs.txt",
    "library_folders_attrs.txt",
];

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

function isOfType(item: GraphItem, type: string): boolean {
    if (Array.isArray(item["@type"])) {
        return item["@type"].includes(type);
    }
    return item["@type"] === type;
}

function shouldBeIgnored(item: GraphItem): boolean {
    return KNOWN_IGNORED_FILES.some((ignoredFile) => item["@id"].includes(ignoredFile));
}

function isWorkflow(item: GraphItem): boolean {
    return isOfType(item, "ComputationalWorkflow") && item["@id"].endsWith(".gxwf.yml");
}

function isFile(item: GraphItem): boolean {
    return (
        isOfType(item, "File") &&
        !shouldBeIgnored(item) &&
        !isOfType(item, "ComputationalWorkflow") &&
        !item["@id"].startsWith("workflows/")
    );
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

    // TODO: Handle main entity

    const workflows = crate["@graph"]
        .filter((item) => isWorkflow(item))
        .map((workflow) => ({
            id: workflow["@id"],
            name: String(workflow.name),
            type: "ComputationalWorkflow",
            path: workflow["@id"],
        }));

    const files = crate["@graph"]
        .filter((item) => isFile(item))
        .map((dataset) => ({
            id: dataset["@id"],
            name: String(dataset.name),
            type: String(dataset.encodingFormat),
            path: dataset["@id"],
        }));

    // TODO: Handle collections?

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
        files,
        creators,
    };
}
