import axios from "axios";
import { rethrowSimple } from "utils/simple-error";
import { getAppRoot } from "onload/loadConfig";

export class Services {
    constructor(options = {}) {
        this.root = options.root || getAppRoot();
    }

    async getActiveInteractiveTools() {
        const url = `${this.root}api/entry_points?running=true`;
        try {
            const response = await axios.get(url);
            return response.data;
        } catch (e) {
            rethrowSimple(e);
        }
    }

    async stopInteractiveTool(ids) {
        const url = `${this.root}interactivetool/list`;
        const formData = new FormData();
        formData.append("operation", "stop");
        ids.forEach((id) => formData.append("id", id));
        const response = await axios.post(url, formData);
        return response.data;
    }
    catch(e) {
        rethrowSimple(e);
    }
}
