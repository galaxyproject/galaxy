<template>
    <div v-if="editLicense">
        <LoadingSpan v-if="licensesLoading" message="Loading licenses..." />
        <b-form-select
            v-else
            v-model="license"
            data-description="license select"
            :options="licenseOptions"></b-form-select>
        <License v-if="currentLicenseInfo" :license-id="license" :input-license-info="currentLicenseInfo">
            <template v-slot:buttons>
                <span v-b-tooltip.hover title="Save License"
                    ><FontAwesomeIcon data-description="license save" icon="save" @click="onSave"
                /></span>
                <span v-b-tooltip.hover title="Cancel Edit"><FontAwesomeIcon icon="times" @click="disableEdit" /></span>
            </template>
        </License>
        <div v-else>
            <a href="#" @click.prevent="onSave">Save without license</a> or
            <a href="#" @click.prevent="editLicense = false">cancel edit.</a>
        </div>
    </div>
    <div v-else-if="license" data-description="license selector" :data-license="license">
        <License :license-id="license">
            <template v-slot:buttons>
                <span v-b-tooltip.hover title="Edit License"
                    ><FontAwesomeIcon icon="edit" data-description="edit license link" @click="editLicense = true"
                /></span>
            </template>
        </License>
    </div>
    <div v-else data-description="license selector" data-license="null">
        <i
            ><a href="#" data-description="edit license link" @click.prevent="editLicense = true"
                >Specify a license for this workflow.</a
            ></i
        >
    </div>
</template>

<script>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faEdit, faSave, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import axios from "axios";
import BootstrapVue from "bootstrap-vue";
import LoadingSpan from "components/LoadingSpan";
import { getAppRoot } from "onload/loadConfig";
import Vue from "vue";

import License from "./License";

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
