import axios from "axios";

import { Toast } from "@/composables/toast";
import { withPrefix } from "@/utils/redirect";
import { errorMessageAsString } from "@/utils/simple-error";
import { wait } from "@/utils/utils";

/**
 * Data needed to send a BioCompute Object to a BCODB server.
 */
export interface BcoDatabaseExportData {
    serverBaseUrl: string;
    authorization: string;
    table: string;
    ownerGroup: string;
}

/**
 * Generate a BioCompute Object from an invocation and send it to a BCODB server.
 * @param invocationId The ID of the invocation to export.
 * @param inputData The data needed to send the BCO to the BCODB.
 */
export async function saveInvocationBCOToDatabase(invocationId: string, inputData: BcoDatabaseExportData) {
    try {
        const bcoContent = await generateBcoContent(invocationId);
        await sendBco(bcoContent, inputData);
        Toast.success(`Invocation successfully sent to: ${inputData.serverBaseUrl}`);
    } catch (err) {
        Toast.error(errorMessageAsString(err), "Error sending BioCompute Object to BCODB");
    }
}

async function generateBcoContent(invocationId: string) {
    const data = {
        model_store_format: "bco.json",
        include_files: false,
        include_deleted: false,
        include_hidden: false,
    };
    const response = await axios.post(withPrefix(`/api/invocations/${invocationId}/prepare_store_download`), data);
    const storage_request_id = response.data.storage_request_id;
    const pollUrl = withPrefix(`/api/short_term_storage/${storage_request_id}/ready`);
    const resultUrl = withPrefix(`/api/short_term_storage/${storage_request_id}`);
    let pollingResponse = await axios.get(pollUrl);
    let maxRetries = 120;
    while (!pollingResponse.data && maxRetries) {
        await wait(2000);
        pollingResponse = await axios.get(pollUrl);
        maxRetries -= 1;
    }
    if (!pollingResponse.data) {
        throw Error("Timeout waiting for BioCompute Object export result!");
    } else {
        const resultResponse = await axios.get(resultUrl);
        return resultResponse.data;
    }
}

async function sendBco(bcoContent: string, inputData: BcoDatabaseExportData) {
    const bcoData = {
        POST_api_objects_draft_create: [
            {
                contents: bcoContent,
                owner_group: inputData.ownerGroup,
                schema: "IEEE",
                prefix: inputData.table,
            },
        ],
    };

    const headers = {
        Authorization: "Token " + inputData.authorization,
        "Content-type": "application/json; charset=UTF-8",
    };
    await axios.post(`${inputData.serverBaseUrl}/api/objects/drafts/create/`, bcoData, { headers: headers });
}
