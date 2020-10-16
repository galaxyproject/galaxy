from galaxy.tools.verify.interactor import GalaxyInteractorApi


class TestCaseGalaxyInteractor(GalaxyInteractorApi):

    def __init__(self, functional_test_case, test_user=None):
        self.functional_test_case = functional_test_case
        super(TestCaseGalaxyInteractor, self).__init__(
            galaxy_url=functional_test_case.url,
            master_api_key=functional_test_case.master_api_key,
            api_key=functional_test_case.user_api_key,
            test_user=test_user,
            keep_outputs_dir=getattr(functional_test_case, "keepOutdir", None),
        )
