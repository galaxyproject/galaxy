<template>
    <div>
        <b-alert :show="messageVisible" variant="danger">
            {{ messageText }}
        </b-alert>
        <b-alert :show="infoVisible" variant="info">
            No errors available.
        </b-alert>
        <b-table :show="errorsVisible" striped :fields="errorsAttributes" :items="errors"/>
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
                { key: 'file', sortable: true },
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
        },
        infoVisible: function() {
            return !this.errorsVisible && this.errorsLoaded;
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
