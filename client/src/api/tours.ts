import { type components, GalaxyApi } from "@/api";
import { rethrowSimple } from "@/utils/simple-error";

export type TourDetails = components["schemas"]["TourDetails"];
export type TourSummary = components["schemas"]["Tour"];
export type TourRequirements = components["schemas"]["TourDetails"]["requirements"];
export type TourStep = components["schemas"]["TourStep"];

export async function getTourData(tourId: string) {
    const { data, error } = await GalaxyApi().GET("/api/tours/{tour_id}", {
        params: { path: { tour_id: tourId } },
    });
    if (error) {
        rethrowSimple(error);
    }
    return data;
}

export async function generateTour(toolId: string, toolVersion: string) {
    const { data, error } = await GalaxyApi().GET("/api/tours/generate", {
        params: {
            query: {
                tool_id: toolId,
                tool_version: toolVersion,
            },
        },
    });
    if (error) {
        rethrowSimple(error);
    }
    return data;
}
