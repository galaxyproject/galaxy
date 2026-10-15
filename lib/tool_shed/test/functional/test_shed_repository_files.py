from galaxy.exceptions.error_codes import error_codes_by_name
from galaxy_test.base import api_asserts
from ..base.api import ShedApiTestCase


class TestShedRepositoryFilesApi(ShedApiTestCase):
    def test_repository_files_lists_unchanged_files(self):
        # The revision that only adds README.txt must still list and serve column_maker.xml.
        populator = self.populator
        repository = populator.setup_test_data_repo("column_maker_unchanged")
        revisions = populator.get_downloadable_revisions(repository)
        listings = {revision: populator.get_repository_files(repository, revision) for revision in revisions}
        for revision, listing in listings.items():
            assert listing.changeset_revision == revision
            assert "column_maker_unchanged/column_maker.xml" in [entry.path for entry in listing.files]
        readme_revisions = [
            revision
            for revision, listing in listings.items()
            if "column_maker_unchanged/README.txt" in [entry.path for entry in listing.files]
        ]
        assert len(readme_revisions) == 1
        readme_listing = listings[readme_revisions[0]]
        entry = next(e for e in readme_listing.files if e.path == "column_maker_unchanged/column_maker.xml")
        assert entry.type == "file"
        assert not entry.executable
        contents = populator.get_repository_file_contents(
            repository, readme_revisions[0], "column_maker_unchanged/column_maker.xml"
        )
        assert contents.content and 'id="Add_a_column1"' in contents.content
        assert contents.size == entry.size

    def test_repository_file_contents_per_revision(self):
        populator = self.populator
        repository = populator.setup_test_data_repo("column_maker")
        revisions = populator.get_downloadable_revisions(repository)
        assert len(revisions) == 3
        for revision, version in zip(revisions, ("1.1.0", "1.2.0", "1.3.0")):
            contents = populator.get_repository_file_contents(repository, revision, "column_maker/column_maker.xml")
            assert contents.path == "column_maker/column_maker.xml"
            assert contents.type == "file"
            assert not contents.binary
            assert not contents.truncated
            assert contents.content is not None
            assert f'version="{version}"' in contents.content
            assert contents.size == len(contents.content.encode("utf-8"))

    def test_repository_files_anonymous(self):
        populator = self.populator
        repository = populator.setup_test_data_repo("column_maker", end=1)
        revision = populator.get_downloadable_revisions(repository)[0]
        listing_response = populator.get_repository_files_raw(repository, revision, anonymous=True)
        api_asserts.assert_status_code_is_ok(listing_response)
        assert [entry["path"] for entry in listing_response.json()["files"]] == ["column_maker/column_maker.xml"]
        contents_response = populator.get_repository_files_raw(
            repository, revision, path="column_maker/column_maker.xml", anonymous=True
        )
        api_asserts.assert_status_code_is_ok(contents_response)
        assert 'version="1.1.0"' in contents_response.json()["content"]

    def test_repository_file_contents_percent_encoded_path(self):
        # {path:path} matches the decoded path, so an encoded slash names the same nested file.
        populator = self.populator
        repository = populator.setup_test_data_repo("column_maker", end=1)
        revision = populator.get_downloadable_revisions(repository)[0]
        literal = populator.get_repository_files_raw(repository, revision, path="column_maker/column_maker.xml")
        encoded = populator.get_repository_files_raw(repository, revision, path="column_maker%2Fcolumn_maker.xml")
        api_asserts.assert_status_code_is_ok(literal)
        api_asserts.assert_status_code_is_ok(encoded)
        assert encoded.json() == literal.json()
        assert encoded.headers["ETag"] == literal.headers["ETag"]

    def test_repository_files_rejects_unbounded_revisions(self):
        populator = self.populator
        repository = populator.setup_test_data_repo("column_maker", end=1)
        revision = populator.get_downloadable_revisions(repository)[0]
        api_asserts.assert_status_code_is_ok(populator.get_repository_files_raw(repository, revision))
        for bad_revision in (
            "tip",
            "default",
            "0",
            revision[:8],
            f"{revision}{'0' * 28}",
            "000000000000",
            "deadbeefdead",
        ):
            self._assert_not_found(populator.get_repository_files_raw(repository, bad_revision))
            self._assert_not_found(
                populator.get_repository_files_raw(repository, bad_revision, path="column_maker/column_maker.xml")
            )

    def test_repository_file_contents_rejects_bad_paths(self):
        populator = self.populator
        repository = populator.setup_test_data_repo("column_maker", end=1)
        revision = populator.get_downloadable_revisions(repository)[0]
        api_asserts.assert_status_code_is_ok(
            populator.get_repository_files_raw(repository, revision, path="column_maker/column_maker.xml")
        )
        for bad_path in (
            "%2E%2E/column_maker/column_maker.xml",
            "column_maker/%2E%2E/column_maker/column_maker.xml",
            "column_maker%2Fcolumn_maker.xml%00",
            ".hg/hgrc",
            ".hg/store/00manifest.i",
            "column_maker",
            "missing.txt",
        ):
            self._assert_not_found(populator.get_repository_files_raw(repository, revision, path=bad_path))

    def test_repository_files_unavailable_revisions(self):
        populator = self.populator
        repository = populator.setup_test_data_repo("column_maker", end=1)
        revision = populator.get_downloadable_revisions(repository)[0]
        path = "column_maker/column_maker.xml"

        populator.set_deprecated(repository)
        self._assert_not_found(populator.get_repository_files_raw(repository, revision))
        self._assert_not_found(populator.get_repository_files_raw(repository, revision, path=path))
        populator.unset_deprecated(repository)
        api_asserts.assert_status_code_is_ok(populator.get_repository_files_raw(repository, revision))

        populator.set_malicious(repository, revision)
        self._assert_not_found(populator.get_repository_files_raw(repository, revision))
        self._assert_not_found(populator.get_repository_files_raw(repository, revision, path=path))
        populator.unset_malicious(repository, revision)
        api_asserts.assert_status_code_is_ok(populator.get_repository_files_raw(repository, revision, path=path))

    def test_repository_files_are_cacheable(self):
        populator = self.populator
        repository = populator.setup_test_data_repo("column_maker", end=1)
        revision = populator.get_downloadable_revisions(repository)[0]
        for path in (None, "column_maker/column_maker.xml"):
            response = populator.get_repository_files_raw(repository, revision, path=path)
            api_asserts.assert_status_code_is_ok(response)
            etag = response.headers["ETag"]
            assert response.headers["Cache-Control"] == "public, max-age=86400"
            assert "immutable" not in response.headers["Cache-Control"]
            # Contents are only ever served wrapped in JSON, never as the file's own type.
            assert response.headers["Content-Type"] == "application/json"

            not_modified = populator.get_repository_files_raw(
                repository, revision, path=path, headers={"If-None-Match": etag}
            )
            assert not_modified.status_code == 304
            assert not_modified.content == b""
            assert not_modified.headers["ETag"] == etag

            stale = populator.get_repository_files_raw(
                repository, revision, path=path, headers={"If-None-Match": '"nolongercurrent"'}
            )
            api_asserts.assert_status_code_is_ok(stale)
            assert stale.content == response.content

        listing_etag = populator.get_repository_files_raw(repository, revision).headers["ETag"]
        contents_etag = populator.get_repository_files_raw(
            repository, revision, path="column_maker/column_maker.xml"
        ).headers["ETag"]
        assert listing_etag != contents_etag

        for not_found in (
            populator.get_repository_files_raw(repository, "deadbeefdead"),
            populator.get_repository_files_raw(repository, revision, path="missing.txt"),
        ):
            self._assert_not_found(not_found)
            assert "ETag" not in not_found.headers
            assert "public" not in not_found.headers.get("Cache-Control", "")

    def _assert_not_found(self, response):
        # Distinguishes the manager's ObjectNotFound from a route that does not exist.
        api_asserts.assert_status_code_is(response, 404)
        api_asserts.assert_error_code_is(response, error_codes_by_name["USER_OBJECT_NOT_FOUND"])
