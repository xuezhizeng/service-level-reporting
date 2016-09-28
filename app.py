#!/usr/bin/env python3

import gevent.monkey
gevent.monkey.patch_all()

import psycogreen.gevent
psycogreen.gevent.patch_psycopg()

import collections
import connexion
import logging
import os
import psycopg2
import psycopg2.pool
from psycopg2.extras import NamedTupleCursor

import slo

database_uri = os.getenv('DATABASE_URI')
# NOTE: we can safely use SimpleConnectionPool instead of ThreadedConnectionPool as we use gevent greenlets
pool = psycopg2.pool.SimpleConnectionPool(1, 10, database_uri, cursor_factory=NamedTupleCursor)


def get_health():
    return 'OK'


def get_service_level_indicators(product, name, time_from=None, time_to=None):
    # TODO: allow filtering by time_from/time_to
    conn = pool.getconn()
    try:
        cur = conn.cursor()
        cur.execute('''SELECT sli_timestamp, sli_value from zsm_data.service_level_indicator
        WHERE sli_product_id = (SELECT p_id FROM zsm_data.product WHERE p_slug = %s) AND sli_name = %s
        AND sli_timestamp >= \'now\'::timestamp - interval \'7 days\'
        ORDER BY 1''', (product, name))
        return cur.fetchall()
    finally:
        pool.putconn(conn)


def post_update(product, name, body):
    kairosdb_url = os.getenv('KAIROSDB_URL')
    conn = pool.getconn()
    try:
        cur = conn.cursor()
        cur.execute('SELECT ds_definition FROM zsm_data.data_source WHERE ds_product_id = (SELECT p_id FROM zsm_data.product WHERE p_slug = %s) AND ds_sli_name = %s', (product, name))
        row = cur.fetchone()
        if not row:
            return 'Not found', 404
        definition, = row

    finally:
        pool.putconn(conn)
    count = slo.process_sli(product, name, definition, kairosdb_url, body.get('start', 5), 'minutes', database_uri)
    return {'count': count}


def strip_column_prefix(d):
    res = {}
    for k, v in d.items():
        res[k.split('_', 1)[1]] = v
    return res


def get_service_level_objectives(product):
    conn = pool.getconn()
    res = []
    try:
        cur = conn.cursor()
        cur.execute('''SELECT slo_id, slo_title
                FROM zsm_data.service_level_objective slo
                JOIN zsm_data.product ON p_id = slo_product_id
                WHERE p_slug = %s''', (product,))
        rows = cur.fetchall()
        for row in rows:
            d = strip_column_prefix(row._asdict())
            cur.execute('SELECT slit_from, slit_to, slit_sli_name, slit_unit FROM zsm_data.service_level_indicator_target WHERE slit_slo_id = %s', (row.slo_id, ))
            targets = cur.fetchall()
            d['targets'] = [strip_column_prefix(r._asdict()) for r in targets]
            res.append(d)
    finally:
        pool.putconn(conn)
    return res


def get_service_level_objective_report(product, report_type):
    conn = pool.getconn()
    res = collections.defaultdict(dict)
    try:
        cur = conn.cursor()
        cur.execute('''SELECT date_trunc(\'day\', sli_timestamp) AS day, sli_name AS name, MIN(sli_value) AS min, AVG(sli_value), MAX(sli_value), COUNT(sli_value),
                (SELECT SUM(CASE b WHEN true THEN 0 ELSE 1 END) FROM UNNEST(array_agg(sli_value BETWEEN COALESCE(slit_from, \'-Infinity\') AND COALESCE(slit_to, \'Infinity\'))) AS dt(b)) AS agg
                FROM zsm_data.service_level_indicator
                JOIN zsm_data.service_level_indicator_target ON slit_sli_name = sli_name
                JOIN zsm_data.service_level_objective ON slo_id = slit_slo_id
                JOIN zsm_data.product ON p_id = slo_product_id AND p_slug = %s
                WHERE sli_timestamp >= \'now\'::timestamp - interval \'7 days\'
                GROUP BY date_trunc(\'day\', sli_timestamp), sli_name''', (product, ))
        rows = cur.fetchall()
        for row in rows:
            res[row.day.isoformat()][row.name] = {'min': row.min, 'avg': row.avg, 'max': row.max, 'count': row.count, 'breaches': row.agg}
    finally:
        pool.putconn(conn)
    return res


logging.basicConfig(level=logging.INFO)
app = connexion.App(__name__)
app.add_api('swagger.yaml')
# set the WSGI application callable to allow using uWSGI:
# uwsgi --http :8080 -w app
application = app.app

if __name__ == '__main__':
    # run our standalone gevent server
    app.run(port=8080, server='gevent')