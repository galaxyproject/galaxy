import { ref } from "vue";
import axios from "axios";
import { getAppRoot } from "onload/loadConfig";

/**
 * Fetches a detailed array of datatypes available on this galaxy instance.
 * Does not cache the result or use a store.
 */
export function useDetailedDatatypes() {
    const datatypesLoading = ref(true);
    const datatypes = ref([]);

    async function getDatatypes() {
        try {
            const datatypesPromise = axios.get(`${getAppRoot()}api/datatypes?extension_only=false`);
            const datatypeEDAMFormatsPromise = axios.get(`${getAppRoot()}api/datatypes/edam_formats/detailed`);
            const datatypeEDAMDataPromise = axios.get(`${getAppRoot()}api/datatypes/edam_data/detailed`);

            const [baseTypes, datatypeEDAMFormats, datatypeEDAMData] = await Promise.all([
                datatypesPromise,
                datatypeEDAMFormatsPromise,
                datatypeEDAMDataPromise,
            ]);

            datatypes.value = baseTypes.data.map((type, i) => {
                const typeEDAMFormat = datatypeEDAMFormats.data[type.extension] ?? null;
                const typeEDAMData = datatypeEDAMData.data[type.extension] ?? null;

                return {
                    extension: type.extension,
                    description: type.description,
                    descriptionUrl: type.description_url,
                    edamFormat: typeEDAMFormat.prefix_IRI,
                    edamFormatLabel: typeEDAMFormat.label,
                    edamFormatDefinition: typeEDAMFormat.definition,
                    edamData: typeEDAMData.prefix_IRI,
                    edamDataLabel: typeEDAMData.label,
                    edamDataDefinition: typeEDAMData.definition,
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
