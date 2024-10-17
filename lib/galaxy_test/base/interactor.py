from galaxy.tool_util.verify.interactor import GalaxyInteractorApi


class TestCaseGalaxyInteractor(GalaxyInteractorApi):
    def __init__(self, functional_test_case, test_user=None, api_key=None):
        self.functional_test_case = functional_test_case
        admin_api_key = getattr(functional_test_case, "master_api_key", None) or getattr(
            functional_test_case, "admin_api_key", None
        )
        super().__init__(
            galaxy_url=functional_test_case.url,
            master_api_key=admin_api_key,
            api_key=api_key or getattr(functional_test_case, "user_api_key", None),
            test_user=test_user,
            keep_outputs_dir=getattr(functional_test_case, "keepOutdir", None),
        )
