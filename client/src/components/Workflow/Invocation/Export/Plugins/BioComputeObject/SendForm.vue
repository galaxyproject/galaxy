<script setup>
import { ref, reactive, inject } from "vue";
import { BModal } from "bootstrap-vue";
import axios from "axios";
import { Toast } from "ui/toast";

const sendBCOModal = ref(null);

const form = reactive({
    fetch: "",
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

/**
 * TODO: replace with `prepare_download` endpoint when https://github.com/galaxyproject/galaxy/pull/14620 is ready
 */
async function generateBcoContent() {
    try {
        const resp = await axios.get(`/api/invocations/${invocationId}/biocompute/`);
        return resp.data;
    } catch (err) {
        handleError(err);
    }
}

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
    hideModal();
    const bcoContent = await generateBcoContent();
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
                <a href="https://w3id.org/biocompute/tutorials/galaxy_quick_start/" target="_blank">here</a>.
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
                            autocomplete="section-bco"
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
                            autocomplete="section-bco"
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
                            autocomplete="section-bco"
                            required />
                        User Name
                    </label>
                </div>
                <div class="form-group">
                    <button class="btn btn-primary">{{ "Submit" | localize }}</button>
                </div>
            </form>
        </div>
    </b-modal>
</template>
