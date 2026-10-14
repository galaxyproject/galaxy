<template>
    <div>
        <Alert :message="message" :variant="status" />
        <Alert v-if="viewOnly" message="Not implemented" variant="dark" />
        <Alert v-else-if="loading" message="Waiting for data" variant="info" />
        <div v-else-if="dataManagers && !dataManagers.length">
            <Alert variant="primary">
                <span class="alert-heading h-sm">None installed</span>
                You do not currently have any Data Managers installed.
            </Alert>
        </div>
        <div v-else-if="dataManagers && dataTables">
            <BContainer fluid>
                <BRow>
                    <BCol md="6">
                        <BFormGroup description="Search for strings or regular expressions">
                            <BInputGroup>
                                <BFormInput v-model="filter" placeholder="Type to Search" @keyup.esc="filter = ''" />
                                <BInputGroupAppend>
                                    <BButton :disabled="!filter" @click="filter = ''">Clear (esc)</BButton>
                                </BInputGroupAppend>
                            </BInputGroup>
                        </BFormGroup>
                    </BCol>
                </BRow>
            </BContainer>
            <BCardGroup columns>
                <BCard id="data-managers-card" no-body header="Installed Data Managers">
                    <BListGroup flush>
                        <BListGroupItem v-for="(dataManager, index) in dataManagersFiltered" :key="index">
                            <GButtonGroup vertical>
                                <GButton
                                    :id="kebabCase(dataManager['name'])"
                                    :href="dataManager['toolUrl']"
                                    target="_blank"
                                    color="blue">
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
                        </BListGroupItem>
                    </BListGroup>
                </BCard>
                <BCard no-body header="Tool Data Tables">
                    <BListGroup flush>
                        <BListGroupItem
                            v-for="(dataTable, index) in dataTablesFiltered"
                            :id="kebabCase(dataTable['name']) + '-table'"
                            :key="index"
                            :to="{ name: 'DataManagerTable', params: { name: dataTable['name'] } }"
                            :variant="dataTable['managed'] === true ? 'primary' : 'link'">
                            {{ dataTable["name"] }}
                            <BBadge v-if="dataTable['managed'] === true" variant="primary" pill
                                ><span class="fa fa-exchange"
                            /></BBadge>
                        </BListGroupItem>
                    </BListGroup>
                </BCard>
            </BCardGroup>
        </div>
    </div>
</template>

<script>
import axios from "axios";
import {
    BBadge,
    BButton,
    BCard,
    BCardGroup,
    BCol,
    BContainer,
    BFormGroup,
    BFormInput,
    BInputGroup,
    BInputGroupAppend,
    BListGroup,
    BListGroupItem,
    BRow,
} from "bootstrap-vue";
import { debounce } from "lodash";

import { getAppRoot } from "@/onload/loadConfig";

import Alert from "@/components/Alert.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import GButtonGroup from "@/components/BaseComponents/GButtonGroup.vue";

export default {
    components: {
        BBadge,
        BButton,
        BCard,
        BCardGroup,
        BCol,
        BContainer,
        BFormGroup,
        BFormInput,
        BInputGroup,
        BInputGroupAppend,
        BListGroup,
        BListGroupItem,
        BRow,
        Alert,
        GButton,
        GButtonGroup,
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
