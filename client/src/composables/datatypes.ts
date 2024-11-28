import { type Ref, ref } from "vue";

import { GalaxyApi } from "@/api";
import { rethrowSimple } from "@/utils/simple-error";

export interface DetailedDatatypes {
    extension: string;
    description?: string | null;
    descriptionUrl?: string | null;
    edamFormat?: string | null;
    edamFormatLabel?: string | null;
    edamFormatDefinition?: string | null;
    edamData?: string | null;
    edamDataLabel?: string | null;
    edamDataDefinition?: string | null;
}

/**
 * Fetches a detailed array of datatypes available on this galaxy instance.
 * Does not cache the result or use a store.
 */
export function useDetailedDatatypes() {
    const datatypesLoading = ref(true);
    const datatypes: Ref<DetailedDatatypes[]> = ref([]);

    async function getDatatypes() {
        try {
            const datatypesPromise = GalaxyApi().GET("/api/datatypes", {
                params: { query: { extension_only: false } },
            });
            const datatypeEDAMFormatsPromise = GalaxyApi().GET("/api/datatypes/edam_formats/detailed");
            const datatypeEDAMDataPromise = GalaxyApi().GET("/api/datatypes/edam_data/detailed");

            const [
                { data: baseData, error: baseError },
                { data: datatypeEDAMFormats, error: edamFormatsError },
                { data: datatypeEDAMData, error: edamDataError },
            ] = await Promise.all([datatypesPromise, datatypeEDAMFormatsPromise, datatypeEDAMDataPromise]);

            type BaseTypes = Exclude<typeof baseData, string[]>;

            const error = baseError || edamFormatsError || edamDataError;
            if (error) {
                rethrowSimple(error);
            }

            const items = baseData as BaseTypes;
            // We can safely use non-null assertions here because otherwise we would have thrown an error
            datatypes.value = items!.map((type) => {
                const typeEDAMFormat = datatypeEDAMFormats![type.extension] ?? null;
                const typeEDAMData = datatypeEDAMData![type.extension] ?? null;

                return {
                    extension: type.extension,
                    description: type.description,
                    descriptionUrl: type.description_url,
                    edamFormat: typeEDAMFormat?.prefix_IRI,
                    edamFormatLabel: typeEDAMFormat?.label,
                    edamFormatDefinition: typeEDAMFormat?.definition,
                    edamData: typeEDAMData?.prefix_IRI,
                    edamDataLabel: typeEDAMData?.label,
                    edamDataDefinition: typeEDAMData?.definition,
                };
            });
        } catch (e) {
            console.error("unable to fetch available datatypes\n", e);
        } finally {
            datatypesLoading.value = false;
        }
    }

    getDatatypes();

    return { datatypes, datatypesLoading };
}
