<!--
    WARNING
    This component is temporal and should be dropped once Celery is the default task system in Galaxy.
    The plugin system should be used instead.
-->
<template>
    <div>
        <p>
            A BioCompute Object (BCO) is the unofficial name for a JSON object that adheres to the
            <a href="https://standards.ieee.org/ieee/2791/7337/">IEEE-2791-2020 standard</a>. A BCO is designed to
            communicate High-throughput Sequencing (HTS) analysis results, data set creation, data curation, and
            bioinformatics verification protocols.
        </p>
        <p>Learn more about <a href="https://biocomputeobject.org/" target="_blank">BioCompute Objects</a>.</p>
        <p>
            Instructions for
            <a href="https://w3id.org/biocompute/tutorials/galaxy_quick_start" target="_blank"
                >creating a BCO using Galaxy</a
            >.
        </p>
        <b-tabs lazy>
            <b-tab title="Download">
                <a class="bco-json" style="padding-left: 1em" :href="bcoDownloadLink"><b>Download BCO</b></a>
            </b-tab>
            <b-tab title="Submit To BCODB">
                <div>
                    <p>
                        To submit to a BCODB you need to already have an authenticated account. Instructions on
                        submitting a BCO from Galaxy are available
                        <a href="https://w3id.org/biocompute/tutorials/galaxy_quick_start/" target="_blank">here</a>.
                    </p>
                    <form @submit.prevent="submitForm">
                        <div class="form-group">
                            <label for="fetch">
                                <input
                                    id="fetch"
                                    v-model="form.fetch"
                                    type="text"
                                    class="form-control"
                                    placeholder="https://biocomputeobject.org"
                                    autocomplete="off"
                                    required />
                                BCO DB URL (example: https://biocomputeobject.org)
                            </label>
                        </div>
                        <div class="form-group">
                            <label for="authorization">
                                <input
                                    id="authorization"
                                    v-model="form.authorization"
                                    type="password"
                                    class="form-control"
                                    autocomplete="off"
                                    required />
                                User API Key
                            </label>
                        </div>
                        <div class="form-group">
                            <label for="table">
                                <input
                                    id="table"
                                    v-model="form.table"
                                    type="text"
                                    class="form-control"
                                    placeholder="GALXY"
                                    required />
                                Prefix
                            </label>
                        </div>
                        <div class="form-group">
                            <label for="owner_group">
                                <input
                                    id="owner_group"
                                    v-model="form.owner_group"
                                    type="text"
                                    class="form-control"
                                    autocomplete="off"
                                    required />
                                User Name
                            </label>
                        </div>
                        <div class="form-group">
                            <button class="btn btn-primary">{{ "Submit" | localize }}</button>
                        </div>
                    </form>
                </div>
            </b-tab>
        </b-tabs>
    </div>
</template>

<script>
import axios from "axios";
import { getRootFromIndexLink } from "onload";
import { getAppRoot } from "onload/loadConfig";

const getUrl = (path) => getRootFromIndexLink() + path;
export default {
    props: {
        invocationId: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            form: {
                fetch: "",
                authorization: "",
                table: "",
                owner_group: "",
            },
        };
    },
    computed: {
        bcoDownloadLink: function () {
            return `${getAppRoot()}api/invocations/${this.invocationId}/biocompute/download`;
        },
    },
    methods: {
        async submitForm() {
            const bco = await axios
                .get(getUrl(`./api/invocations/${this.invocationId}/biocompute/`))
                .then((response) => {
                    this.bco = response.data;
                    return this.bco;
                })
                .catch((e) => {
                    this.errors.push(e);
                });
            const bcoString = {
                POST_api_objects_draft_create: [
                    {
                        contents: bco,
                        owner_group: this.form.owner_group,
                        schema: "IEEE",
                        prefix: this.form.table,
                    },
                ],
            };
            const headers = {
                Authorization: "Token " + this.form.authorization,
                "Content-type": "application/json; charset=UTF-8",
            };
            const submitURL = this.form.fetch;
            axios
                .post(`${submitURL}/api/objects/drafts/create/`, bcoString, { headers: headers })
                .then((response) => {
                    if (response.status === 200) {
                        console.log("response:", response);
                        alert(response.data[0].message);
                    }
                    if (response.status === 207) {
                        console.log("response:", response);
                        alert(response.data[0].message);
                    }
                })
                .catch(function (error) {
                    console.log("Error", { ...error });
                    if (error.response.status == 401) {
                        alert(error.response.data.detail);
                        console.log("Error response: ", error);
                    } else {
                        console.log("Error", error);
                        alert("Error", error);
                    }
                });
            this.form.owner_group = "";
            this.form.authorization = "";
            this.form.owner_group = "";
            this.form.fetch = "";
        },
    },
};
</script>
