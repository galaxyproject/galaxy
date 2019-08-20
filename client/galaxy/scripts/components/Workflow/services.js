import axios from "axios";

/** Workflow data request helper **/
export class Services {
    constructor(options = {}) {
        this.root = options.root;
    }

    getWorkflows() {
        return new Promise((resolve, reject) => {
            axios
                .get(`${this.root}api/workflows`)
                .then(response => {
                    let workflows = response.data;
                    for (workflow of workflows) {
                        workflow.create_time = workflow.create_time.substring(0, 10);
                        if (workflow.annotations && workflow.annotations.length > 0) {
                            workflow.annotations = workflow.annotations[0].trim();
                        }
                        if (!workflow.annotations) {
                            workflow.annotations = "Not available.";
                        }
                    }
                    resolve(workflows);
                })
                .catch(e => {
                    let errorMessage = "Request failed.";
                    if (e.response) {
                        errorMessage = e.response.data.err_msg || `${e.response.statusText} (${e.response.status})`;
                    }
                    reject(errorMessage);
                });
        });
    }
}
