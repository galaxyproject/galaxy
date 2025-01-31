import { GalaxyApi } from "@/api";
import { type HDADetailed } from "@/api";
import { errorMessageAsString } from "@/utils/simple-error";

export type ReportType = "dataset" | "tool";

export async function dispatchReport(
    reportType: ReportType,
    reportableData: HDADetailed | any, // TODO Better option for Tools than "any" ?
    message: string,
    email: string
) {
    if (reportType === "dataset") {
        return await submitReportDataset(reportableData, message, email);
    } else {
        return await submitReportTool(reportableData, message, email);
    }
}

export async function submitReportDataset(
    reportableData: HDADetailed,
    message: string,
    email: string
): Promise<{ messages: string[][]; error?: string }> {
    try {
        const { data, error } = await GalaxyApi().POST("/api/jobs/{job_id}/error", {
            params: {
                path: { job_id: reportableData.creating_job },
            },
            body: {
                dataset_id: reportableData.id,
                message,
                email,
            },
        });

        if (error) {
            return { messages: [], error: errorMessageAsString(error) };
        }
        return { messages: data.messages };
    } catch (err) {
        return { messages: [], error: errorMessageAsString(err) };
    }
}

export async function submitReportTool(
    reportableData: any,
    message: string,
    email: string
): Promise<{ messages: string[][]; error?: string }> {
    try {
        const { data, error } = await GalaxyApi().POST("/api/tools/{tool_id}/error", {
            params: {
                path: {
                    tool_id: reportableData.tool_id,
                },
            },
            body: {
                reportable_data: reportableData,
                message,
                email,
            },
        });

        if (error) {
            return { messages: [], error: errorMessageAsString(error) };
        }
        // return { messages: data.messages };
        return { messages: [["Success!", "success"]] };
    } catch (err) {
        console.log("api error (err)", err);
        return { messages: [], error: errorMessageAsString(err) };
    }
}
