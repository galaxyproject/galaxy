<template>
    <div>
        <GAlert :message="message" :variant="status" />
        <GAlert v-if="viewOnly" message="Not implemented" variant="dark" />
        <GAlert v-else-if="loading" message="Waiting for data" variant="info" />
        <div v-else-if="dataManagers && !dataManagers.length">
            <GAlert variant="primary">
                <span class="alert-heading h-sm">None installed</span>
                You do not currently have any Data Managers installed.
            </GAlert>
        </div>
        <div v-else-if="dataManagers && dataTables">
            <b-container fluid>
                <GRow>
                    <GCol md="6">
                        <b-form-group description="Search for strings or regular expressions">
                            <GInputGroup>
                                <GInput v-model="filter" placeholder="Type to Search" @keyup.esc.native="filter = ''" />
                                <GInputGroupAppend>
                                    <GButton :disabled="!filter" @click="filter = ''">Clear (esc)</GButton>
                                </GInputGroupAppend>
                            </GInputGroup>
                        </b-form-group>
                    </GCol>
                </GRow>
            </b-container>
            <GCardGroup columns>
                <b-card id="data-managers-card" no-body header="Installed Data Managers">
                    <b-list-group flush>
                        <b-list-group-item v-for="(dataManager, index) in dataManagersFiltered" :key="index">
                            <GButtonGroup vertical>
                                <GButton
                                    :id="kebabCase(dataManager['name'])"
                                    :href="dataManager['toolUrl']"
                                    target="_blank"
                                    variant="primary">
                                    <div>{{ dataManager["name"] }}</div>
                                    <div v-if="dataManager['description']">
                                        <i>{{ dataManager["description"] }}</i>
                                    </div>
                                </GButton>
                                <GButton
                                    :id="kebabCase(dataManager['name']) + '-jobs'"
                                    :to="{
                                        name: 'DataManagerJobs',
                                        params: { id: encodeURIComponent(dataManager['id']) },
                                    }">
                                    Jobs
                                </GButton>
                            </GButtonGroup>
                        </b-list-group-item>
                    </b-list-group>
                </b-card>
                <b-card no-body header="Tool Data Tables">
                    <b-list-group flush>
                        <b-list-group-item
                            v-for="(dataTable, index) in dataTablesFiltered"
                            :id="kebabCase(dataTable['name']) + '-table'"
                            :key="index"
                            :to="{ name: 'DataManagerTable', params: { name: dataTable['name'] } }"
                            :variant="dataTable['managed'] === true ? 'primary' : 'link'">
                            {{ dataTable["name"] }}
                            <b-badge v-if="dataTable['managed'] === true" variant="primary" pill
                                ><span class="fa fa-exchange"
                            /></b-badge>
                        </b-list-group-item>
                    </b-list-group>
                </b-card>
            </GCardGroup>
        </div>
    </div>
</template>

<script>
import axios from "axios";
import { getAppRoot } from "onload/loadConfig";
import { debounce } from "underscore";

import GAlert from "@/component-library/GAlert.vue";
import GButton from "@/component-library/GButton.vue";
import GButtonGroup from "@/component-library/GButtonGroup.vue";
import GCardGroup from "@/component-library/GCardGroup.vue";
import GCol from "@/component-library/GCol.vue";
import GInput from "@/component-library/GInput.vue";
import GInputGroup from "@/component-library/GInputGroup.vue";
import GInputGroupAppend from "@/component-library/GInputGroupAppend.vue";
import GRow from "@/component-library/GRow.vue";

export default {
    components: {
        GAlert,
        GButton,
        GButtonGroup,
        GInput,
        GCardGroup,
        GRow,
        GCol,
        GInputGroup,
        GInputGroupAppend,
    },
    beforeRouteEnter(to, from, next) {
        console.log("beforeRouteEnter");
        next((vm) => vm.debouncedLoad());
    },
    props: {
        debouncePeriod: { type: Number, required: false, default: 100 },
    },
    data() {
        return {
            dataManagers: [],
            dataTables: [],
            filter: "",
            viewOnly: false,
            message: "",
            status: "",
            loading: false,
        };
    },
    computed: {
        dataManagersFiltered() {
            return this.dataManagers.filter((d) => d["name"].match(new RegExp(this.filter, "i")));
        },
        dataTablesFiltered() {
            return this.dataTables.filter((d) => d["name"].match(new RegExp(this.filter, "i")));
        },
    },
    created() {
        console.log("created");
        this.debouncedLoad = debounce(this.load, this.debouncePeriod);
        this.debouncedLoad();
    },
    methods: {
        kebabCase(s) {
            return s.toLowerCase().replace(/ /g, "-");
        },
        load() {
            this.loading = true;
            axios
                .get(`${getAppRoot()}data_manager/data_managers_list`)
                .then((response) => {
                    console.log("response", response);
                    this.dataManagers = response.data.dataManagers;
                    this.dataTables = response.data.dataTables;
                    this.viewOnly = response.data.viewOnly;
                    this.message = response.data.message;
                    this.status = response.data.status;
                })
                .catch((error) => {
                    console.error(error);
                })
                .finally(() => {
                    this.loading = false;
                });
        },
    },
};
</script>
