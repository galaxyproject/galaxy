<template>
    <div v-if="hasInvocationProps">
        <details class="invocation-biocompute-objects">
            <summary><b>Biocompute Object</b></summary>
            <div v-if="hasInvocationProps">
                <details class="invocation-biocompute-object-export">
                    <summary><b>Export BioCompute Object</b></summary>
                    <div>
                        <form v-on:submit.prevent="submitForm">
                            <div class="form-group">
                                <label for="fetch">BCO DB Root URL</label>
                                <input
                                    type="text"
                                    class="form-control"
                                    id="fetch"
                                    placeholder="https://biocomputeobject11.org"
                                    v-model="form.fetch" />
                            </div>
                            <div class="form-group">
                                <label for="authorization">User API Key</label>
                                <input
                                    type="text"
                                    class="form-control"
                                    id="authorization"
                                    v-model="form.authorization" />
                            </div>
                            <div class="form-group">
                                <label for="table">Prefix</label>
                                <input
                                    type="text"
                                    class="form-control"
                                    id="table"
                                    placeholder="BCO"
                                    v-model="form.table" />
                            </div>
                            <div class="form-group">
                                <label for="owner_group">User Name</label>
                                <input type="text" class="form-control" id="owner_group" v-model="form.owner_group" />
                            </div>
                            <div class="form-group">
                                <button class="btn btn-primary">{{ "Submit" | localize }}</button>
                            </div>
                        </form>
                    </div>
                </details>
            </div>
            <div>
                <a class="bco-json" :href="bcoJSON"><b>Download BioCompute Object</b></a>
            </div>
        </details>
    </div>
</template>
<script>
import { getRootFromIndexLink } from "onload";
import { mapGetters } from "vuex";
import axios from "axios";

const getUrl = (path) => getRootFromIndexLink() + path;

export default {
    props: {
        invocation: {
            required: true,
            type: String,
        },
    },
    data() {
        return {
            bco: {
                type: Object,
                required: true,
            },
            form: {
                fetch: "",
                authorization: "",
                table: "",
                owner_group: "",
            },
        };
    },
    created: function () {
        axios
            .get(getUrl(`./api/invocations/${this.invocation}/biocompute/`))
            .then((response) => {
                this.bco = response.data;
            })
            .catch((e) => {
                this.errors.push(e);
            });
    },
    computed: {
        ...mapGetters(["getInvocationById"]),
        indexStr() {
            if (this.index == null) {
                return 0;
            } else {
                return `${this.index + 1}`;
            }
        },
        bcoJSON: function () {
            return getUrl(`api/invocations/${this.invocation}/biocompute/download`);
        },
        hasInvocationProps() {
            return Object.keys(this.invocation).length > 0;
        },
    },
    methods: {
        submitForm() {
            const bcoString = {
                POST_api_objects_draft_create: [
                    {
                        contents: this.bco,
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
                    console.log("response:", response);
                    alert(JSON.parse(response.data.message));
                })
                .catch(function (error) {
                    if (error.response) {
                        alert(JSON.parse(error));
                        console.log("Error response: ", error.response);
                    } else if (error.request) {
                        alert(`Error request: failed to connect to server at ${submitURL}`);
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
