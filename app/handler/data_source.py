import connexion

from app.db import dbconn
from app.utils import strip_column_prefix


def get(product):
    with dbconn() as conn:
        cur = conn.cursor()
        cur.execute('''
            SELECT p.p_name, p.p_slug, ds.ds_sli_name, ds.ds_definition FROM zsm_data.product AS p,
            zsm_data.data_source AS ds  WHERE p.p_id=ds.ds_product_id AND p.p_slug = %s
        ''', (product,))
        rows = cur.fetchall()
        res = [strip_column_prefix(r._asdict()) for r in rows]
    return res


def add(product, data_source):
    return connexion.problem(
        status=403, title='Forbidden',
        detail='You are using legacy Service level reporting. Editing/Deleting resources is no longer allowed!')


def delete(product, sli_name):
    return connexion.problem(
        status=403, title='Forbidden',
        detail='You are using legacy Service level reporting. Editing/Deleting resources is no longer allowed!')
