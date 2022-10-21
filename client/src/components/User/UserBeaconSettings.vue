<template>
  <b-row class="ml-3 mb-1">
    <i class="pref-icon pt-1 fa fa-lg fa-broadcast-tower"/>
    <div class="pref-content pr-1">
      <a id="beacon-settings" href="javascript:void(0)"
      ><b v-b-modal.modal-beacon v-localize>Manage Beacon</b></a
      >
      <div v-localize class="form-text text-muted">Contribute variants to Beacon</div>
      <b-modal
          size="xl"
          id="modal-beacon"
          ref="modal"
          ok-only
          title="Manage Beacon"
          title-tag="h1"
          @show="loadSettings">

        <!-- Explanation text-->
        <p>
          This setting will enable the possibility to share your Variants (in VCF (vcf) or compressed VCF (vcf_gz))
          with the entire community in a secure way without sharing the entire file or Galaxy history. This is possible
          by utilizing the <a href="https://beacon-project.io">Global Alliance for Genomics & Health Beacon Project</a>.
          <br>
          <br>
          We turn Galaxy into a Beacon server and offer your variants anonymously via the Beacon Network. All shared
          Variants will be merged to a single dataset. If someone searches in the Beacon Network for a specific variant
          that is in one of your datasets our Galaxy server will return
          <span class="cursive">“Yes, we have seen such a variant”</span>. Nothing more.
          <br>
          <br>
          The user has the possibility to contact the Admin of the Galaxy server and we will in turn contact
          you and ask if you want to contact this user and negotiate a potential data access.
          Sharing is essential in Galaxy, secure sharing of sensitive data is now possible using Beacon.
        </p>


        <b-alert v-if="enabled" show>
          <div class="flex-row space-between">
            <div class="no-shrink">
              Beacon sharing is <span class="bold">enabled</span> for your profile
            </div>
            <div class="fill"></div>
            <div class="no-shrink">
              <b-button @click="optOut" variant="danger">Disable</b-button>
            </div>
          </div>
        </b-alert>


        <!-- Setting to show when beacon is disabled -->
        <b-alert v-if="!enabled" show>
          <div class="flex-row space-between">
            <div class="no-shrink">
              Beacon sharing is currently <span class="bold">disabled</span> - no data will be shared
            </div>
            <div class="fill"></div>
            <div>
              <b-button @click="optIn" variant="success">Enable</b-button>
            </div>
          </div>
        </b-alert>

        <div v-if="enabled">
          <p>
            If you this setting you can share data by copying VCF/VCF.gz files to a history called
            <span class="cursive">{{ beaconHistoryName }}</span>. The Beacon database is rebuild every day, this means
            if
            you disable the option here, of if we remove the history, or data in the history, the variants will
            disappear
            from the Beacon in the next 24h.
          </p>
        </div>


        <!-- Detailed information about the beacon history -->
        <div v-if="enabled" class="gray-box">
          <!-- Case: History does not exist-->
          <div v-if="!beaconHistory.id" class="flex-row">
            <div class="no-shrink">
              No beacon history found
            </div>
            <div class="fill"></div>
            <div class="no-shrink">
              <b-button @click="createBeaconHistory">Create Beacon History</b-button>
            </div>
          </div>

          <!-- Case: History exists -->
          <div v-if="beaconHistory.id" class="flex-row">
            <div class="no-shrink">
              Variant files are searched in your beacon history
            </div>
            <div class="fill"></div>
            <div class="no-shrink">
              <b-button @click="switchHistory(beaconHistory.id)">Switch to History</b-button>
            </div>
          </div>
        </div>

        <div v-if="enabled">
          <p>
            Datasets must fulfill the following conditions in order to be processed
          </p>
          <ul>
            <li>must be VCF or VCF.bzip format</li>
            <li>must have a human reference assigned to it (e.g. hg19)</li>
            <li>must define at least one sample</li>
          </ul>
        </div>
      </b-modal>
    </div>
  </b-row>
</template>

<script>
import store from "store"
import axios from "axios";
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";

Vue.use(BootstrapVue);

export default {
  props: {
    root: {
      type: String,
      required: true,
    },
    userId: {
      type: String,
      required: true,
    },
  },
  data() {
    return {
      enabled: false,
      beaconHistoryName: "___BEACON_PICKUP___",
      beaconHistory: {}
    };
  },
  created() {
    this.getBeaconHistory();
  },
  methods: {
    switchHistory: async function (historyId) {
      await store.dispatch("history/setCurrentHistory", historyId);
    },
    getBeaconHistory: function () {
      axios
          .get(this.root + "api/histories?q=name&qv=" + this.beaconHistoryName)
          .then((response) => {
            if (response.data.length > 0) {
              // always select first match
              this.beaconHistory = response.data[0];

            }
          })
          .catch((error) => {
            console.log(error.response)
          });
    },
    createBeaconHistory() {
      const annotation = "Variant files will be collected from this history if beacon sharing is activated"
      axios
          .post(this.root + "api/histories", {name: this.beaconHistoryName})
          .then((response) => {
            this.beaconHistory = response.data
            axios.put(`${this.root}api/histories/${this.beaconHistory.id}`, {"annotation": annotation});
          })
          .catch((error) => {
            this.errorMessages.push(error.response.data.err_msg), console.log(error.response)
          });
    },
    optIn() {
      try {
        axios.post(`${this.root}api/users/${this.userId}/beacon`, {"enabled": true}).then(
            response => {
              // TODO check response
              this.loadSettings();
              if (!this.beaconHistory.id) {
                this.createBeaconHistory()
              }
            }
        );
      } catch (e) {
        console.log(e);
      }
    },
    optOut() {
      try {
        axios.post(`${this.root}api/users/${this.userId}/beacon`, {"enabled": false}).then(
            response => {
              // TODO check response
              this.loadSettings();
            }
        );
      } catch (e) {
        console.log(e);
      }
    },
    async loadSettings() {
      try {
        await axios.get(`${this.root}api/users/${this.userId}/beacon`).then(
            response => {
              this.enabled = response.data.enabled == 1;
            }
        );
      } catch (e) {
        console.log(e);
      }
    },
  },
};
</script>

<style scoped>
span.bold {
  font-weight: bold;
}

.pref-icon {
  width: 3rem;
}

.gray-box {
  padding: 8px 16px;
  margin-top: 32px;
  margin-bottom: 32px;
  border: 1px solid #bdc6d0;
  border-radius: 5px;
  background-color: rgba(0, 0, 0, 0.04);
}

.flex-row {
  display: flex;
  flex-flow: row;
}

.space-between {
  justify-content: space-between;
  align-items: center;
}

.cursive {
  font-style: italic;
}

.bold {
  font-weight: bolder;
}

.fill {
  width: 100%;
}

.no-shrink {
  flex-shrink: 0;
}
</style>