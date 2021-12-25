<template>
    <b-modal
        modal-class="selection-dialog-modal"
        v-if="modalShow"
        visible
        :static="modalStatic"
        @hide="hideModal">
        <template v-slot:modal-header>
            <slot name="search"> </slot>
        </template>
        <b-alert v-if="showFtpHelper" variant="info" show>
          This Galaxy server allows you to upload files via FTP. To upload some files, log in to the FTP server at
          <strong>{{ ftpUploadSite }}</strong> using your Galaxy credentials.
          For help visit the <a href="https://galaxyproject.org/ftp-upload/" target="_blank">tutorial</a>.
          <span v-if="oidcEnabled"><br/>If you are signed-in to Galaxy using a third-party identity and you <strong>do not have a Galaxy password</strong> please use the reset password option in the login form with your email to create a password for your account.</span>
        </b-alert>
        <b-alert v-if="errorMessage" variant="danger" show v-html="errorMessage" />
        <div v-else>
            <slot name="options" v-if="optionsShow"> </slot>
            <div v-else><span class="fa fa-spinner fa-spin" /> <span>Please wait...</span></div>
        </div>
        <template v-slot:modal-footer>
            <div v-if="!errorMessage" class="w-100">
                <slot name="buttons"> </slot>
                <b-btn size="sm" class="float-right selection-dialog-modal-cancel" @click="hideModal"> Cancel </b-btn>
            </div>
            <div v-else class="w-100">
              <b-btn id="back-btn" size="sm" class="float-left" v-if="undoShow" @click="backFunc()">
                <font-awesome-icon :icon="['fas', 'caret-left']"/>
                Back
              </b-btn>
              <b-btn size="sm" class="float-right" variant="primary" id="close-btn" @click="hideModal">
                Close
              </b-btn>
            </div>
        </template>
    </b-modal>
</template>

<script>
import Vue from "vue";
import { getGalaxyInstance } from "app";
import BootstrapVue from "bootstrap-vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

Vue.use(BootstrapVue);

export default {
    props: {
        multiple: {
            type: Boolean,
            default: false,
        },
        modalStatic: {
            type: Boolean,
            default: false,
        },
        errorMessage: {
            type: String,
            default: null,
        },
        optionsShow: {
            type: Boolean,
            default: false,
        },
        modalShow: {
            type: Boolean,
            default: true,
        },
        hideModal: {
            type: Function,
            required: true,
        },
        backFunc: {
          type: Function,
          required: true,
        },
        undoShow: {
          type: Boolean,
          required: true,
        },
        showFtpHelper: {
          type: Boolean,
          required: false,
        },
    },
    components: {
      FontAwesomeIcon,
    },
    data() {
      return {
        ftpUploadSite: getGalaxyInstance().config.ftp_upload_site,
        oidcEnabled: getGalaxyInstance().config.enable_oidc,
      }
    },
};
</script>

<style>
.selection-dialog-modal .modal-body {
    max-height: 50vh;
    height: 50vh;
    overflow-y: auto;
}
</style>
