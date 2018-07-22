<template>
  <div>
    <b-breadcrumb :items="breadcrumbItems" />
    <Alert :message="message" :variant="status" />
    <Alert v-if="viewOnly" message="Not implemented" variant="dark" />
    <Alert v-else-if="!jobs.length" message="There are no jobs for this data manager." variant="primary" />
    <div v-else>
      <b-container fluid class="mb-3">
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
        <b-row>
          <b-col>
            <b-button :pressed.sync="showCommandLine" variant="outline-secondary">
              {{ showCommandLine ? 'Hide' : 'Show'}} Command Line
            </b-button>
          </b-col>
        </b-row>
      </b-container>
      <b-table :fields="tableFields" :items="tableItems" :filter="filter" hover responsive striped>
        <template slot="actions" slot-scope="row">
          <!-- we use @click.stop here to prevent emitting of a 'row-clicked' event  -->
          <b-button-group>
            <b-button :href="jobs[row.index]['runUrl']" v-b-tooltip.hover title="Rerun">
              <span class="fa fa-refresh" />
            </b-button>
            <b-button v-b-tooltip.hover title="View Info" :href="jobs[row.index]['infoUrl']" target="galaxy_main">
              <span class="fa fa-info-circle" />
            </b-button>
            <b-button v-if="!showCommandLine" @click.stop="onInfoButtonClick(row)" :pressed.sync="row.detailsShowing">
              {{ row.detailsShowing ? 'Hide' : 'Show'}} Command Line
            </b-button>
          </b-button-group>
        </template>
        <template slot="row-details" slot-scope="row">
          <b-card>
            <b-container fluid>
              <b-row>
                <b-col cols="auto">
                  Command line:
                </b-col>
                <b-col>
                  <pre class="code"><code class="command-line">{{ row.item.commandLine }}</code></pre>
                </b-col>
              </b-row>
              <b-button class="mt-3" @click="row.toggleDetails">Hide Command Line</b-button>
            </b-container>
          </b-card>
        </template>
      </b-table>
    </div>
  </div>
</template>

<script>
import axios from "axios";
import Alert from "components/Alert.vue";

export default {
    components: {
        Alert
    },
    props: {
        id: {
            type: String,
            required: true
        }
    },
    data() {
        return {
            dataManager: [],
            jobs: [],
            fields: [
                { key: "id", label: "Job ID", sortable: true },
                { key: "user" },
                { key: "updateTime", label: "Last Update", sortable: true },
                { key: "state" },
                { key: "actions" },
                { key: "jobRunnerName", label: "Job Runner" },
                { key: "jobRunnerExternalId", label: "PID/Cluster ID", sortable: true }
            ],
            showCommandLine: false,
            filter: "",
            viewOnly: false,
            message: "",
            status: ""
        };
    },
    computed: {
        breadcrumbItems() {
            return [
                {
                    text: "Data Managers",
                    to: "/"
                },
                {
                    text: "Jobs for " + this.dataManager["name"] + " (" + this.dataManager["description"] + ") ",
                    active: true
                }
            ];
        },
        tableFields() {
            let tableFields = this.fields.slice(0);
            if (this.showCommandLine) {
                tableFields.splice(5, 0, {
                    key: "commandLine",
                    tdClass: "command-line"
                });
            }
            return tableFields;
        },
        tableItems() {
            let tableItems = this.jobs;
            for (const item of tableItems) {
                item["updateTime"] = item["updateTime"].replace("T", "\n");

                switch (item["state"]) {
                    case "ok":
                        item["_cellVariants"] = { state: "success" };
                        break;
                    case "error":
                        item["_cellVariants"] = { state: "danger" };
                        break;
                    case "deleted":
                        item["_cellVariants"] = { state: "warning" };
                        break;
                    case "running":
                        item["_cellVariants"] = { state: "info" };
                        break;
                    case "waiting":
                    case "queued":
                        item["_cellVariants"] = { state: "primary" };
                        break;
                    case "paused":
                        item["_cellVariants"] = { state: "secondary" };
                        break;
                }
            }
            return tableItems;
        }
    },
    methods: {
        onInfoButtonClick(row) {
            row.toggleDetails();
            this.$refs["popover" + row.index].$emit("close");
        }
    },
    created() {
        axios
            .get(`${Galaxy.root}data_manager/jobs_list?id=${this.id}`)
            .then(response => {
                this.dataManager = response.data.dataManager;
                this.jobs = response.data.jobs;
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

<style>
pre.code {
    background: black;
    color: white;
    padding: 1em;
}
.command-line {
    white-space: pre-wrap;
    word-break: break-word;
}
</style>
