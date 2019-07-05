from Crypto.Cipher import Blowfish

from galaxy.util import smart_str


def encode_dataset_user(trans, dataset, user):
    # encode dataset id as usual
    # encode user id using the dataset create time as the key
    dataset_hash = trans.security.encode_id(dataset.id)
    if user is None:
        user_hash = 'None'
    else:
        user_hash = str(user.id)
        # Pad to a multiple of 8 with leading "!"
        user_hash = ("!" * (8 - len(user_hash) % 8)) + user_hash
        cipher = Blowfish.new(smart_str(dataset.create_time), mode=Blowfish.MODE_ECB)
        user_hash = cipher.encrypt(user_hash).encode('hex')
    return dataset_hash, user_hash


def decode_dataset_user(trans, dataset_hash, user_hash):
    # decode dataset id as usual
    # decode user id using the dataset create time as the key
    dataset_id = trans.security.decode_id(dataset_hash)
    dataset = trans.sa_session.query(trans.app.model.HistoryDatasetAssociation).get(dataset_id)
    assert dataset, "Bad Dataset id provided to decode_dataset_user"
    if user_hash in [None, 'None']:
        user = None
    else:
        cipher = Blowfish.new(smart_str(dataset.create_time), mode=Blowfish.MODE_ECB)
        user_id = cipher.decrypt(user_hash.decode('hex')).lstrip("!")
        user = trans.sa_session.query(trans.app.model.User).get(int(user_id))
        assert user, "A Bad user id was passed to decode_dataset_user"
    return dataset, user
