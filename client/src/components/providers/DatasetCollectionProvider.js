import { SingleQueryProvider } from "components/providers/SingleQueryProvider";

import { fetchCollectionDetails } from "@/api/datasetCollections";

// There isn't really a good way to know when to stop polling for HDCA updates,
// but we know the populated_state should at least be ok.
export default SingleQueryProvider(fetchCollectionDetails, (result) => result.populated_state === "ok");
