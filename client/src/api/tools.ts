import { type components, GalaxyApi } from "@/api";
import { ERROR_STATES, type ShowFullJobResponse } from "@/api/jobs";
import { errorMessageAsString } from "@/utils/simple-error";

export type HdcaUploadTarget = components["schemas"]["HdcaDataItemsTarget"];
export type HdasUploadTarget = components["schemas"]["DataElementsTarget"];
export type FetchDataPayload = components["schemas"]["FetchDataPayload"];
export type FileDataElement = components["schemas"]["FileDataElement"];
export type PastedDataElement = components["schemas"]["PastedDataElement"];
export type UrlDataElement = components["schemas"]["UrlDataElement"];
export type CompositeDataElement = components["schemas"]["CompositeDataElement"];
export type FetchDatasetHash = components["schemas"]["FetchDatasetHash"];
export type NestedElement = components["schemas"]["NestedElement"];
export type NestedElementItems = NestedElement["elements"];
export type NestedElementItem = NestedElementItems[number];
export type FetchTargets = FetchDataPayload["targets"];
export type AnyFetchTarget = FetchTargets[number];

export type ApiDataElement = FileDataElement | PastedDataElement | UrlDataElement;

export interface ToolIdentifier {
    toolId: string;
    toolVersion: string;
}

export function getToolKey(toolId: string, toolVersion: string): string {
    return `${toolId}@${toolVersion}`;
}

export function urlDataElement(identifier: string, uri: string): UrlDataElement {
    const element: UrlDataElement = {
        src: "url",
        url: uri,
        name: identifier,
        // these shouldn't be required but the way our model -> ts stuff works it is...
        auto_decompress: false,
        dbkey: "?",
        ext: "auto",
        to_posix_lines: false,
        deferred: false,
        space_to_tab: false,
    };
    return element;
}

export function nestedElement(identifier: string, elements: NestedElement["elements"]) {
    const nestedElement: NestedElement = {
        name: identifier,
        elements: elements,
        auto_decompress: false,
        dbkey: "?",
        ext: "auto",
        to_posix_lines: false,
        deferred: false,
        space_to_tab: false,
    };
    return nestedElement;
}

export async function fetchDatasetsToJobId(payload: FetchDataPayload) {
    const { data } = await GalaxyApi().POST("/api/tools/fetch", {
        body: payload,
    });
    return fetchResponseToJobId(data as FetchDataResponse);
}

/**
 * Fetches datasets into Galaxy via the /api/tools/fetch endpoint.
 * Uses callback-based result handling for upload trackers.
 *
 * @param payload - The fetch data payload defining datasets to import
 * @param callbacks - Optional callbacks for success/error/progress events
 */
export async function fetchDatasets(payload: FetchDataPayload, callbacks: FetchDatasetsCallbacks = {}): Promise<void> {
    try {
        const { data, error } = await GalaxyApi().POST("/api/tools/fetch", {
            body: payload,
        });

        if (error) {
            throw new Error(error.err_msg || "Upload request failed");
        }

        callbacks.success?.(data as FetchDataResponse);
    } catch (error) {
        const errorMessage = errorMessageAsString(error);
        callbacks.error?.(errorMessage);
    }
}

// TODO: The response is not modeled yet in the FastAPI route for /api/tools/fetch
// so we define a minimal interface here for our needs.
// Once the route is properly modeled, we can replace this minimal placeholder interface.
export interface FetchDataResponse {
    jobs: { id: string }[];
    outputs?: Record<string, unknown>;
}

/**
 * Callback functions for dataset fetch/upload lifecycle events.
 */
export interface FetchDatasetsCallbacks {
    /** Called when the request completes successfully */
    success?: (response: FetchDataResponse) => void;
    /** Called when an error occurs */
    error?: (error: string | Error) => void;
    /** Called with warning messages */
    warning?: (message: string) => void;
    /** Called with progress percentage (0-100) for uploads */
    progress?: (percentage: number) => void;
}

function fetchResponseToJobId(response: FetchDataResponse) {
    return response.jobs[0]!.id;
}

export function fetchJobErrorMessage(jobDetails: ShowFullJobResponse): string | undefined {
    const stderr = jobDetails.stderr;
    let errorMessage: string | undefined = undefined;
    if (stderr) {
        errorMessage = "An error was encountered while running your upload job. ";
        if (stderr.indexOf("binary file contains inappropriate content") > -1) {
            errorMessage +=
                "The problem may be that the batch uploader will not automatically decompress your files the way the normal uploader does, please specify a correct extension or upload decompressed data.";
        }
        errorMessage += "Upload job completed with standard error: " + stderr;
    } else if (ERROR_STATES.indexOf(jobDetails.state) !== -1) {
        errorMessage =
            "Unknown error encountered while running your data import job, this could be a server issue or a problem with the upload definition.";
    }
    return errorMessage;
}

export async function getToolInputs(tool_id: string, tool_version: string) {
    return GalaxyApi().GET(`/api/tools/{tool_id}/inputs`, {
        params: {
            query: { tool_version },
            path: { tool_id },
        },
    });
}
