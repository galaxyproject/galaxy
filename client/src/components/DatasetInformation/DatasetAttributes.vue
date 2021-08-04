<template>
    <div>
        <h4>Edit Dataset Attributes</h4>
        <b-alert v-if="messageText" :variant="messageVariant" show>
            <h4 class="alert-heading">Failed to access dataset details.</h4>
            {{ messageText }}
        </b-alert>
        <DatasetAttributesProvider :id="datasetId" v-slot="{ result: dataset, loading }">
            <div v-if="!loading" class="mt-3">
                <b-tabs>
                    <b-tab>
                        <template #title><font-awesome-icon icon="bars" class="mr-1" />Attributes</template>
                        <p>I'm the first tab</p>
                    </b-tab>
                    <b-tab>
                        <template #title><font-awesome-icon icon="cog" class="mr-1" />Convert</template>
                        <p>I'm the second tab</p>
                    </b-tab>
                    <b-tab>
                        <template #title><font-awesome-icon icon="database" class="mr-1" />Datatypes</template>
                        <p>I'm the third tab</p>
                    </b-tab>
                    <b-tab>
                        <template #title><font-awesome-icon icon="user" class="mr-1" />Permissions</template>
                        <p>I'm the fourth tab</p>
                    </b-tab>
                </b-tabs>
            </div>
        </DatasetAttributesProvider>
    </div>
</template>

<script>
import FormElement from "components/Form/FormElement";
import { DatasetAttributesProvider } from "components/providers/DatasetProvider";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faBars, faDatabase, faCog, faUser } from "@fortawesome/free-solid-svg-icons";
import { sendErrorReport } from "./services";

library.add(faBars);
library.add(faDatabase);
library.add(faCog);
library.add(faUser);

export default {
    components: {
        DatasetAttributesProvider,
        FontAwesomeIcon,
    },
    props: {
        datasetId: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            message: null,
            email: null,
            messageText: null,
            messageVariant: null,
        };
    },
    methods: {
        onError(err) {
            this.messageText = err;
        },
        submit(dataset, userEmail) {
            const email = this.email || userEmail;
            const message = this.message;
            sendErrorReport(dataset, message, email).then(
                (resultMessages) => {
                    this.resultMessages = resultMessages;
                },
                (messageText) => {
                    this.messageText = messageText;
                }
            );
        },
    },
};
</script>
