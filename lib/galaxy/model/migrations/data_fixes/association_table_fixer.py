from abc import (
    ABC,
    abstractmethod,
)

from sqlalchemy import (
    delete,
    func,
    null,
    or_,
    select,
)

from galaxy.model import (
    GroupRoleAssociation,
    UserGroupAssociation,
    UserRoleAssociation,
)


class AssociationNullFix(ABC):

    def __init__(self, connection):
        self.connection = connection
        self.assoc_model = self.association_model()
        self.assoc_name = self.assoc_model.__tablename__
        self.where_clause = self.build_where_clause()

    def run(self):
        invalid_assocs = self.count_associations_with_nulls()
        if invalid_assocs:
            self.delete_associations_with_nulls()

    def count_associations_with_nulls(
        self,
    ):
        """
        Retrieve association records where one or both associated item ids are null.
        """
        select_stmt = select(func.count()).where(self.where_clause)
        return self.connection.scalar(select_stmt)

    def delete_associations_with_nulls(self):
        """
        Delete association records where one or both associated item ids are null.
        """
        delete_stmt = delete(self.assoc_model).where(self.where_clause)
        self.connection.execute(delete_stmt)

    @abstractmethod
    def association_model(self):
        """Return model class"""

    @abstractmethod
    def build_where_clause(self):
        """Build where clause for filtering records containing nulls instead of associated item ids"""


class UserGroupAssociationNullFix(AssociationNullFix):

    def association_model(self):
        return UserGroupAssociation

    def build_where_clause(self):
        return or_(UserGroupAssociation.user_id == null(), UserGroupAssociation.group_id == null())


class UserRoleAssociationNullFix(AssociationNullFix):

    def association_model(self):
        return UserRoleAssociation

    def build_where_clause(self):
        return or_(UserRoleAssociation.user_id == null(), UserRoleAssociation.role_id == null())


class GroupRoleAssociationNullFix(AssociationNullFix):

    def association_model(self):
        return GroupRoleAssociation

    def build_where_clause(self):
        return or_(GroupRoleAssociation.group_id == null(), GroupRoleAssociation.role_id == null())


class AssociationDuplicateFix(ABC):

    def __init__(self, connection):
        self.connection = connection
        self.assoc_model = self.association_model()
        self.assoc_name = self.assoc_model.__tablename__

    def run(self):
        duplicate_assocs = self.select_duplicate_associations()
        if duplicate_assocs:
            self.delete_duplicate_associations(duplicate_assocs)

    def select_duplicate_associations(self):
        """Retrieve duplicate association records."""
        select_stmt = self.build_duplicate_tuples_statement()
        return self.connection.execute(select_stmt).all()

    @abstractmethod
    def association_model(self):
        """Return model class"""

    @abstractmethod
    def build_duplicate_tuples_statement(self):
        """
        Build select statement returning a list of tuples (item1_id, item2_id) that have counts > 1
        """

    @abstractmethod
    def build_duplicate_ids_statement(self, item1_id, item2_id):
        """
        Build select statement returning a list of ids for duplicate records retrieved via build_duplicate_tuples_statement().
        """

    def delete_duplicate_associations(self, records):
        """
        Delete duplicate association records retaining oldest record in each group of duplicates.
        """
        to_delete = []
        for item1_id, item2_id in records:
            to_delete += self._get_duplicates_to_delete(item1_id, item2_id)
        for id in to_delete:
            delete_stmt = delete(self.assoc_model).where(self.assoc_model.id == id)
            self.connection.execute(delete_stmt)

    def _get_duplicates_to_delete(self, item1_id, item2_id):
        stmt = self.build_duplicate_ids_statement(item1_id, item2_id)
        duplicates = self.connection.scalars(stmt).all()
        # IMPORTANT: we slice to skip the first item ([1:]), which is the oldest record and SHOULD NOT BE DELETED.
        return duplicates[1:]


class UserGroupAssociationDuplicateFix(AssociationDuplicateFix):

    def association_model(self):
        return UserGroupAssociation

    def build_duplicate_tuples_statement(self):
        stmt = (
            select(UserGroupAssociation.user_id, UserGroupAssociation.group_id)
            .group_by(UserGroupAssociation.user_id, UserGroupAssociation.group_id)
            .having(func.count() > 1)
        )
        return stmt

    def build_duplicate_ids_statement(self, user_id, group_id):
        stmt = (
            select(UserGroupAssociation.id)
            .where(UserGroupAssociation.user_id == user_id, UserGroupAssociation.group_id == group_id)
            .order_by(UserGroupAssociation.update_time)
        )
        return stmt


class UserRoleAssociationDuplicateFix(AssociationDuplicateFix):

    def association_model(self):
        return UserRoleAssociation

    def build_duplicate_tuples_statement(self):
        stmt = (
            select(UserRoleAssociation.user_id, UserRoleAssociation.role_id)
            .group_by(UserRoleAssociation.user_id, UserRoleAssociation.role_id)
            .having(func.count() > 1)
        )
        return stmt

    def build_duplicate_ids_statement(self, user_id, role_id):
        stmt = (
            select(UserRoleAssociation.id)
            .where(UserRoleAssociation.user_id == user_id, UserRoleAssociation.role_id == role_id)
            .order_by(UserRoleAssociation.update_time)
        )
        return stmt


class GroupRoleAssociationDuplicateFix(AssociationDuplicateFix):

    def association_model(self):
        return GroupRoleAssociation

    def build_duplicate_tuples_statement(self):
        stmt = (
            select(GroupRoleAssociation.group_id, GroupRoleAssociation.role_id)
            .group_by(GroupRoleAssociation.group_id, GroupRoleAssociation.role_id)
            .having(func.count() > 1)
        )
        return stmt

    def build_duplicate_ids_statement(self, group_id, role_id):
        stmt = (
            select(GroupRoleAssociation.id)
            .where(GroupRoleAssociation.group_id == group_id, GroupRoleAssociation.role_id == role_id)
            .order_by(GroupRoleAssociation.update_time)
        )
        return stmt
