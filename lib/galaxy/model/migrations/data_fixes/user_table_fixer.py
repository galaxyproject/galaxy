import uuid

from sqlalchemy import (
    func,
    Result,
    select,
    text,
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
        Records updated with the generated value are marked as deleted.
        """
        duplicates = self._get_duplicate_username_data()
        prev_username = None
        for id, username, _ in duplicates:
            if username == prev_username:
                new_username = self._generate_next_available_username(username)
                stmt = update(User).where(User.id == id).values(username=new_username, deleted=True)
                self.connection.execute(stmt)
            else:
                prev_username = username

    def _get_duplicate_username_data(self) -> Result:
        # Duplicate usernames
        duplicates_stmt = select(User.username).group_by(User.username).having(func.count() > 1)
        # User data for records with duplicate usernames (ordering: newest to oldest)
        stmt = (
            select(User.id, User.username, User.create_time)
            .where(User.username.in_(duplicates_stmt))
            .order_by(User.username, User.create_time.desc())
        )
        return self.connection.execute(stmt)

    def _generate_next_available_username(self, username):
        i = 1
        while self.connection.execute(select(User).where(User.username == f"{username}-{i}")).first():
            i += 1
        return f"{username}-{i}"


class EmailDeduplicator:

    def __init__(self, connection):
        self.connection = connection

    def run(self):
        """
        Deduplicate user emails by generating a unique value for all duplicates, keeping
        the email of the most recently created user that has one or more history unchanged.
        If such a user does not exist, keep the oldest user.
        Records updated with the generated value are marked as deleted (we presume them
        to be invalid, and the user should not be able to login).
        """
        stmt = select(User.email).group_by(User.email).having(func.count() > 1)
        duplicate_emails = self.connection.scalars(stmt)
        for email in duplicate_emails:
            users = self._get_users_with_same_email(email)
            user_with_history = self._find_oldest_user_with_history(users)
            duplicates = self._get_users_to_deduplicate(users, user_with_history)
            self._deduplicate_users(email, duplicates)

    def _get_users_with_same_email(self, email: str):
        sql = text(
            """
            SELECT u.id, EXISTS(SELECT h.id FROM history h WHERE h.user_id = u.id)
            FROM galaxy_user u
            WHERE u.email = :email
            ORDER BY u.create_time
            """
        )
        params = {"email": email}
        return self.connection.execute(sql, params).all()

    def _find_oldest_user_with_history(self, users):
        for user_id, exists in users:
            if exists:
                return user_id
        return None

    def _get_users_to_deduplicate(self, users, user_with_history):
        if user_with_history:
            # Preserve the oldest user with a history
            return [user_id for user_id, _ in users if user_id != user_with_history]
        else:
            # Preserve the oldest user
            return [user_id for user_id, _ in users[1:]]

    def _deduplicate_users(self, email, to_deduplicate):
        for id in to_deduplicate:
            new_email = self._generate_replacement_for_duplicate_email(email)
            stmt = update(User).where(User.id == id).values(email=new_email, deleted=True)
            self.connection.execute(stmt)

    def _generate_replacement_for_duplicate_email(self, email: str) -> str:
        """
        Generate a replacement for a duplicate email value. The new value consists of the original
        email and a unique suffix. Since the original email is part of the new value, it will be
        possible to retrieve the user record based on this value, if needed.
        """
        return f"{email}-{uuid.uuid4()}"
