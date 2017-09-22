import connexion

from app.db import dbconn
from app.utils import strip_column_prefix


def get():
    with dbconn() as conn:
        cur = conn.cursor()
        cur.execute('''SELECT pg_name, pg_slug, pg_department FROM zsm_data.product_group''')
        rows = cur.fetchall()
        res = [strip_column_prefix(r._asdict()) for r in rows]
        return res


def add(product_group):
    return connexion.problem(
        status=403, title='Forbidden',
        detail='You are using legacy Service level reporting. Editing/Deleting resources is no longer allowed!')


def delete(pg_slug: str):
    return connexion.problem(
        status=403, title='Forbidden',
        detail='You are using legacy Service level reporting. Editing/Deleting resources is no longer allowed!')
