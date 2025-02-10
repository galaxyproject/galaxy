"""
Manager and Serializer for Users.
"""

import hashlib
import logging
import random
import string
import time
from datetime import datetime
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from markupsafe import escape
from sqlalchemy import (
    and_,
    exc,
    func,
    select,
    true,
)
from sqlalchemy.exc import NoResultFound

from galaxy import (
    exceptions,
    model,
    schema,
    util,
)
from galaxy.config import templates
from galaxy.managers import (
    base,
    deletable,
)
from galaxy.managers.base import combine_lists
from galaxy.model import (
    Job,
    User,
    UserAddress,
    UserQuotaUsage,
)
from galaxy.model.db.user import (
    _cleanup_nonprivate_user_roles,
    get_user_by_email,
    get_user_by_username,
)
from galaxy.security.validate_user_input import (
    VALID_EMAIL_RE,
    validate_email,
    validate_password,
    validate_preferred_object_store_id,
    validate_publicname,
)
from galaxy.structured_app import (
    BasicSharedApp,
    MinimalManagerApp,
)
from galaxy.util.hash_util import new_secure_hash_v2

log = logging.getLogger(__name__)

PASSWORD_RESET_TEMPLATE = """
To reset your Galaxy password for the instance at %s use the following link,
which will expire %s.

%s%s

If you did not make this request, no action is necessary on your part, though
you may want to notify an administrator.

If you're having trouble using the link when clicking it from email client, you
can also copy and paste it into your browser.
"""
TXT_ACTIVATION_EMAIL_TEMPLATE_RELPATH = "mail/activation-email.txt"
HTML_ACTIVATION_EMAIL_TEMPLATE_RELPATH = "mail/activation-email.html"


