"""Unit tests for PageManager embed-token resolution (expiry boundary)."""

from datetime import timedelta

from galaxy import model
from galaxy.managers.pages import PageManager
from galaxy.model import now
from .base import BaseTestCase


class TestPageManager(BaseTestCase):
    def set_up_managers(self):
        super().set_up_managers()
        # PageManager.__init__ reads app.workflow_manager; the mock app does not
        # populate it and resolve_embed_token never uses it, so stub it.
        self.app.workflow_manager = None
        self.page_manager: PageManager = self.app[PageManager]

    def _mint_token(self, expiration_time=None) -> model.PageEmbedToken:
        user = self.user_manager.create(email="embed@example.com", username="embed", password="123456")
        page = model.Page()
        page.title = "Embed page"
        page.slug = "embed-page"
        page.user = user
        token = model.PageEmbedToken(page=page, user=user)
        if expiration_time is not None:
            token.expiration_time = expiration_time
        session = self.page_manager.session()
        session.add_all([page, token])
        session.commit()
        return token

    def test_resolve_valid_token(self):
        token = self._mint_token()
        resolved = self.page_manager.resolve_embed_token(token.token)
        assert resolved is not None
        assert resolved.token == token.token
        assert resolved.user is not None

    def test_resolve_expired_token_returns_none(self):
        token = self._mint_token(expiration_time=now() - timedelta(minutes=1))
        assert self.page_manager.resolve_embed_token(token.token) is None

    def test_resolve_unknown_token_returns_none(self):
        assert self.page_manager.resolve_embed_token("does-not-exist") is None

    def test_resolve_empty_token_returns_none(self):
        assert self.page_manager.resolve_embed_token("") is None
