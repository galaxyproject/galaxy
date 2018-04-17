<template>
    <div class="ui-portlet-limited">
        <div class="portlet-header">
            <div class="portlet-title">
                <i class="portlet-title-icon fa fa-upload"></i>
                <span class="portlet-title-text"><b>Import a History from an Archive</b></span>
            </div>
        </div>
        <div class="portlet-content">
            <form ref="form">
                <div v-if="errormessage" class="ui-message ui-show alert alert-danger">
                    {{ errormessage }}
                </div>
                <div class="portlet-body">
                        <div class="ui-form-element">
                            <div class="ui-form-title">Archived History URL</div>
                            <input class="ui-input" type="text" name="archive_source"/>
                        </div>
                        <div class="ui-form-element">
                            <div class="ui-form-title">Archived History file</div>
                            <input type="file" name="archive_file"/>
                        </div>
                </div>
                <div class="portlet-buttons">
                    <input class="btn btn-primary" type="button" value="Import History" @click="submit"/>
                </div>
            </form>
        </div>
    </div>
</template>
<script>
import axios from "axios";

export default {
    data() {
        return {
            errormessage: null
        };
    },
    methods: {
        submit: function() {
            /*
            $.ajax({
                url: `${Galaxy.root}api/histories`,
                data: new FormData(this.$refs.form),
                cache: false,
                contentType: false,
                processData: false,
                method: "POST"
            })
                .done(response => {
                    window.location = `${Galaxy.root}histories/list?message=${response.message}&status=success`;
                })
                .fail(response => {
                */
            let formData = new FormData(this.$refs.form);
            axios
                .post(`${Galaxy.root}api/histories`, formData)
                .then(response => {
                    window.location = `${Galaxy.root}histories/list?message=${response.message}&status=success`;
                })
                .catch(response => {
                    let message = response.responseJSON && response.responseJSON.err_msg;
                    this.errormessage = message || "Import failed for unkown reason.";
                });
        }
    }
};
</script>
<style>
.ui-show {
    display: block;
}
</style>
