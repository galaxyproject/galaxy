<template>
    <div v-if="editLicense">
        <loading-span v-if="licensesLoading" message="Loading licenses..." />
        <b-form-select v-else v-model="license" :options="licenseOptions"></b-form-select>
        <License v-if="currentLicenseInfo" :license-id="license" :input-license-info="currentLicenseInfo">
            <template v-slot:buttons>
                <font-awesome-icon v-b-tooltip.hover title="Save License" icon="save" @click="onSave" />
                <font-awesome-icon v-b-tooltip.hover title="Cancel Edit" icon="times" @click="disableEdit" />
            </template>
        </License>
        <div v-else>
            <a href="#" @click.prevent="onSave">Save without license</a> or
            <a href="#" @click.prevent="editLicense = false">cancel edit.</a>
        </div>
    </div>
    <div v-else-if="license">
        <License :license-id="license">
            <template v-slot:buttons>
                <font-awesome-icon v-b-tooltip.hover title="Edit License" icon="edit" @click="editLicense = true" />
            </template>
        </License>
    </div>
    <div v-else>
        <i><a href="#" @click.prevent="editLicense = true">Specify a license for this workflow.</a></i>
    </div>
</template>

<script>
import { getAppRoot } from "onload/loadConfig";
import axios from "axios";
import LoadingSpan from "components/LoadingSpan";
import License from "./License";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";

import { faSave, faTimes, faEdit } from "@fortawesome/free-solid-svg-icons";

import Vue from "vue";
import BootstrapVue from "bootstrap-vue";

library.add(faSave);
library.add(faTimes);
library.add(faEdit);

Vue.use(BootstrapVue);

export default {
    components: { License, LoadingSpan, FontAwesomeIcon },
    props: {
        inputLicense: {
            type: String,
        },
    },
    data() {
        return {
            license: this.inputLicense || null,
            licensesLoading: false,
            licenses: [],
            editLicense: false,
        };
    },
    computed: {
        currentLicenseInfo() {
            for (const license of this.licenses) {
                if (license.licenseId == this.license) {
                    return license;
                }
            }
            return null;
        },
        licenseOptions() {
            const options = [];
            options.push({
                value: null,
                text: "*Do not specify a license.*",
            });
            for (const license of this.licenses) {
                if (license.licenseId == this.license || license.recommended) {
                    options.push({
                        value: license.licenseId,
                        text: license.name,
                    });
                }
            }
            return options;
        },
    },
    watch: {
        inputLicense() {
            this.license = this.inputLicense;
        },
    },
    mounted() {
        const url = `${getAppRoot()}api/licenses`;
        axios
            .get(url)
            .then((response) => response.data)
            .then((data) => {
                this.licenses = data;
                this.licensesLoading = false;
            })
            .catch((e) => {
                console.error(e);
            });
    },
    methods: {
        onSave() {
            this.onLicense(this.license);
            this.disableEdit();
        },
        disableEdit() {
            this.editLicense = false;
        },
        onLicense(license) {
            this.$emit("onLicense", license);
        },
    },
};
</script>
