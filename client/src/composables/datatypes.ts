import { ref } from "vue";
import { fetcher } from "@/schema";

import type { Ref } from "vue";

const datatypesFetcher = fetcher.path("/api/datatypes").method("get").create();
const edamFormatsFetcher = fetcher.path("/api/datatypes/edam_formats/detailed").method("get").create();
const edamDataFetcher = fetcher.path("/api/datatypes/edam_data/detailed").method("get").create();

export interface DetailedDatatypes {
    extension: string;
    description?: string;
    descriptionUrl?: string;
    edamFormat?: string;
    edamFormatLabel?: string;
    edamFormatDefinition?: string;
    edamData?: string;
    edamDataLabel?: string;
    edamDataDefinition?: string;
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
            const datatypesPromise = datatypesFetcher({ extension_only: false });
            const datatypeEDAMFormatsPromise = edamFormatsFetcher({});
            const datatypeEDAMDataPromise = edamDataFetcher({});

            const [baseTypes, datatypeEDAMFormats, datatypeEDAMData] = await Promise.all([
                datatypesPromise,
                datatypeEDAMFormatsPromise,
                datatypeEDAMDataPromise,
            ]);

            type BaseTypes = Exclude<typeof baseTypes.data, string[]>;

            datatypes.value = (baseTypes.data as BaseTypes).map((type) => {
                const typeEDAMFormat = datatypeEDAMFormats.data[type.extension] ?? null;
                const typeEDAMData = datatypeEDAMData.data[type.extension] ?? null;

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
