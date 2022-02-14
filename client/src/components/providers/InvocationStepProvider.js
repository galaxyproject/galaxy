import axios from "axios";
import { getAppRoot } from "onload/loadConfig";
import { SingleQueryProvider } from "components/providers/SingleQueryProvider";
import { rethrowSimple } from "utils/simple-error";

async function getInvocation({ id }) {
    try {
        const { data } = await axios.get(`${getAppRoot()}api/invocations/any/steps/${id}`);
        return data;
    } catch (e) {
        rethrowSimple(e);
    }
}

export default SingleQueryProvider(getInvocation);
