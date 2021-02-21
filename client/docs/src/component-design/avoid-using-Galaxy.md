Don't directly reference window.Galaxy in Vue components

You've got components. Components take props. Please pass in any values you might need from
window.Galaxy as props and avoid referencing global Galaxy inside your components. I've even created
basic providers which give you access to the Galaxy.config, current user, and current user
histories. Please use them to retrieve your values, and bypass importing Galaxy altogether.

There are use-cases where the Backbone models update over time and we need to update some value
inside Vue. Let me help you solve those problems instead of importing backbone models into Vue
components. Usually the answer is a backbone event listener that updates some relevant Vuex store.

When writing a new component, your goal should be to replace old Galaxy functionality, not to
repackage it in another format so we continue to have Galaxy's inherent problems, the most important
of which is...