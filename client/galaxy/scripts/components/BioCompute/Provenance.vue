<template>
    <table>
        <tr>
        <td colspan=3>
            <h2>Provenance Domain</h2>
        </td>
        </tr>
        <tr>
            <td>Name</td>
            <td colspan=2>{{ item.name }}</td>
        </tr>
        <tr>
            <td>Version</td>
            <td>{{ item.version }}</td>
        </tr>
        <tr>
            <td class='border_except'>Review</td>
        </tr>
        <tr>
            <td></td>
            <td>Status</td>
            <td>Date</td>
            <td>Name</td>
            <td>Email</td>
            <td>Affiliation</td>
            <td>Comment</td>
            <td></td>
        </tr>
        <tr v-for="(object, index) in item.review" :key="object">
            <!-- Source:  https://stackoverflow.com/questions/51953173/how-do-i-pass-input-text-using-v-onchange-to-my-vue-method -->
            <td><button>Remove</button></td>
            <td><textarea :data-jpath="`provenance_domain.review[${index}].status`" v-on:input='event => store_input(event)' v-model="object.status"/></td>
            <td><textarea v-on:input='event => store_input(event)' v-model="object.date"/></textarea></td>
            <td><textarea v-on:input='event => store_input(event)' v-model="object.reviewer.name"/></textarea></td>
            <td><textarea v-on:input='event => store_input(event)' v-model="object.reviewer.email" /></textarea></td>
            <td><textarea v-on:input='event => store_input(event)' v-model="object.reviewer.affiliation"/></textarea></td>
            <td><textarea v-on:input='event => store_input(event)' v-model="object.reviewer_comment"/></textarea></td>
        </tr>
        <tr>
          <td colspan=5>
            <button>Add Review Step</button>
          </td>
        <tr>
            <td colspan=8>
            </td>
        </tr>
          <tr>
              <td>Derived From</td>
              <td>{{ item.derived_from }}</td>
          </tr>
        <tr>
            <td>Obsolete After</td>
            <td>{{ item.obsolete_after }}</td>
        </tr>
        <tr>
            <td colspan=8>
            </td>
        </tr>
        <tr>
            <td>Embargo</td>
            <td colspan=2></td>
            <td class='bold_contain'>Created</td>
            <td></td>
            <td class='bold_contain'>Modified</td>
        </tr>
        <tr>
            <td class='bold_except'>
            </td>
            <td>
            </td>
            <td></td>
            <td>{{ item.created }}</td>
            <td></td>
            <td>{{ item.modified }}</td>
        </tr>
        <tr>
            <td colspan=8>
            </td>
        </tr>
        <tr>
            <td>Contributors</td>
        </tr>
        <tr>
            <td>Name</td>
            <td class='bold_contain'>Affiliation</td>
            <td class='bold_contain'>Email</td>
            <td class='bold_contain'>Contribution</td>
            <td></td>
        </tr>
        <tr v-for="contrib in item.contributors" :key="contrib.name">
            <td class='bold_except'>{{ contrib.name }}</td>
            <td>{{ contrib.affiliation }}</td>
            <td>{{ contrib.email }}</td>
            <td>{{ contrib.contribution[0] }}</td>
        </tr>
        <tr>
        <td colspan=4>
        <button>Add Contributor</button>
        </td>
        </tr>
        <tr>
            <td>License</td>
            <td>{{ item.license }}</td>
        </tr>
    </table>
</template>

<script>

// Standard imports.
import updateStorage from './ScriptsShared/updateStorage'

export default {

    mixins: [updateStorage],
    name: 'provenance',
    props: {
        item: Object,
        invokeId: String
    }

};
</script>
