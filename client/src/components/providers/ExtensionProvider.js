import LookupProvider from "./LookupProvider";
import { sortByObjectProp } from "utils/sorting";
import { prependPath } from "utils/redirect";

const getExtensions = async () => {
    const url = prependPath("api/datatypes?extension_only=False");
    const response = await fetch(url, {
        cache: "force-cache",
    });
    if (!response.ok) {
        throw new Error(response.statusText);
    }
    const data = await response.json();
    const extensions = data.map((d) => {
        const { extension: id, extension: text, description, description_url } = d;
        return { id, text, description, description_url };
    });
    extensions.sort(sortByObjectProp("id"));
    return extensions;
};

export default LookupProvider(getExtensions);
