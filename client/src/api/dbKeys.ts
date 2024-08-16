/**
 * Historically, this API was used to get the list of genomes that were available
 * but now it is used to get the list of more generic "dbkeys".
 */

import { GalaxyApi } from "@/api";
import { rethrowSimple } from "@/utils/simple-error";

export async function getDbKeys() {
    const { data, error } = await GalaxyApi().GET("/api/genomes");
    if (error) {
        rethrowSimple(error);
    }
    return data;
}
