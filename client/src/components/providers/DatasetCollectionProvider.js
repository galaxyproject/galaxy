import { fetchCollectionDetails, fetchCollectionSummary } from "@/api/datasetCollections";
import { SingleQueryProvider } from "@/components/providers/SingleQueryProvider";

// There isn't really a good way to know when to stop polling for HDCA updates,
// but we know the populated_state should at least be ok.
export default SingleQueryProvider(
    (params) => {
        if (params.view && params.view === "collection") {
            return fetchCollectionSummary({ hdca_id: params.id });
        }
        return fetchCollectionDetails({ hdca_id: params.id });
    },
    (result) => result.populated_state === "ok",
);