class UserManager(base.ModelManager, deletable.PurgableManagerMixin):
    foreign_key_name = "user"

    # TODO: there is quite a bit of functionality around the user (authentication, permissions, quotas, groups/roles)
    #   most of which it may be unneccessary to have here

    # TODO: incorp BaseAPIController.validate_in_users_and_groups
    # TODO: incorporate UsesFormDefinitionsMixin?
    def __init__(self, app: BasicSharedApp, app_type="galaxy"):
        self.model_class = app.model.User
        self.app_type = app_type
        super().__init__(app)

    def register(self, trans, email=None, username=None, password=None, confirm=None, subscribe=False):
        """
        Register a new user.
        """
        if not trans.app.config.allow_user_creation and not trans.user_is_admin:
            message = "User registration is disabled.  Please contact your local Galaxy administrator for an account."
            if trans.app.config.error_email_to is not None:
                message += f" Contact: {trans.app.config.error_email_to}"
            return None, message
        if not email or not username or not password or not confirm:
            return None, "Please provide email, username and password."

        email = util.restore_text(email).strip()
        username = util.restore_text(username).strip()
        # We could add a separate option here for enabling or disabling domain validation (DNS resolution test)
        validate_domain = trans.app.config.user_activation_on
        message = "\n".join(
            (
                validate_email(trans, email, validate_domain=validate_domain),
                validate_password(trans, password, confirm),
                validate_publicname(trans, username),
            )
        ).rstrip()

        if message:
            return None, message
        message, status = trans.app.auth_manager.check_registration_allowed(email, username, password, trans.request)
        if message and not trans.user_is_admin:
            return None, message
        if subscribe:
            message = self.send_subscription_email(email)
            if message:
                return None, message
        user = self.create(email=email, username=username, password=password)
        if self.app.config.user_activation_on:
            self.send_activation_email(trans, email, username)
        return user, None

    def create(self, email=None, username=None, password=None, **kwargs):
        """
        Create a new user.
        """
        self._error_on_duplicate_email(email)
        user = self.model_class(email=email)
        if password:
            user.set_password_cleartext(password)
        else:
            user.set_random_password()
        user.username = username
        if self.app.config.user_activation_on:
            user.active = False
        else:
            # Activation is off, every new user is active by default.
            user.active = True
        session = self.session()
        session.add(user)
        try:
            # Creating a private role will commit the session
            self.app.security_agent.create_user_role(user, self.app)
        except exc.IntegrityError as db_err:
            raise exceptions.Conflict(str(db_err))
        return user

    def delete(self, user, flush=True):
        """Mark the given user deleted."""
        if not self.app.config.allow_user_deletion:
            raise exceptions.ConfigDoesNotAllowException(
                "The configuration of this Galaxy instance does not allow admins to delete users."
            )
        super().delete(user, flush=flush)
        self._stop_all_jobs_from_user(user)

    def _stop_all_jobs_from_user(self, user):
        active_jobs = self._get_all_active_jobs_from_user(user)
        session = self.session()
        for job in active_jobs:
            job.mark_deleted(self.app.config.track_jobs_in_database)
        session.commit()

    def _get_all_active_jobs_from_user(self, user: User) -> List[Job]:
        """Get all jobs that are not ready yet and belong to the given user."""
        stmt = select(Job).where(and_(Job.user_id == user.id, Job.state.in_(Job.non_ready_states)))
        jobs = self.session().scalars(stmt)
        return jobs  # type:ignore[return-value]

    def undelete(self, user, flush=True):
        """Remove the deleted flag for the given user."""
        if not self.app.config.allow_user_deletion:
            raise exceptions.ConfigDoesNotAllowException(
                "The configuration of this Galaxy instance does not allow admins to undelete users."
            )
        if user.purged:
            raise exceptions.ItemDeletionException("Purged user cannot be undeleted.")
        super().undelete(user, flush=flush)

    def purge(self, user, flush=True):
        """Purge the given user. They must have the deleted flag already."""
        if not self.app.config.allow_user_deletion:
            raise exceptions.ConfigDoesNotAllowException(
                "The configuration of this Galaxy instance does not allow admins to delete or purge users."
            )
        if not user.deleted:
            raise exceptions.MessageException(f"User '{user.email}' has not been deleted, so they cannot be purged.")
        private_role = self.app.security_agent.get_private_user_role(user)
        if private_role is None:
            raise exceptions.InconsistentDatabase(
                f"User {user.email} private role is missing while attempting to purge deleted user."
            )
        # Delete History
        for active_history in user.active_histories:
            self.session().refresh(active_history)
            for hda in active_history.active_datasets:
                # Delete HistoryDatasetAssociation
                hda.deleted = True
                self.session().add(hda)
            active_history.deleted = True
            self.session().add(active_history)
        # Delete UserGroupAssociations
        for uga in user.groups:
            self.session().delete(uga)
        _cleanup_nonprivate_user_roles(self.session(), user, private_role.id)
        # Delete UserAddresses
        for address in user.addresses:
            self.session().delete(address)
        compliance_log = logging.getLogger("COMPLIANCE")
        compliance_log.info(f"delete-user-event: {user.username}")
        # Maybe there is some case in the future where an admin needs
        # to prove that a user was using a server for some reason (e.g.
        # a court case.) So we make this painfully hard to recover (and
        # not immediately reversable) in line with GDPR, but still
        # leave open the possibility to prove someone was part of the
        # server just in case. By knowing the exact email + approximate
        # time of deletion, one could run through hashes for every
        # second of the surrounding days/weeks.
        pseudorandom_value = str(int(time.time()))
        # Replace email + username with a (theoretically) unreversable
        # hash. If provided with the username we can probably re-hash
        # to identify if it is needed for some reason.
        #
        # Deleting multiple times will re-hash the username/email
        email_hash = new_secure_hash_v2(user.email + pseudorandom_value)
        uname_hash = new_secure_hash_v2(user.username + pseudorandom_value)
        # Redact all roles user has
        for role in user.all_roles():
            if self.app.config.redact_username_during_deletion:
                role.name = role.name.replace(user.username, uname_hash)
                role.description = role.description.replace(user.username, uname_hash)

            if self.app.config.redact_email_during_deletion:
                role.name = role.name.replace(user.email, email_hash)
                role.description = role.description.replace(user.email, email_hash)
            self.session().add(role)
        private_role.name = email_hash
        private_role.description = f"Private Role for {email_hash}"
        self.session().add(private_role)
        # Redact user's email and username
        user.email = email_hash
        user.username = uname_hash
        # Redact user addresses as well
        if self.app.config.redact_user_address_during_deletion:
            stmt = select(UserAddress).where(UserAddress.user_id == user.id)
            for addr in self.session().scalars(stmt):
                addr.desc = new_secure_hash_v2(addr.desc + pseudorandom_value)
                addr.name = new_secure_hash_v2(addr.name + pseudorandom_value)
                addr.institution = new_secure_hash_v2(addr.institution + pseudorandom_value)
                addr.address = new_secure_hash_v2(addr.address + pseudorandom_value)
                addr.city = new_secure_hash_v2(addr.city + pseudorandom_value)
                addr.state = new_secure_hash_v2(addr.state + pseudorandom_value)
                addr.postal_code = new_secure_hash_v2(addr.postal_code + pseudorandom_value)
                addr.country = new_secure_hash_v2(addr.country + pseudorandom_value)
                addr.phone = new_secure_hash_v2(addr.phone + pseudorandom_value)
                self.session().add(addr)
        # Purge the user
        super().purge(user, flush=flush)

    def _error_on_duplicate_email(self, email: str) -> None:
        """
        Check for a duplicate email and raise if found.

        :raises exceptions.Conflict: if any are found
        """
        # TODO: remove this check when unique=True is added to the email column
        if self.by_email(email) is not None:
            raise exceptions.Conflict("Email must be unique", email=email)

    def by_id(self, user_id: int) -> Optional[model.User]:
        return self.app.model.session.get(self.model_class, user_id)

    # ---- filters
    def by_email(self, email: str, filters=None, **kwargs) -> Optional[model.User]:
        """
        Find a user by their email.
        """
        filters = combine_lists(self.model_class.email == email, filters)
        try:
            # TODO: use one_or_none
            return super().one(filters=filters, **kwargs)
        except exceptions.ObjectNotFound:
            return None

    def by_api_key(self, api_key: str, sa_session=None):
        """
        Find a user by API key.
        """
        if self.check_bootstrap_admin_api_key(api_key=api_key):
            return schema.BootstrapAdminUser()
        sa_session = sa_session or self.app.model.session
        try:
            stmt = select(self.app.model.APIKeys).filter_by(key=api_key, deleted=False)
            provided_key = sa_session.execute(stmt).scalar_one()
        except NoResultFound:
            raise exceptions.AuthenticationFailed("Provided API key is not valid.")
        if provided_key.user.deleted:
            raise exceptions.AuthenticationFailed("User account is deactivated, please contact an administrator.")
        sa_session.refresh(provided_key.user)
        newest_key = provided_key.user.api_keys[0]
        if newest_key.key != provided_key.key:
            raise exceptions.AuthenticationFailed("Provided API key has expired.")
        return provided_key.user

    def by_oidc_access_token(self, access_token: str):
        if hasattr(self.app, "authnz_manager") and self.app.authnz_manager:
            user = self.app.authnz_manager.match_access_token_to_user(self.app.model.session, access_token)
            return user
        else:
            return None

    def check_bootstrap_admin_api_key(self, api_key):
        bootstrap_admin_api_key = getattr(self.app.config, "bootstrap_admin_api_key", None)
        if not bootstrap_admin_api_key:
            return False
        # Hash keys to make them the same size, so we can do safe comparison.
        bootstrap_hash = hashlib.sha256(util.smart_str(bootstrap_admin_api_key)).hexdigest()
        provided_hash = hashlib.sha256(util.smart_str(api_key)).hexdigest()
        return util.safe_str_cmp(bootstrap_hash, provided_hash)

    # ---- admin
    def is_admin(self, user: Optional[model.User], trans=None) -> bool:
        """Return True if this user is an admin (or session is authenticated as admin).

        Do not pass trans to simply check if an existing user object is an admin user,
        pass trans when checking permissions.
        """
        if user is None:
            # Anonymous session or master_api_key used, if master_api_key is detected
            # return True.
            return trans and trans.user_is_admin
        return self.app.config.is_admin_user(user)

    def admins(self, filters=None, **kwargs):
        """
        Return a list of admin Users.
        """
        admin_emails = self.app.config.admin_users_list
        filters = combine_lists(self.model_class.email.in_(admin_emails), filters)
        return super().list(filters=filters, **kwargs)

    def error_unless_admin(self, user, msg="Administrators only", **kwargs):
        """
        Raise an error if `user` is not an admin.

        :raises exceptions.AdminRequiredException: if `user` is not an admin.
        """
        # useful in admin only methods
        if not self.is_admin(user, trans=kwargs.get("trans", None)):
            raise exceptions.AdminRequiredException(msg, **kwargs)
        return user

    # ---- anonymous
    def is_anonymous(self, user: Optional[model.User]) -> bool:
        """
        Return True if `user` is anonymous.
        """
        # define here for single point of change and make more readable
        return user is None

    def error_if_anonymous(self, user, msg="Log-in required", **kwargs):
        """
        Raise an error if `user` is anonymous.
        """
        if user is None:
            # TODO: code is correct (401) but should be named AuthenticationRequired (401 and 403 are flipped)
            raise exceptions.AuthenticationFailed(msg, **kwargs)
        return user

    def get_user_by_identity(self, identity):
        """Get user by username or email."""
        user = None
        if VALID_EMAIL_RE.match(identity):
            # VALID_PUBLICNAME and VALID_EMAIL do not overlap, so 'identity' here is an email address
            user = get_user_by_email(self.session(), identity, self.model_class)
            if not user:
                # Try a case-insensitive match on the email
                user = self._get_user_by_email_case_insensitive(self.session(), identity)
        else:
            user = get_user_by_username(self.session(), identity, self.model_class)
        return user

    # ---- current
    def current_user(self, trans):
        # define here for single point of change and make more readable
        # TODO: trans
        return trans.user

    def user_can_do_run_as(self, user) -> bool:
        run_as_users = [u for u in self.app.config.get("api_allow_run_as", "").split(",") if u]
        if not run_as_users:
            return False
        user_in_run_as_users = user and user.email in run_as_users
        # Can do if explicitly in list or master_api_key supplied.
        can_do_run_as = user_in_run_as_users or user.bootstrap_admin_user
        return can_do_run_as

    # ---- preferences
    def preferences(self, user):
        return dict(user.preferences.items())

    # ---- roles and permissions
    def private_role(self, user):
        return self.app.security_agent.get_private_user_role(user)

    def sharing_roles(self, user):
        return self.app.security_agent.get_sharing_roles(user)

    def default_permissions(self, user):
        return self.app.security_agent.user_get_default_permissions(user)

    def quota(self, user, total=False, quota_source_label=None):
        if total:
            return self.app.quota_agent.get_quota_nice_size(user, quota_source_label=quota_source_label)
        return self.app.quota_agent.get_percent(user=user, quota_source_label=quota_source_label)

    def quota_bytes(self, user, quota_source_label: Optional[str] = None):
        return self.app.quota_agent.get_quota(user=user, quota_source_label=quota_source_label)

    def change_password(self, trans, password=None, confirm=None, token=None, id=None, current=None):
        """
        Allows to change a user password with a token.
        """
        if not token and not id:
            return None, "Please provide a token or a user and password."
        if token:
            token_result = trans.sa_session.get(self.app.model.PasswordResetToken, token)
            if not token_result or not token_result.expiration_time > datetime.utcnow():
                return None, "Invalid or expired password reset token, please request a new one."
            user = token_result.user
            message = self.__set_password(trans, user, password, confirm)
            if message:
                return None, message
            token_result.expiration_time = datetime.utcnow()
            trans.sa_session.add(token_result)
            return user, "Password has been changed. Token has been invalidated."
        else:
            if not isinstance(id, int):
                id = self.app.security.decode_id(id)
            user = self.by_id(id)
            if user:
                message = self.app.auth_manager.check_change_password(user, current, trans.request)
                if message:
                    return None, message
                message = self.__set_password(trans, user, password, confirm)
                if message:
                    return None, message
                return user, "Password has been changed."
            else:
                return user, "User not found."

    def __set_password(self, trans, user, password, confirm):
        if not password:
            return "Please provide a new password."
        if user:
            # Validate the new password
            message = validate_password(trans, password, confirm)
            if message:
                return message
            else:
                # Save new password
                user.set_password_cleartext(password)
                # Invalidate all other sessions
                if trans.galaxy_session:
                    stmt = select(self.app.model.GalaxySession).where(
                        and_(
                            self.app.model.GalaxySession.user_id == user.id,
                            self.app.model.GalaxySession.is_valid == true(),
                            self.app.model.GalaxySession.id != trans.galaxy_session.id,
                        )
                    )
                    for other_galaxy_session in trans.sa_session.scalars(stmt):
                        other_galaxy_session.is_valid = False
                        trans.sa_session.add(other_galaxy_session)
                trans.sa_session.add(user)
                trans.sa_session.commit()
                trans.log_event("User change password")
        else:
            return "Failed to determine user, access denied."

    def impersonate(self, trans, user):
        if not trans.app.config.allow_user_impersonation:
            raise exceptions.Message("User impersonation is not enabled in this instance of Galaxy.")
        if user:
            trans.handle_user_logout()
            trans.handle_user_login(user)
        else:
            raise exceptions.Message("Please provide a valid user.")

    def send_activation_email(self, trans, email, username):
        """
        Send the verification email containing the activation link to the user's email.
        """
        activation_token = self.__get_activation_token(trans, email)
        activation_link = trans.url_builder(
            "/user/activate",
            activation_token=activation_token,
            email=escape(email),
            qualified=True,
        )
        template_context = {
            "name": escape(username),
            "user_email": escape(email),
            "date": datetime.utcnow().strftime("%D"),
            "hostname": trans.request.host,
            "activation_url": activation_link,
            "terms_url": self.app.config.terms_url,
            "contact_email": self.app.config.error_email_to,
            "instance_resource_url": self.app.config.instance_resource_url,
            "custom_message": self.app.config.custom_activation_email_message,
            "expiry_days": self.app.config.activation_grace_period,
        }
        body = templates.render(TXT_ACTIVATION_EMAIL_TEMPLATE_RELPATH, template_context, self.app.config.templates_dir)
        html = templates.render(HTML_ACTIVATION_EMAIL_TEMPLATE_RELPATH, template_context, self.app.config.templates_dir)
        to = email
        subject = "Galaxy Account Activation"
        try:
            util.send_mail(self.app.config.email_from, to, subject, body, self.app.config, html=html)
            return True
        except Exception:
            log.debug(body)
            log.exception("Unable to send the activation email.")
            return False

    def __get_activation_token(self, trans, email):
        """
        Check for the activation token. Create new activation token and store it in the database if no token found.
        """
        user = get_user_by_email(trans.sa_session, email, self.app.model.User)
        activation_token = user.activation_token
        if activation_token is None:
            activation_token = util.hash_util.new_secure_hash_v2(str(random.getrandbits(256)))
            user.activation_token = activation_token
            trans.sa_session.add(user)
            trans.sa_session.commit()
        return activation_token

    def send_reset_email(self, trans, payload, **kwd):
        """Reset the user's password. Send an email with token that allows a password change."""
        if self.app.config.smtp_server is None:
            return "Mail is not configured for this Galaxy instance and password reset information cannot be sent. Please contact your local Galaxy administrator."
        email = payload.get("email")
        if not email:
            return "Please provide your email."
        message = validate_email(trans, email, check_dup=False)
        if message:
            return message
        else:
            reset_user, prt = self.get_reset_token(trans, email)
            if prt:
                reset_url = trans.url_builder("/login/start", token=prt.token)
                body = PASSWORD_RESET_TEMPLATE % (
                    trans.app.config.hostname,
                    prt.expiration_time.strftime(trans.app.config.pretty_datetime_format),
                    trans.request.host,
                    reset_url,
                )
                subject = "Galaxy Password Reset"
                try:
                    util.send_mail(trans.app.config.email_from, email, subject, body, self.app.config)
                    trans.sa_session.add(reset_user)
                    trans.sa_session.commit()
                    trans.log_event(f"User reset password: {email}")
                except Exception as e:
                    log.debug(body)
                    return f"Failed to submit email. Please contact the administrator: {util.unicodify(e)}"
        if not reset_user:
            log.warning(f"Failed to produce password reset token. User with email '{email}' not found.")
        return None

    def get_reset_token(self, trans, email):
        reset_user = get_user_by_email(trans.sa_session, email, self.app.model.User)
        if not reset_user and email != email.lower():
            reset_user = self._get_user_by_email_case_insensitive(trans.sa_session, email)
        if reset_user and not reset_user.deleted:
            prt = self.app.model.PasswordResetToken(reset_user)
            trans.sa_session.add(prt)
            trans.sa_session.commit()
            return reset_user, prt
        return None, None

    def send_subscription_email(self, email):
        if self.app.config.smtp_server is None:
            return "Subscribing to the mailing list has failed because mail is not configured for this Galaxy instance. Please contact your local Galaxy administrator."
        else:
            body = (self.app.config.mailing_join_body or "") + "\n"
            to = self.app.config.mailing_join_addr
            frm = email
            subject = self.app.config.mailing_join_subject or ""
            try:
                util.send_mail(frm, to, subject, body, self.app.config)
            except Exception:
                log.exception("Subscribing to the mailing list has failed.")
                return "Subscribing to the mailing list has failed."

    def activate(self, user):
        user.active = True
        self.session().add(user)
        session = self.session()
        session.commit()

    def get_or_create_remote_user(self, remote_user_email):
        """
        Create a remote user with the email remote_user_email and return it
        """
        if not self.app.config.use_remote_user:
            return None
        if getattr(self.app.config, "normalize_remote_user_email", False):
            remote_user_email = remote_user_email.lower()
        user = get_user_by_email(self.session(), remote_user_email, self.app.model.User)
        if user:
            # Ensure a private role and default permissions are set for remote users (remote user creation bug existed prior to 2009)
            self.app.security_agent.get_private_user_role(user, auto_create=True)
            if self.app_type == "galaxy":
                if not user.default_permissions:
                    self.app.security_agent.user_set_default_permissions(user)
                    self.app.security_agent.user_set_default_permissions(user, history=True, dataset=True)
        elif user is None:
            random.seed()
            user = self.app.model.User(email=remote_user_email)
            user.set_random_password(length=12)
            user.external = True
            user.username = username_from_email(self.session(), remote_user_email, self.app.model.User)
            self.session().add(user)
            self.session().commit()
            self.app.security_agent.create_private_user_role(user)
            # We set default user permissions, before we log in and set the default history permissions
            if self.app_type == "galaxy":
                self.app.security_agent.user_set_default_permissions(user)
            # self.log_event( "Automatically created account '%s'", user.email )
        return user

    def _get_user_by_email_case_insensitive(self, session, email):
        stmt = select(self.app.model.User).where(func.lower(self.app.model.User.email) == email.lower()).limit(1)
        return session.scalars(stmt).first()


