import connexion

from app.db import dbconn
from app.utils import strip_column_prefix


def get(product):
    res = []
    with dbconn() as conn:
        cur = conn.cursor()
        cur.execute('''SELECT slo_id, slo_title
                FROM zsm_data.service_level_objective slo
                JOIN zsm_data.product ON p_id = slo_product_id
                WHERE p_slug = %s''', (product,))
        rows = cur.fetchall()
        for row in rows:
            d = strip_column_prefix(row._asdict())
            cur.execute(
                'SELECT slit_from, slit_to, slit_sli_name, slit_unit FROM '
                'zsm_data.service_level_indicator_target WHERE slit_slo_id = %s',
                (row.slo_id,))
            targets = cur.fetchall()
            d['targets'] = [strip_column_prefix(r._asdict()) for r in targets]
            res.append(d)
    return res


def add(product, slo):
    return connexion.problem(
        status=403, title='Forbidden',
        detail='You are using legacy Service level reporting. Editing/Deleting resources is no longer allowed!')


def delete(slo_id):
    return connexion.problem(
        status=403, title='Forbidden',
        detail='You are using legacy Service level reporting. Editing/Deleting resources is no longer allowed!')
