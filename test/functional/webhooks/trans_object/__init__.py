def main(trans, webhook, params):
    if trans.user:
        user = trans.user.username
    else:
        user = "No user is logged in."
    return {"username": user}
