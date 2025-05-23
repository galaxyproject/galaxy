import { type components, GalaxyApi } from "@/api";
import { ERROR_STATES, type ShowFullJobResponse } from "@/api/jobs";

export type HdcaUploadTarget = components["schemas"]["HdcaDataItemsTarget"];
export type FetchDataPayload = components["schemas"]["FetchDataPayload"];
export type UrlDataElement = components["schemas"]["UrlDataElement"];
export type NestedElement = components["schemas"]["NestedElement"];

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

export async function fetch(payload: FetchDataPayload) {
    const { data } = await GalaxyApi().POST("/api/tools/fetch", {
        body: payload,
    });
    return fetchResponseToJobId(data as FetchResponseInterface);
}

interface FetchResponseInterface {
    jobs: { id: string }[];
}

function fetchResponseToJobId(response: FetchResponseInterface) {
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
