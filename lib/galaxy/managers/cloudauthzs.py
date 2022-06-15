"""
Manager and (de)serializer for cloud authorizations (cloudauthzs).
"""

import logging
from typing import Dict

from galaxy import model
from galaxy.exceptions import InternalServerError
from galaxy.managers import (
    base,
    sharable,
)

log = logging.getLogger(__name__)


class CloudAuthzManager(sharable.SharableModelManager):

    model_class = model.CloudAuthz
    foreign_key_name = "cloudauthz"


class CloudAuthzsSerializer(base.ModelSerializer):
    """
    Interface/service object for serializing cloud authorizations (cloudauthzs) into dictionaries.
    """

    model_manager_class = CloudAuthzManager

    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        self.cloudauthzs_manager = self.manager

        self.default_view = "summary"
        self.add_view(
            "summary",
            [
                "id",
                "model_class",
                "user_id",
                "provider",
                "config",
                "authn_id",
                "last_update",
                "last_activity",
                "create_time",
                "description",
            ],
        )

    def add_serializers(self):
        super().add_serializers()

        # Arguments of the following lambda functions:
        # i  : an instance of galaxy.model.CloudAuthz.
        # k  : serialized dictionary key (e.g., 'model_class', 'provider').
        # **c: a dictionary containing 'trans' and 'user' objects.
        serializers: Dict[str, base.Serializer] = {
            "id": lambda item, key, **context: self.app.security.encode_id(item.id),
            "model_class": lambda item, key, **context: "CloudAuthz",
            "user_id": lambda item, key, **context: self.app.security.encode_id(item.user_id),
            "provider": lambda item, key, **context: str(item.provider),
            "config": lambda item, key, **context: item.config,
            "authn_id": lambda item, key, **context: self.app.security.encode_id(item.authn_id)
            if item.authn_id
            else None,
            "last_update": lambda item, key, **context: str(item.last_update),
            "last_activity": lambda item, key, **context: str(item.last_activity),
            "create_time": lambda item, key, **context: item.create_time.isoformat(),
            "description": lambda item, key, **context: str(item.description),
        }
        self.serializers.update(serializers)


class CloudAuthzsDeserializer(base.ModelDeserializer):
    """
    Service object for validating and deserializing dictionaries that
    update/alter cloudauthz configurations.
    """

    model_manager_class = CloudAuthzManager

    def add_deserializers(self):
        super().add_deserializers()
        self.deserializers.update(
            {
                "authn_id": self.deserialize_and_validate_authn_id,
                "provider": self.default_deserializer,
                "config": self.default_deserializer,
                "description": self.default_deserializer,
            }
        )

    def deserialize_and_validate_authn_id(self, item, key, val, **context):
        """
        Deserializes an authentication ID (authn_id), and asserts if the
        current user can assume that authentication.

        :type  item:    galaxy.model.CloudAuthz
        :param item:    an instance of cloudauthz

        :type  key:     string
        :param key:     `authn_id` attribute of the cloudauthz object (i.e., the `item` param).

        :type  val:     string
        :param val:     the value of `authn_id` attribute of the cloudauthz object (i.e., the `item` param).

        :type  context: dict
        :param context: a dictionary object containing Galaxy `trans`.

        :rtype:         string
        :return:        decoded authentication ID.
        """

        decoded_authn_id = self.app.security.decode_id(val, object_name="authz")

        trans = context.get("trans")
        if trans is None:
            log.debug("Not found expected `trans` when deserializing CloudAuthz.")
            raise InternalServerError

        try:
            trans.app.authnz_manager.can_user_assume_authn(trans, decoded_authn_id)
        except Exception as e:
            raise e

        return decoded_authn_id
