import axios from "axios";

import type { components } from "@/api";
import { withPrefix } from "@/utils/redirect";
import { rethrowSimple } from "@/utils/simple-error";

export type CompositeFileInfo = components["schemas"]["CompositeFileInfo"];
export type DatatypeDetails = components["schemas"]["DatatypeDetails"];

/**
 * Get details about a specific datatype
 */
export async function fetchDatatypeDetails(extension: string) {
    try {
        const { data } = await axios.get(withPrefix(`/api/datatypes/${extension}`));
        return data;
    } catch (error) {
        rethrowSimple(error);
    }
}
