<template>
    <div>
        <div v-if="messageVisible" class="alert alert-danger">
            {{ messageText }}
        </div>
        <div v-if="!errorsVisible && errorsLoaded" class="alert alert-info">
            No errors available.
        </div>
        <b-table v-if="errorsVisible" striped :fields="errorsAttributes" :items="errors"/>
    </div>
</template>
<script>
import { getErrorStack } from "./AdminServices.js"

export default {
    data() {
        return {
            errors: [],
            errorsLoaded: false,
            errorsAttributes: [
                { key: 'time', sortable: true },
                { key: 'phase', sortable: true },
                { key: 'file' },
                { key: 'error' }
            ],
            messageText: null
        };
    },
    computed: {
        errorsVisible: function() {
            return this.errors.length > 0;
        },
        errorsLength: function() {
            return this.errors.length;
        },
        messageVisible: function() {
            return this.messageText != null;
        }
    },
    created() {
        getErrorStack()
            .then(response => {
                this.errors = response.data;
                this.errorsLoaded = true;
            })
            .catch(e => {
                let message = e && e.response && e.response.data && e.response.data.err_msg;
                this.messageText = message || "Request failed for an unknown reason.";
            });
    }
};
</script>
