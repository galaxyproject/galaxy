<template>
  <div>
    <h4>Current Custom Builds</h4>
    <table class="grid">
      <thead>
        <tr>
          <th>Name</th>
          <th>Key</th>
          <th>Number of chroms/contigs</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <template v-if="builds.length">
          <tr v-for="build in builds" :key="build.id">
            <td>{{ build.name }}</td>
            <td>{{ build.id }}</td>
            <td>{{ build.count }}</td>
            <td>
              <div class="ui-button-icon-plain" style="display: inline-block;">
                <div class="button" data-original-title="" title="" @click="deleteBuild(build.id, $event)">
                  <i class="icon fa fa-trash-o"></i><span class="title"></span>
                </div>
              </div>
            </td>
          </tr>
        </template>
        <div v-else style="display: inline;">No content available.</div>
      </tbody>
    </table>

    <h4 class="ui-margin-top">Add a Custom Build</h4>
    <span class="ui-column">
      <div class="ui-column-left">
        <div class="ui-margin-top">
          <div class="ui-portlet-limited">
            <div class="portlet-content">
              <div class="portlet-body">

                <div class="ui-form-element section-row" tour_id="name" style="display: block;">
                  <div class="ui-form-title">
                    <span class="ui-form-title-text" style="display: inline;">Name</span>
                  </div>
                  <div class="ui-form-field" style="display: block;">
                    <input class="ui-input" type="text" style="display: inline-block;">
                    <span class="ui-form-info">Specify a build name e.g. Hamster.</span>
                  </div>
                </div>
                <div class="ui-form-element section-row" tour_id="id" style="display: block;">
                  <div class="ui-form-title">
                    <span class="ui-form-title-text" style="display: inline;">Key</span>
                  </div>
                  <div class="ui-form-field" style="display: block;">
                    <input class="ui-input" type="text" style="display: inline-block;">
                    <span class="ui-form-info">Specify a build key e.g. hamster_v1.</span>
                    <div class="ui-form-backdrop" style="display: none;"></div>
                  </div>
                </div>
              </div>

              <div class="portlet-buttons">
                  <button type="button" class="ui-button-default btn btn-primary ui-clear-float" id="save" style="display: inline-block;" data-original-title="" title="">
                    <i class="icon fa fa-save ui-margin-right"></i>
                    <span class="title">Save</span>
                  </button>
                </div>
            </div>
          </div>
        </div>
      </div>
      <div class="ui-column-right alert alert-info">
        <template v-if="lengthType === 'fasta'">
          <h4>FASTA format</h4>
          <p>This is a multi-fasta file from your current history that provides the genomesequences for each chromosome/contig in your build.</p>
          <p>Here is a snippet from an example multi-fasta file:</p>
          <pre>&gt;chr1
ATTATATATAAGACCACAGAGAGAATATTTTGCCCGG...

&gt;chr2
GGCGGCCGCGGCGATATAGAACTACTCATTATATATA...

...</pre>
        </template>
        <template v-else>
          <h4>Length Format</h4>
          <p>The length format is two-column, separated by whitespace, of the form:</p>
          <pre>chrom/contig   length of chrom/contig</pre>
          <p>For example, the first few entries of <em>mm9.len</em> are as follows:</p>
          <pre>chr1    197195432
chr2    181748087
chr3    159599783
chr4    155630120
chr5    152537259</pre>
          <p>Trackster uses this information to populate the select box for chrom/contig, andto set the maximum basepair of the track browser. You may either upload a .len fileof this format (Len File option), or directly enter the information into the box (Len Entry option).</p>
        </template>
      </div>
    </span>
  </div>
</template>

<script>
import axios from "axios";

export default {
  data() {
    return {
      builds: [],
      lengthType: "fasta",
      dataSources: [
        { id: "", name: "" },
        { id: "", name: "" },
        { id: "", name: "" }
      ]
    };
  },

  created() {
    axios
      .get(`${Galaxy.root}api/users/${Galaxy.user.id}/custom_builds`)
      .then(response => {
        this.builds = response.data;
      })
      .catch(error => {
        console.error(error);
      });
  },

  methods: {
    deleteBuild(id) {
      console.log('id', id);
    }
  }
}
</script>

<style>

</style>
