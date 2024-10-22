import { fetchDatasetDetails } from "@/api/datasets";
import { SingleQueryProvider } from "@/components/providers/SingleQueryProvider";

import { stateIsTerminal } from "./utils";

export default SingleQueryProvider(fetchDatasetDetails, stateIsTerminal);
