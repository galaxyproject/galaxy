from galaxy.security.idencoding import IdEncodingHelper


def encode_dataset_user(trans, dataset, user):
    # encode dataset id as usual
    # encode user id using the dataset create time as the key
    dataset_hash = trans.security.encode_id(dataset.id)
    if user is None:
        user_hash = "None"
    else:
        security = IdEncodingHelper(id_secret=dataset.create_time)
        user_hash = security.encode_id(user.id)
    return dataset_hash, user_hash


def decode_dataset_user(trans, dataset_hash, user_hash):
    # decode dataset id as usual
    # decode user id using the dataset create time as the key
    dataset_id = trans.security.decode_id(dataset_hash)
    dataset = trans.sa_session.get(trans.app.model.HistoryDatasetAssociation, dataset_id)
    assert dataset, "Bad Dataset id provided to decode_dataset_user"
    if user_hash in [None, "None"]:
        user = None
    else:
        security = IdEncodingHelper(id_secret=dataset.create_time)
        user_id = security.decode_id(user_hash)
        user = trans.sa_session.get(trans.app.model.User, user_id)
        assert user, "A Bad user id was passed to decode_dataset_user"
    return dataset, user
