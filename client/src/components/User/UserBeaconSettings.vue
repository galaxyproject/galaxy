<template>
  <b-row class="ml-3 mb-1">
    <i class="pref-icon pt-1 fa fa-lg fa-broadcast-tower" />
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

        <h3>About Beacon</h3>
        <p>
          A beacon is a web service that shares information about the occurrence of genetic variants.
          A beacon answers questions of the form "Do you have information about the following mutation?" and responds with one of "Yes" or "No".

          <b-link href="https://beacon-network.org/#/about">Learn more</b-link>
        </p>


        <b-alert show>Apart from the "Yes/No" response <span class="bold">no data will be shared</span></b-alert>



        <h3>Participate</h3>
        There is a beacon instance set up on this galaxy instance. To contribute variant information follow the steps below.

        <div class="actual-settings">
          <h4>Opt-in to variant sharing</h4>
          <div class="setting-container">
            <div class="setting-text">
              <p v-if="!enabled"> you are currently not opted in</p>
              <p v-if="enabled"> you have already opted in and you can share data</p>
            </div>
            <div class="setting-buttons">
              <b-button v-if="!enabled" @click="optIn" variant="success">Opt-in</b-button>
              <b-button v-if="enabled" @click="optOut" variant="danger">Opt-out</b-button>
            </div>
          </div>
        </div>

      </b-modal>
    </div>
  </b-row>
</template>

<script>
import axios from "axios";
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import { userLogoutClient } from "layout/menu";
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
    };
  },
  computed: {
    showDeleteError() {
      return this.deleteError !== "";
    },
  },
  methods: {
    async optIn() {
      try {
        await axios.post(`${this.root}api/users/${this.userId}/beacon`, {"enabled": true}).then(
            response => {
              // TODO check response
              this.loadSettings();
            }
        );
      } catch (e) {
        console.log(e);
      }
    },
    async optOut() {
      try {
        await axios.post(`${this.root}api/users/${this.userId}/beacon`, {"enabled": false}).then(
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
    checkFormValidity() {
      const valid = this.$refs.form.checkValidity();
      this.nameState = valid;
      return valid;
    },
    resetModal() {
      this.name = "";
      this.nameState = null;
    },
    handleOk(bvModalEvt) {
      // Prevent modal from closing
      bvModalEvt.preventDefault();
      // Trigger submit handler
      this.handleSubmit();
    },
    async handleSubmit() {
      if (!this.checkFormValidity()) {
        return false;
      }
      if (this.email === this.name) {
        this.nameState = true;
        try {
          await axios.delete(`${this.root}api/users/${this.userId}`);
        } catch (e) {
          if (e.response.status === 403) {
            this.deleteError =
                "User deletion must be configured on this instance in order to allow user self-deletion.  Please contact an administrator for assistance.";
            return false;
          }
        }
        userLogoutClient();
      } else {
        this.nameState = false;
        return false;
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

.setting-container {
  display: flex;
  flex-flow: row;
  justify-content: space-between;
  align-items: center;
}

.setting-container div.setting-text {
  width: 100%;
  margin-bottom: 32px;
}

.setting-container div.setting-buttons {
  display: flex;
  width: 10rem;
}

.setting-container div.setting-buttons button {
  margin-left: auto;
  margin-right: 0;
}

.actual-settings {
  padding: 8px 16px;
  margin-top: 32px;
  margin-bottom: 32px;
  border: 1px solid #bdc6d0;
  border-radius: 5px;
  background-color: rgba(0, 0, 0, 0.04);
}
</style>