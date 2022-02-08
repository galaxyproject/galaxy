import { SingleQueryProvider } from "components/providers/SingleQueryProvider";

async function getDatasetCollection({ id }) {
    const url = `${getAppRoot()}api/dataset_collections/${id}?instance_type=history`;
    try {
        const { data } = await axios.get(url);
        return data;
    } catch (e) {
        rethrowSimple(e);
    }
}

export default SingleQueryProvider(getDatasetCollection);
