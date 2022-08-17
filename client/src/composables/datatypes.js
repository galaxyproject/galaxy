import { ref } from "vue";
import axios from "axios";
import { getAppRoot } from "onload/loadConfig";

export function useGetDetailedDatatypes() {
    const datatypesLoading = ref(true);
    const datatypes = ref([]);

    async function getDatatypes() {
        const datatypesPromise = axios.get(`${getAppRoot()}api/datatypes?extension_only=false`);
        const datatypeEDAMFormatsPromise = axios.get(`${getAppRoot()}api/datatypes/edam_formats?id_only=false`);
        const datatypeEDAMDataPromise = axios.get(`${getAppRoot()}api/datatypes/edam_data?id_only=false`);

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
                edamFormat: typeEDAMFormat.prefix_IRI,
                edamFormatLabel: typeEDAMFormat.label,
                edamFormatDefinition: typeEDAMFormat.definition,
                edamData: typeEDAMData.prefix_IRI,
                edamDataLabel: typeEDAMData.label,
                edamDataDefinition: typeEDAMData.definition,
            };
        });

        datatypesLoading.value = false;
    }

    try {
        getDatatypes();
    } catch (e) {
        console.error("unable to fetch available datatypes\n", e);
    }

    return { datatypes, datatypesLoading };
}
