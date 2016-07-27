from miracle.models import User


def delete_data(task, user):
    with task.db.session() as session:
        session.query(User).filter(User.token == user).delete()
    return True


def main(task, user, _delete_data=True):
    if not user:
        return False

    # Testing hooks.
    if not _delete_data:
        return True

    if _delete_data is True:  # pragma: no cover
        _delete_data = delete_data

    return _delete_data(task, user)
