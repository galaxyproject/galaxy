<template>
    <div>
        <Alert :message="message" :variant="status" />
        <Alert v-if="viewOnly" message="Not implemented" variant="dark" />
        <div v-else-if="!dataManagers.length">
            <Alert variant="primary">
                <h4 class="alert-heading">None installed</h4>
                You do not currently have any Data Managers installed
            </Alert>
            <Alert variant="info">
                Data Managers can be installed from a
                <ToolShedButton />
            </Alert>
        </div>
        <div v-else>
            <Alert variant="secondary" dismissible>
                Choose your data managing option from below. You may install additional Data Managers from a
                <ToolShedButton />
            </Alert>
            <b-container fluid>
                <b-row>
                    <b-col md="6">
                        <b-form-group description="Search for strings or regular expressions">
                            <b-input-group>
                                <b-form-input v-model="filter" placeholder="Type to Search" @keyup.esc.native="filter = ''" />
                                <b-input-group-append>
                                    <b-btn :disabled="!filter" @click="filter = ''">Clear (esc)</b-btn>
                                </b-input-group-append>
                            </b-input-group>
                        </b-form-group>
                    </b-col>
                </b-row>
            </b-container>
            <b-card-group columns>
                <b-card no-body header="<h4>Data Managers</h4>" id="data-managers-card">
                    <b-list-group flush>
                        <b-list-group-item v-for="(dataManager, index) in dataManagersFiltered" :key="index">
                            <b-button-group vertical>
                                <b-button :href="dataManager['toolUrl']" target="_blank" variant="primary" :id="kebabCase(dataManager['name'])">
                                    <div>{{ dataManager['name'] }}</div>
                                    <div v-if="dataManager['description']">
                                        <i>{{ dataManager['description'] }}</i>
                                    </div>
                                </b-button>
                                <b-button :href="dataManager['jobsUrl']" target="galaxy_main" :id="kebabCase(dataManager['name']) + '-jobs'">
                                    Jobs
                                </b-button>
                            </b-button-group>
                        </b-list-group-item>
                    </b-list-group>
                </b-card>
                <b-card no-body header="<h4>View Tool Data Table Entries</h4>">
                    <b-list-group flush>
                        <b-list-group-item v-for="(dataTable, index) in dataTablesFiltered" :key="index" :href="dataTable['url']" target="galaxy_main" :variant="dataTable['managed'] === true ? 'primary' : ''">
                            {{ dataTable['name'] }}
                            <span v-if="dataTable['managed'] === true" class="fa fa-exchange" />
                        </b-list-group-item>
                    </b-list-group>
                </b-card>
            </b-card-group>
        </div>
    </div>
</template>

<script>
import axios from "axios";
import Alert from "components/Alert.vue";

var ToolShedButton = {
    template: `
  <b-link href="/admin_toolshed/browse_tool_sheds"
          target="galaxy_main"
          class="alert-link">
  ToolShed
  </b-link>`
};

export default {
    components: {
        Alert,
        ToolShedButton
    },
    data() {
        return {
            dataManagers: [],
            dataTables: [],
            filter: "",
            viewOnly: false,
            message: "",
            status: ""
        };
    },
    computed: {
        dataManagersFiltered() {
            return this.dataManagers.filter(d => d["name"].match(new RegExp(this.filter, "i")));
        },
        dataTablesFiltered() {
            return this.dataTables.filter(d => d["name"].match(new RegExp(this.filter, "i")));
        }
    },
    methods: {
        kebabCase(s) {
            return s.toLowerCase().replace(/ /g, "-");
        }
    },
    created() {
        axios
            .get(`${Galaxy.root}data_manager/data_managers_list`)
            .then(response => {
                this.dataManagers = response.data.dataManagers;
                this.dataTables = response.data.dataTables;
                this.viewOnly = response.data.viewOnly;
                this.message = response.data.message;
                this.status = response.data.status;
            })
            .catch(error => {
                console.error(error);
            });
    }
};
</script>
