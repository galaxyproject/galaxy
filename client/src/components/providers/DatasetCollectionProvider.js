import { fetchCollectionDetails, fetchCollectionSummary } from "@/api/datasetCollections";
import { SingleQueryProvider } from "@/components/providers/SingleQueryProvider";

// There isn't really a good way to know when to stop polling for HDCA updates,
// but we know the populated_state should at least be ok.
export default SingleQueryProvider(
    async (params) => {
        if (params.view && params.view === "collection") {
            return fetchCollectionSummary({ hdca_id: params.id });
        }
        const result = await fetchCollectionDetails({ hdca_id: params.id });
        if (result.error) {
            throw result.error;
        }
        return result.data;
    },
    (result) => result.populated_state === "ok",
);
