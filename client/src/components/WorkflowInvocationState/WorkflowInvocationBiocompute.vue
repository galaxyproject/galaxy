<template>
    <div v-if="Object.keys(invocation).length">
        <details class="invocation-biocompute-objects">
            <summary><b>Biocompute Object</b></summary>
            <div v-if="Object.keys(invocation).length">
                <details class="invocation-biocompute-object-export">
                    <summary><b>Export BioCompute Object</b></summary>
                     <div>
                         <form v-on:submit.prevent="submitForm">
                             <div class="form-group">
                                 <label for="fetch">BCO DB Root URL</label>
                                 <input type="text" 
                                  class="form-control"
                                  id="fetch" 
                                  placeholder="https://beta.portal.aws.biochemistry.gwu.edu" 
                                  v-model="form.fetch">
                             </div>
                             <div class="form-group">
                                 <label for="authorization">User API Key</label>
                                 <input type="text" 
                                  class="form-control"
                                  id="authorization" 
                                  v-model="form.authorization">
                            </div>
                            <div class="form-group">
                                 <label for="table">Table</label>
                                 <input type="text"
                                  class="form-control"
                                  id="table"
                                  placeholder="bco_draft"
                                  v-model="form.table">
                            </div>
                            <div class="form-group">
                                 <label for="owner_group">Group</label>
                                 <input type="text"
                                  class="form-control" 
                                  id="owner_group" 
                                  placeholder="bco_drafters"
                                  v-model="form.owner_group">
                            </div>
                            <div class="form-group">
                                 <button class="btn btn-primary">Submit</button>
                            </div>
                        </form>
                      </div>
                </details>
            </div>
            <div><a class="bco-json" :href="bcoJSON"><b>Download BioCompute Object</b></a></div>
        </details>
    </div>
</template>
<script>

import { getRootFromIndexLink } from "onload";
import { mapGetters, mapActions } from "vuex";
import axios from "axios";

const getUrl = (path) => getRootFromIndexLink() + path;

export default {
    props: {
        invocation: {
            required: true,
        },
    },
    data() {
        return {
            bco: {
                type: Object,
                required: true,
            },
            form: {
                fetch: '',
                authorization: '',
                table: '',
                owner_group: ''
            },
        };
    },
    created: function () {
        axios.get(getUrl(`./api/invocations/${this.invocation}/biocompute/`))
            .then(response => {this.bco = response.data})
            .catch(e => {this.errors.push(e)});
    },
    computed: {
        ...mapGetters(["getInvocationById"]),
        invocation2: function () {
            return this.$store.state.user.currentUser;
        },
        indexStr() {
            if (this.index == null) {
                return 0;
            } else {
                return `${this.index + 1}`;
            }
        },
        bcoJSON: function () {
            return getUrl(`api/invocations/${this.invocation}/biocompute/download`);
        }
    },
    methods: {
        submitForm(){
            const bcoString = {
                POST_create_new_object: [
                    {
                        contents: this.bco,
                        owner_group: this.form.owner_group,
                        schema: 'IEEE',
                        state: 'DRAFT',
                        table: this.form.table,
                    }
                ]};
            const headers = {
               "Authorization": "Token " + this.form.authorization,
               "Content-type": "application/json; charset=UTF-8"
            };
            axios.post(this.form.fetch, bcoString, {headers:headers})
                .then((res) => {})
                .catch((error) => {})
                .finally(() => {console.log(this.form)
            });
        }
    }
}
</script>

