import axios from "axios";

import { withPrefix } from "@/utils/redirect";
import { rethrowSimple } from "@/utils/simple-error";

/**
 * Interface for datatype to visualization mapping
 */
export interface DatatypeVisualization {
    datatype: string; // Datatype extension (e.g., "h5", "tabular")
    visualization: string; // Visualization plugin name
}

/**
 * Fetches the list of datatype to visualization mappings
 */
export async function fetchDatatypeVisualizations(): Promise<DatatypeVisualization[]> {
    try {
        const { data } = await axios.get(withPrefix("/api/datatypes/visualizations"));
        return data;
    } catch (error) {
        rethrowSimple(error);
    }
}

/**
 * Gets the preferred visualization for a specific datatype
 */
export async function getPreferredVisualization(datatype: string): Promise<DatatypeVisualization | null> {
    try {
        const url = withPrefix(`/api/datatypes/${datatype}/visualizations`);
        const { data } = await axios.get(url);

        // If the API returns an array with one item, return that item
        if (Array.isArray(data) && data.length === 1) {
            return data[0];
        }

        return data;
    } catch (error) {
        // Return null if no preferred visualization is found
        if (axios.isAxiosError(error) && error.response?.status === 404) {
            return null;
        }
        rethrowSimple(error);
    }
}
