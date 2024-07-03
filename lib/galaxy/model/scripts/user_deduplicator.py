from sqlalchemy import (
    func,
    select,
    update,
)
from sqlalchemy.engine import (
    Connection,
    Result,
)

from galaxy.managers.users import generate_next_available_username_with_connection
from galaxy.model import User


class UserDeduplicator:

    def __init__(self, engine):
        self.engine = engine

    def deduplicate_emails(self) -> None:
        with self.engine.begin() as connection:
            prev_email = None
            for id, email, _ in self._get_duplicate_email_data():
                if email == prev_email:
                    new_email = self._generate_replacement_for_duplicate_email(connection, email)
                    stmt = update(User).where(User.id == id).values(email=new_email)
                    connection.execute(stmt)
                else:
                    prev_email = email

    def deduplicate_usernames(self) -> None:
        with self.engine.begin() as connection:
            prev_username = None
            for id, username, _ in self._get_duplicate_username_data():
                if username == prev_username:
                    new_username = generate_next_available_username_with_connection(
                        connection, username, model_class=User
                    )
                    stmt = update(User).where(User.id == id).values(username=new_username)
                    connection.execute(stmt)
                else:
                    prev_username = username

    def _get_duplicate_username_data(self) -> Result:
        counts = select(User.username, func.count()).group_by(User.username).having(func.count() > 1)
        sq = select(User.username).select_from(counts.cte())
        stmt = (
            select(User.id, User.username, User.create_time)
            .where(User.username.in_(sq))
            .order_by(User.username, User.create_time.desc())
        )

        with self.engine.connect() as conn:
            duplicates = conn.execute(stmt)
        return duplicates

    def _get_duplicate_email_data(self) -> Result:
        counts = select(User.email, func.count()).group_by(User.email).having(func.count() > 1)
        sq = select(User.email).select_from(counts.cte())
        stmt = (
            select(User.id, User.email, User.create_time)
            .where(User.email.in_(sq))
            .order_by(User.email, User.create_time.desc())
        )

        with self.engine.connect() as conn:
            duplicates = conn.execute(stmt)
        return duplicates

    def _generate_replacement_for_duplicate_email(self, connection: Connection, email: str) -> str:
        """
        Generate a replacement for a duplicate email value. The new value consists of the original email
        and a suffix. This value cannot be used as an email, but since the original email is part of
        the new value, it will be possible to retrieve the user record based on this value, if needed.
        This is used to remove duplicate email values from the database, for the rare case the database
        contains such values.
        """
        i = 1
        while connection.execute(select(User).where(User.email == f"{email}-{i}")).first():
            i += 1
        return f"{email}-{i}"
