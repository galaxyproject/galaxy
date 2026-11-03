import type { components } from "@/api";
import { GalaxyApi } from "@/api";
import { rethrowSimple } from "@/utils/simple-error";

export type CompositeFileInfo = components["schemas"]["CompositeFileInfo"];
export type DatatypeDetails = components["schemas"]["DatatypeDetails"];
export type DatatypeConverter = components["schemas"]["DatatypeConverter"];

/**
 * Get details about a specific datatype
 */
export async function fetchDatatypeDetails(extension: string): Promise<DatatypeDetails> {
    try {
        const { GET } = GalaxyApi();
        const { data } = await GET("/api/datatypes/{datatype}", {
            params: {
                path: { datatype: extension },
            },
        });
        if (!data) {
            throw new Error(`Failed to fetch datatype details for ${extension}`);
        }
        return data as DatatypeDetails;
    } catch (error) {
        rethrowSimple(error);
    }
}

/**
 * Get every installed datatype converter as source/target extension pairs
 */
export async function fetchDatatypeConverters(): Promise<DatatypeConverter[]> {
    const { data, error } = await GalaxyApi().GET("/api/datatypes/converters");
    if (error) {
        rethrowSimple(error);
    }
    return data;
}
