<template>
  <b-container>
    <b-row>
      <b-col>
        <h4>Current Custom Builds</h4>
      </b-col>
    </b-row>
    <b-row>
        <b-col>
          <b-table small show-empty
            class="grid"
            :items="items"
            :fields="fields">
            <template slot="action" slot-scope="row">
              <div class="ui-button-icon-plain" style="display: inline-block;">
                <div class="button" v-b-tooltip.bottom.hover
                  title="Delete build"
                  @click="deleteBuild(row.item.id, $event)">
                  <i class="icon fa fa-trash-o" />
                </div>
              </div>
            </template>
          </b-table>
        </b-col>
    </b-row>
    <template v-if="installedBuilds.length > 0">
      <b-row>
        <b-col>
          <h4>System Installed Builds</h4>
        </b-col>
      </b-row>
      <b-row>
        <b-col id="installed-builds">
          <multiselect multiple taggable disabled
            label="label"
            track-by="value"
            :searchable="false"
            :show-labels="false"
            :value="installedBuilds"
            :options="installedBuilds">
            <span slot="caret"></span>
            <template slot="tag" slot-scope="props">
              <span class="multiselect__tag">
                <span>{{ props.option.label }}</span>
              </span>
            </template>
          </multiselect>
        </b-col>
      </b-row>
    </template>
    <b-row>
      <b-col>
        <h4>Add a Custom Build</h4>
      </b-col>
    </b-row>
    <b-row>
      <b-col>
        <b-card class="ui-portlet-limited">
          <b-alert fade dismissible
            :variant="alertType"
            :show="dismissCountDown"
            @dismissed="dismissCountDown=0"
            @dismiss-count-down="countDownChanged">
            {{ alertMessage }}
          </b-alert>

          <b-form @submit.prevent="save">
            <b-form-group
              label="Name"
              description="Specify a build name, e.g. Hamster."
              label-for="name">
              <b-form-input class="ui-input" id="name" tour_id="name" v-model="form.name" required />
            </b-form-group>
            <b-form-group
              label="Key"
              description="Specify a build key, e.g. hamster_v1."
              label-for="id">
              <b-form-input class="ui-input" id="id" tour_id="id" v-model="form.id" required />
            </b-form-group>
            <b-form-group
              label="Definition"
              description="Provide the data source."
              label-for="type">
              <ui-select
                id="type"
                tour_id="type"
                :label="'text'"
                v-model="selectedDataSource"
                :options="dataSources" />
            </b-form-group>
            <div class="ui-form-section">
              <b-form-group
                v-if="selectedDataSource && selectedDataSource.value === 'fasta'"
                label="FASTA-file">
                <ui-select
                  :label="'label'"
                  :options="fastaFiles"
                  :loading="fastaFilesLoading"
                  :disabled="fastaFilesSelectDisabled"
                  v-model="selectedFastaFile" />
              </b-form-group>
              <b-form-group
                v-if="selectedDataSource && selectedDataSource.value === 'file'"
                label="Len-file">
                <b-form-file placeholder="Choose a file..." @change="readFile" />
                <b-progress animated show-progress
                  v-show="fileLoaded !== 0"
                  :value="fileLoaded"
                  :max="maxFileSize" />
                <b-form-textarea disabled
                  class="ui-textarea file-content"
                  v-show="form.file"
                  :value="form.file"/>
              </b-form-group>
              <b-form-group
                v-if="selectedDataSource && selectedDataSource.value === 'text'"
                label="Edit/Paste">
                <b-form-textarea class="ui-textarea" v-model="form.text" />
              </b-form-group>
            </div>
            <b-button
              type="submit"
              variant="primary"
              v-b-tooltip.bottom.hover
              title="Create new build">
              <i class="icon fa fa-save ui-margin-right" />Save
            </b-button>
          </b-form>
        </b-card>
      </b-col>
      <b-col>
        <b-card
          v-if="selectedDataSource && selectedDataSource.value === 'fasta'"
          class="alert-info">
          <h4>FASTA format</h4>
          <p class="card-text">This is a multi-fasta file from your current history that provides the genome sequences for each chromosome/contig in your build.</p>
          <p class="card-text">Here is a snippet from an example multi-fasta file:</p>
          <pre class="card-text">&gt;chr1
ATTATATATAAGACCACAGAGAGAATATTTTGCCCGG...

&gt;chr2
GGCGGCCGCGGCGATATAGAACTACTCATTATATATA...

...</pre>
        </b-card>
        <b-card v-else class="alert-info">
          <h4>Length Format</h4>
          <p class="card-text">The length format is two-column, separated by whitespace, of the form:</p>
          <pre class="card-text">chrom/contig   length of chrom/contig</pre>
          <p class="card-text">For example, the first few entries of <em>mm9.len</em> are as follows:</p>
          <pre class="card-text">chr1    197195432
chr2    181748087
chr3    159599783
chr4    155630120
chr5    152537259</pre>
          <p class="card-text">Trackster uses this information to populate the select box for chrom/contig, andto set the maximum basepair of the track browser. You may either upload a .len fileof this format (Len File option), or directly enter the information into the box (Len Entry option).</p>
        </b-card>
      </b-col>
    </b-row>
  </b-container>
</template>

<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import Multiselect from 'vue-multiselect';
import axios from "axios";
import Select from "../ui/Select.vue";