class UserSerializer(base.ModelSerializer, deletable.PurgableSerializerMixin):
    model_manager_class = UserManager

    def __init__(self, app: MinimalManagerApp):
        """
        Convert a User and associated data to a dictionary representation.
        """
        super().__init__(app)
        self.user_manager = self.manager

        self.default_view = "summary"
        self.add_view("summary", ["id", "email", "username"])
        self.add_view(
            "detailed",
            [
                # 'update_time',
                # 'create_time',
                "is_admin",
                "total_disk_usage",
                "nice_total_disk_usage",
                "quota_percent",
                "quota",
                "quota_bytes",
                "deleted",
                "purged",
                # 'active',
                "preferences",
                # all annotations
                # 'annotations'
                "preferred_object_store_id",
            ],
            include_keys_from="summary",
        )

    def add_serializers(self):
        super().add_serializers()
        deletable.PurgableSerializerMixin.add_serializers(self)

        self.serializers.update(
            {
                "id": self.serialize_id,
                "create_time": self.serialize_date,
                "update_time": self.serialize_date,
                "is_admin": lambda i, k, **c: self.user_manager.is_admin(i),
                "preferences": lambda i, k, **c: self.user_manager.preferences(i),
                "total_disk_usage": lambda i, k, **c: float(i.total_disk_usage),
                "quota_percent": lambda i, k, **c: self.user_manager.quota(i),
                "quota": lambda i, k, **c: self.user_manager.quota(i, total=True),
                "quota_bytes": lambda i, k, **c: self.user_manager.quota_bytes(i),
            }
        )

    def serialize_disk_usage(self, user: model.User) -> List[UserQuotaUsage]:
        usages = user.dictify_usage(self.app.object_store)
        rval: List[UserQuotaUsage] = []
        for usage in usages:
            quota_source_label = usage.quota_source_label
            quota_percent = self.user_manager.quota(user, quota_source_label=quota_source_label)
            quota = self.user_manager.quota(user, total=True, quota_source_label=quota_source_label)
            quota_bytes = self.user_manager.quota_bytes(user, quota_source_label=quota_source_label)
            rval.append(
                UserQuotaUsage(
                    quota_source_label=quota_source_label,
                    total_disk_usage=usage.total_disk_usage,
                    quota_percent=quota_percent,
                    quota=quota,
                    quota_bytes=quota_bytes,
                )
            )
        return rval

    def serialize_disk_usage_for(self, user: model.User, label: Optional[str]) -> UserQuotaUsage:
        usage = user.dictify_usage_for(label)
        quota_source_label = usage.quota_source_label
        quota_percent = self.user_manager.quota(user, quota_source_label=quota_source_label)
        quota = self.user_manager.quota(user, total=True, quota_source_label=quota_source_label)
        quota_bytes = self.user_manager.quota_bytes(user, quota_source_label=quota_source_label)
        return UserQuotaUsage(
            quota_source_label=quota_source_label,
            total_disk_usage=usage.total_disk_usage,
            quota_percent=quota_percent,
            quota=quota,
            quota_bytes=quota_bytes,
        )


