<script setup>
import { ref, reactive, inject } from "vue";
import { BModal } from "bootstrap-vue";
import axios from "axios";
import { Toast } from "composables/toast";
import { withPrefix } from "utils/redirect";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import ExternalLink from "components/ExternalLink";

const sendBCOModal = ref(null);
const generatingBCO = ref(false);

const form = reactive({
    fetch: "https://biocomputeobject.org",
    authorization: "",
    table: "BCO",
    owner_group: "",
});

const invocationId = inject("invocationId");

function showModal() {
    resetForm();
    sendBCOModal.value.show();
}

function hideModal() {
    sendBCOModal.value.hide();
}

function resetForm() {
    form.fetch = "";
    form.authorization = "";
    form.table = "GALXY";
    form.owner_group = "";
}

function handleError(err) {
    Toast.error(`Failed to send BCO. ${err}`);
}

async function generateBcoContent() {
    try {
        generatingBCO.value = true;
        const data = {
            model_store_format: "bco.json",
            include_files: false,
            include_deleted: false,
            include_hidden: false,
        };
        const response = await axios.post(withPrefix(`/api/invocations/${invocationId}/prepare_store_download`), data);
        const storage_request_id = response.data.storage_request_id;
        const pollUrl = withPrefix(`/api/short_term_storage/${storage_request_id}/ready`);
        const resultUrl = withPrefix(`/api/short_term_storage/${storage_request_id}`);
        let pollingResponse = await axios.get(pollUrl);
        let maxRetries = 120;
        while (!pollingResponse.data && maxRetries) {
            await wait();
            pollingResponse = await axios.get(pollUrl);
            maxRetries -= 1;
        }
        if (!pollingResponse.data) {
            throw "Timeout waiting for BioCompute Object export result!";
        } else {
            const resultResponse = await axios.get(resultUrl);
            return resultResponse.data;
        }
    } catch (err) {
        handleError(err);
    } finally {
        generatingBCO.value = false;
    }
}

const wait = function (ms = 2000) {
    return new Promise((resolve) => {
        setTimeout(resolve, ms);
    });
};

async function sendBco(bcoContent) {
    const bcoData = {
        POST_api_objects_draft_create: [
            {
                contents: bcoContent,
                owner_group: form.owner_group,
                schema: "IEEE",
                prefix: form.table,
            },
        ],
    };

    const headers = {
        Authorization: "Token " + form.authorization,
        "Content-type": "application/json; charset=UTF-8",
    };
    try {
        await axios.post(`${form.fetch}/api/objects/drafts/create/`, bcoData, { headers: headers });
        Toast.success(`Invocation successfully sent to: ${form.fetch}`);
    } catch (err) {
        handleError(err);
    }
}

async function submitForm() {
    const bcoContent = await generateBcoContent();
    hideModal();
    await sendBco(bcoContent);
    resetForm();
}

defineExpose({ showModal });
</script>

<template>
    <b-modal ref="sendBCOModal" title="Submit To BCODB" title-tag="h2" centered hide-footer>
        <div>
            <p>
                To submit to a BCODB you need to already have an authenticated account. Instructions on submitting a BCO
                from Galaxy are available
                <external-link href="https://w3id.org/biocompute/tutorials/galaxy_quick_start/" target="_blank"
                    >here</external-link
                >.
            </p>
            <form @submit.prevent="submitForm">
                <div class="form-group">
                    <label for="fetch">
                        <input
                            id="fetch"
                            v-model="form.fetch"
                            type="text"
                            class="form-control"
                            placeholder="https://biocomputeobject.org"
                            autocomplete="off"
                            required />
                        BCO DB URL (example: https://biocomputeobject.org)
                    </label>
                </div>
                <div class="form-group">
                    <label for="authorization">
                        <input
                            id="authorization"
                            v-model="form.authorization"
                            type="password"
                            class="form-control"
                            autocomplete="off"
                            required />
                        User API Key
                    </label>
                </div>
                <div class="form-group">
                    <label for="table">
                        <input
                            id="table"
                            v-model="form.table"
                            type="text"
                            class="form-control"
                            placeholder="GALXY"
                            required />
                        Prefix
                    </label>
                </div>
                <div class="form-group">
                    <label for="owner_group">
                        <input
                            id="owner_group"
                            v-model="form.owner_group"
                            type="text"
                            class="form-control"
                            autocomplete="off"
                            required />
                        User Name
                    </label>
                </div>
                <div class="form-group">
                    <div v-if="generatingBCO">
                        <font-awesome-icon icon="spinner" spin />
                        Generating BCO please wait...
                    </div>
                    <button v-else class="btn btn-primary">{{ "Submit" | localize }}</button>
                </div>
            </form>
        </div>
    </b-modal>
</template>
