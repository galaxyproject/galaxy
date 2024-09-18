from sqlalchemy import (
    func,
    Result,
    select,
    update,
)

from galaxy.model import User


class UsernameDeduplicator:

    def __init__(self, connection):
        self.connection = connection

    def run(self):
        """
        Deduplicate usernames by generating a unique value for all duplicates, keeping
        the username of the most recently created user unchanged.
        """
        duplicates = self._get_duplicate_username_data()
        prev_username = None
        for id, username, _ in duplicates:
            if username == prev_username:
                new_username = self._generate_next_available_username(username)
                stmt = update(User).where(User.id == id).values(username=new_username)
                self.connection.execute(stmt)
            else:
                prev_username = username

    def _get_duplicate_username_data(self) -> Result:
        # Duplicate usernames
        counts = select(User.username, func.count()).group_by(User.username).having(func.count() > 1)
        sq = select(User.username).select_from(counts.cte())
        # User data for records with duplicate usernames (ordering: newest to oldest)
        stmt = (
            select(User.id, User.username, User.create_time)
            .where(User.username.in_(sq))
            .order_by(User.username, User.create_time.desc())
        )
        return self.connection.execute(stmt)

    def _generate_next_available_username(self, username):
        i = 1
        while self.connection.execute(select(User).where(User.username == f"{username}-{i}")).first():
            i += 1
        return f"{username}-{i}"