Vue.use(BootstrapVue);

export default {
  components: {
    "ui-select": Select,
    Multiselect
  },

  data() {
    return {
      customBuildsUrl: `${Galaxy.root}api/users/${Galaxy.user.id}/custom_builds`,
      installedBuilds: [],
      maxFileSize: 100,
      fileLoaded: 0,

      fields: [
        { key: "name", label: "Name" },
        { key: "id", label: "Key" },
        { key: "count", label: "Number of chroms/contigs" },
        { key: "action", label: "" }
      ],
      items: [],

      alertType: "info",
      alertMessage: "",
      dismissSecs: 5,
      dismissCountDown: 0,

      form: {
        id: "",
        name: "",
        file: "",
        text: ""
      },

      dataSources: [
        { value: "fasta", text: "FASTA-file from history" },
        { value: "file", text: "Len-file from disk" },
        { value: "text", text: "Len-file by copy/paste" }
      ],
      selectedDataSource: null,
      fastaFilesLoading: true,
      fastaFilesSelectDisabled: true,
      fastaFiles: [],
      selectedFastaFile: null
    };
  },

  computed: {
    lengthType: function () {
      return this.selectedDataSource ? this.selectedDataSource.value : "";
    },

    lengthValue: function () {
      let value = "";

      if (this.lengthType === "fasta") {
        value = this.selectedFastaFile ? this.selectedFastaFile.value : "";
      } else if (this.lengthType === "file") {
        value = this.form.file;
      } else if (this.lengthType === "text") {
        value = this.form.text;
      }

      return value;
    }
  },

  created() {
    this.loadCustomBuilds();

    Galaxy.currHistoryPanel.model.once("change", model => {
      if (model.id) {
        this.loadCustomBuildsMetadata(model.id);
      } else {
        this.fastaFilesLoading = false;
      }
    });
  },

  methods: {
    loadCustomBuilds () {
      axios
        .get(this.customBuildsUrl)
        .then(response => {
          this.items = response.data;
        })
        .catch(error => {
          console.log(error.response);
        });
    },

    loadCustomBuildsMetadata (historyId) {
      axios
        .get(`${Galaxy.root}api/histories/${historyId}/custom_builds_metadata`)
        .then(response => {
          const fastaHdas = response.data.fasta_hdas;

          if (fastaHdas.length > 0) {
            this.fastaFiles = fastaHdas;
            this.fastaFilesSelectDisabled = false;
          }

          this.fastaFilesLoading = false;
          this.installedBuilds = response.data.installed_builds;
        })
        .catch(error => {
          console.log(error.response);
          this.fastaFilesLoading = false;
        })
    },

    save (event) {
      const data = {
        id: this.form.id,
        name: this.form.name,
        "len|type": this.lengthType,
        "len|value": this.lengthValue
      };

      if (!data.id.trim() || !data.name.trim() || !data["len|value"].trim()) {
        this.showAlert("danger", "All inputs are required.");
        return false;
      }

      axios
        .put(`${this.customBuildsUrl}/${data.id}`, data)
        .then(response => {
          if (response.data.message) {
            this.showAlert("warning", response.data.message);
          } else {
            this.showAlert("success", "Successfully added a new custom build.");
          }
          this.loadCustomBuilds();
        })
        .catch(error => {
          const message = error.response.data.err_msg;
          this.showAlert("danger", message || "Failed to create custom build.");
          console.log(error.response);
        });
    },

    deleteBuild (id) {
      axios
        .delete(`${this.customBuildsUrl}/${id}`)
        .then(response => {
          this.items = this.items.filter(i => i.id !== id);
        })
        .catch(error => {
          const message = error.response.data.err_msg;
          this.showAlert("danger", message || "Failed to delete custom build.");
          console.log(error.response);
        });
    },

    readFile (event) {
      const file = event.target.files && event.target.files[0];

      if (file) {
        const reader = new FileReader();

        reader.onprogress = e => {
          if (e.lengthComputable) {
            this.fileLoaded = Math.round(e.loaded / e.total) * 100;
          }
        };

        reader.onload = () => {
          this.fileLoaded = 0;
          this.form.file = reader.result;
        };

        reader.readAsText(file);
      }
    },

    showAlert (type, message) {
      this.alertType = type;
      this.alertMessage = message;
      this.dismissCountDown = this.dismissSecs;
    },

    countDownChanged (dismissCountDown) {
      this.dismissCountDown = dismissCountDown;
    }
  }
}
</script>

<style>
  .col {
    padding-left: 5px;
    padding-right: 5px;
  }

  .card.ui-portlet-limited .card-body {
    padding: 15px;
  }

  .form-group {
    margin-bottom: .5rem;
  }

  .col-form-label {
    font-weight: bold;
  }

  .custom-file {
    z-index: 0;
  }

  .progress,
  .file-content {
    margin-top: 5px;
  }

  #installed-builds {
    margin-bottom: 15px;
  }

  #installed-builds .multiselect--disabled {
    opacity: 1;
  }

  #installed-builds .multiselect__tags {
    font-size: 12px;
    padding-right: 0;
  }

  #installed-builds .multiselect__tag {
    background: #9e9e9e;
    margin: 5px 5px 0;
    padding: 4px 10px;
  }
</style>