class UserDeserializer(base.ModelDeserializer):
    """
    Service object for validating and deserializing dictionaries that
    update/alter users.
    """

    model_manager_class = UserManager

    def add_deserializers(self):
        super().add_deserializers()
        user_deserializers: Dict[str, base.Deserializer] = {
            "active": self.default_deserializer,
            "username": self.deserialize_username,
            "preferred_object_store_id": self.deserialize_preferred_object_store_id,
        }
        self.deserializers.update(user_deserializers)

    def deserialize_preferred_object_store_id(self, item: Any, key: Any, val: Any, trans=None, **context):
        preferred_object_store_id = val
        validation_error = validate_preferred_object_store_id(trans, self.app.object_store, preferred_object_store_id)
        if validation_error:
            raise base.ModelDeserializingError(validation_error)
        return self.default_deserializer(item, key, preferred_object_store_id, **context)

    def deserialize_username(self, item, key, username, trans=None, **context):
        # TODO: validate_publicname requires trans and should(?) raise exceptions
        # move validation to UserValidator and use self.app, exceptions instead
        validation_error = validate_publicname(trans, username, user=item)
        if validation_error:
            raise base.ModelDeserializingError(validation_error)
        return self.default_deserializer(item, key, username, trans=trans, **context)


class CurrentUserSerializer(UserSerializer):
    model_manager_class = UserManager

    def serialize(self, user, keys, **kwargs):
        """
        Override to return at least some usage info if user is anonymous.
        """
        kwargs["current_user"] = user
        if self.user_manager.is_anonymous(user):
            return self.serialize_current_anonymous_user(user, keys, **kwargs)
        return super(UserSerializer, self).serialize(user, keys, **kwargs)

    def serialize_current_anonymous_user(self, user, keys, trans=None, **kwargs):
        # use the current history if any to get usage stats for trans' anonymous user
        # TODO: might be better as sep. Serializer class
        usage = 0
        percent = None

        history = trans.history
        if history:
            usage = self.app.quota_agent.get_usage(trans, history=trans.history)
            percent = self.app.quota_agent.get_percent(trans=trans, usage=usage)

        # a very small subset of keys available
        values = {
            "id": None,
            "total_disk_usage": float(usage),
            "nice_total_disk_usage": util.nice_size(usage),
            "quota_percent": percent,
        }
        serialized = {}
        for key in keys:
            if key in values:
                serialized[key] = values[key]
        return serialized


