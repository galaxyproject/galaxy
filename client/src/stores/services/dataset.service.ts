import { fetcher } from "@/api/schema";

import { DatasetDetails } from ".";

const getDataset = fetcher.path("/api/datasets/{dataset_id}").method("get").create();

export async function fetchDatasetDetails(params: { id: string }): Promise<DatasetDetails> {
    const { data } = await getDataset({ dataset_id: params.id, view: "detailed" });
    // We know that the server will return a DatasetDetails object because of the view parameter
    // but the type system doesn't, so we have to cast it.
    return data as unknown as DatasetDetails;
}
