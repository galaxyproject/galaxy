<template>
  <b-container>
    <b-row>
      <b-col>
        <h4>Current Custom Builds</h4>
      </b-col>
    </b-row>
    <b-row>
        <b-col>
          <b-table
            small
            show-empty
            class="grid"
            :items="items"
            :fields="fields"
            :sort-by="sortBy"
          >
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
    <b-row>
      <b-col>
        <h4>Add a Custom Build</h4>
      </b-col>
    </b-row>
    <b-row>
      <b-col>
        <b-card class="ui-portlet-limited">
          <b-alert
            fade
            dismissible
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
            </b-form-group><!-- ./name -->
            <b-form-group
              label="Key"
              description="Specify a build key, e.g. hamster_v1."
              label-for="id">
              <b-form-input class="ui-input" id="id" tour_id="id" v-model="form.id" required />
            </b-form-group><!-- ./key -->
            <b-form-group
              label="Definition"
              description="Provide the data source."
              label-for="type">
              <ui-select
                id="type"
                tour_id="type"
                :label="'text'"
                v-model="selected"
                :options="options" />
            </b-form-group><!-- ./type -->
            <div class="ui-form-section">
              <b-form-group v-if="selected.value === 'file'" label="Len-file">
                <b-form-file placeholder="Choose a file..." @change="readFile" />
                <b-progress animated show-progress
                  v-show="fileLoaded !== 0"
                  :value="fileLoaded"
                  :max="maxFileSize" />
                <b-form-textarea disabled
                  v-show="form.value"
                  class="ui-textarea file-content"
                  :value="form.value"/>
              </b-form-group>
              <b-form-group v-if="selected.value === 'text'" label="Edit/Paste">
                <b-form-textarea class="ui-textarea" v-model="form.text" />
              </b-form-group>
            </div><!-- ./ui-form-section -->
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
        <b-card v-if="selected.value === 'fasta'" class="alert-info">
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
import axios from "axios";
import BootstrapVue from "bootstrap-vue";
import Select from "../ui/Select.vue";

export default {
  data() {
    return {
      url: `${Galaxy.root}api/users/${Galaxy.user.id}/custom_builds`,
      alertType: "info",
      alertMessage: "",
      dismissSecs: 3,
      dismissCountDown: 0,
      maxFileSize: 100,
      fileLoaded: 0,
      items: [],
      fields: [
        { key: "name", label: "Name" },
        { key: "id", label: "Key" },
        { key: "count", label: "Number of chroms/contigs" },
        { key: "action", label: "" }
      ],
      sortBy: 'name',
      options: [
        { value: "fasta", text: "FASTA-file from history" },
        { value: "file", text: "Len-file from disk" },
        { value: "text", text: "Len-file by copy/paste" }
      ],
      selected: null,
      form: {
        name: "",
        id: "",
        text: "",
        value: ""
      }
    };
  },

  components: {
    'ui-select': Select
  },

  created() {
    this.loadData();
    this.selected = this.options[0];
  },

  methods: {
    loadData () {
      axios
        .get(this.url)
        .then(response => {
          this.items = response.data;
        })
        .catch(error => {
          console.log(error.response);
        });
    },

    save (event) {
      if (!this.form.id.trim() || !this.form.name.trim()) {
        this.showAlert("danger", "All inputs are required.");
        return false;
      }

      const type = this.selected.value;
      const data = {
        id: this.form.id,
        name: this.form.name,
        "len|type": type
      };

      if (type === "file") {
        data["len|value"] = data.value;
      } else if (type === "text") {
        data["len|value"] = data.text;
      }

      axios
        .put(`${this.url}/${data.id}`, data)
        .then(response => {
          if (response.data.message) {
            this.showAlert("warning", response.data.message);
          } else {
            this.showAlert("success", "Successfully added a new custom build.");
          }
          this.loadData();
        })
        .catch(error => {
          const message = error.response.data.err_msg;
          this.showAlert("danger", message || "Failed to create custom build.");
          console.log(error.response);
        });
    },

    deleteBuild (id) {
      axios
        .delete(`${this.url}/${id}`)
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
          this.form.value = reader.result;
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
    padding: 10px;
  }

  .form-group {
    margin-bottom: .5rem;
  }

  .col-form-label {
    font-weight: bold;
  }

  .custom-select {
    background: none;
    border: 1px solid #aaa;
  }

  .custom-select.mb-3 {
    margin-bottom: 0 !important;
  }

  .progress,
  .file-content {
    margin-top: 5px;
  }
</style>