class AdminUserFilterParser(base.ModelFilterParser, deletable.PurgableFiltersMixin):
    model_manager_class = UserManager
    model_class = model.User

    def _add_parsers(self):
        super()._add_parsers()
        deletable.PurgableFiltersMixin._add_parsers(self)

        # PRECONDITION: user making the query has been verified as an admin
        self.orm_filter_parsers.update(
            {
                "email": {"op": ("eq", "contains", "like")},
                "username": {"op": ("eq", "contains", "like")},
                "active": {"op": ("eq")},
                "disk_usage": {"op": ("le", "ge")},
            }
        )

        self.fn_filter_parsers.update({})


def username_from_email(session, email, model_class=User):
    """Get next available username generated based on email"""
    username = email.split("@", 1)[0].lower()
    username = filter_out_invalid_username_characters(username)
    if username_exists(session, username, model_class):
        username = generate_next_available_username(session, username, model_class)
    return username


def filter_out_invalid_username_characters(username):
    """Replace invalid characters in username"""
    for char in [x for x in username if x not in f"{string.ascii_lowercase + string.digits}-."]:
        username = username.replace(char, "-")
    return username


def username_exists(session, username: str, model_class=User):
    return bool(get_user_by_username(session, username, model_class))


def generate_next_available_username(session, username, model_class=User):
    """Generate unique username; user can change it later"""
    i = 1
    while session.execute(select(model_class).where(model_class.username == f"{username}-{i}")).first():
        i += 1
    return f"{username}-{i}"
