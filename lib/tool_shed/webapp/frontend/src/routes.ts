import AdminControls from "@/components/pages/AdminControls.vue"
import LandingPage from "@/components/pages/LandingPage.vue"
import LoginPage from "@/components/LoginPage.vue"
import RegisterPage from "@/components/RegisterPage.vue"
import RegistrationSuccess from "@/components/RegistrationSuccess.vue"
import HelpPage from "@/components/pages/HelpPage.vue"
import RepositoriesByCategories from "@/components/pages/RepositoriesByCategories.vue"
import RepositoriesByOwners from "@/components/pages/RepositoriesByOwners.vue"
import RepositoriesByOwner from "@/components/pages/RepositoriesByOwner.vue"
import RepositoriesBySearch from "@/components/pages/RepositoriesBySearch.vue"
import RepositoriesByCategory from "@/components/pages/RepositoriesByCategory.vue"
import ComponentsShowcase from "@/components/pages/ComponentsShowcase.vue"
import RepositoryPage from "@/components/pages/RepositoryPage.vue"
import ManageApiKey from "@/components/pages/ManageApiKey.vue"
import ChangePassword from "@/components/pages/ChangePassword.vue"
import CitableRepositoryPage from "@/components/pages/CitableRepositoryPage.vue"

import type { RouteRecordRaw } from "vue-router"

const routes: Array<RouteRecordRaw> = [
    {
        path: "/",
        component: LandingPage,
    },
    {
        path: "/register",
        component: RegisterPage,
    },
    {
        path: "/login",
        component: LoginPage,
    },
    {
        path: "/user/change_password_success",
        component: LandingPage,
        props: { message: "Password successfully changed!" },
    },
    {
        path: "/registration_success",
        component: RegistrationSuccess,
    },
    {
        path: "/login_success",
        component: LandingPage,
        props: { message: "Login successful!" },
    },
    {
        path: "/logout_success",
        component: LandingPage,
        props: { message: "Logout successful!" },
    },
    {
        path: "/help",
        component: HelpPage,
    },
    {
        path: "/admin",
        component: AdminControls,
    },
    {
        path: "/_component_showcase",
        component: ComponentsShowcase,
    },
    {
        path: "/repositories_by_search",
        component: RepositoriesBySearch,
    },
    {
        path: "/repositories_by_category",
        component: RepositoriesByCategories,
    },
    {
        path: "/repositories_by_owner",
        component: RepositoriesByOwners,
    },
    {
        path: "/repositories_by_owner/:username",
        component: RepositoriesByOwner,
        props: true,
    },
    {
        path: "/repositories_by_category/:categoryId",
        component: RepositoriesByCategory,
        props: true,
    },
    {
        path: "/repositories/:repositoryId",
        component: RepositoryPage,
        props: true,
    },
    {
        path: "/user/api_key",
        component: ManageApiKey,
    },
    {
        path: "/user/change_password",
        component: ChangePassword,
    },
    // legacy style access - was thought of as a citable URL
    // so lets keep this path.
    {
        path: "/view/:username",
        component: RepositoriesByOwner,
        props: true,
    },
    {
        path: "/view/:username/:repositoryName",
        component: CitableRepositoryPage,
        props: true,
    },
    {
        path: "/view/:username/:repositoryName/:changesetRevision",
        component: CitableRepositoryPage,
        props: true,
    },
]

export default routes
