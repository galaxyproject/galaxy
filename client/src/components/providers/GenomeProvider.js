import LookupProvider from "./LookupProvider";
import { sortByObjectProp } from "utils/sorting";
import { prependPath } from "utils/redirect";

const getGenomes = async () => {
    const url = prependPath("api/genomes");
    const response = await fetch(url, {
        cache: "force-cache",
    });
    if (!response.ok) {
        throw new Error(response.statusText);
    }
    const data = await response.json();
    const genomes = data.map((row) => {
        const [text, id] = row;
        return { id, text };
    });
    genomes.sort(sortByObjectProp("id"));
    return genomes;
};

export default LookupProvider(getGenomes);
