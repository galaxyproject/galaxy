import logging

log = logging.getLogger(__name__)


class Metadata:
    def __init__(self):
        self.type = None

    def get_changesets_for_setting_metadata(self, app, repository):
        repo = repository.hg_repo
        return repo.changelog

    def is_valid_for_type(self, repository, revisions_to_check=None):
        raise Exception("Unimplemented Method")


class TipOnly(Metadata):
    def __init__(self):
        self.type = None

    def get_changesets_for_setting_metadata(self, app, repository):
        repo = repository.hg_repo
        return [repo.changelog.tip()]
