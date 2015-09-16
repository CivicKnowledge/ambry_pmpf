# -*- coding: utf-8 -*-
from decimal import Decimal

import psycopg2

from fs.opener import fsopendir

from ambry_sources import get_source
from ambry_sources.med.postgresql import add_partition, _table_name
from ambry_sources.mpf import MPRowsFile

from tests import PostgreSQLTestBase, TestBase


class Test(TestBase):

    def test_creates_foreign_data_table_for_simple_fixed_mpr(self):
        # build rows reader
        cache_fs = fsopendir(self.setup_temp_dir())
        sources = self.load_sources()
        spec = sources['simple_fixed']
        s = get_source(spec, cache_fs)
        partition = MPRowsFile(cache_fs, spec.name).load_rows(s)

        # first make sure file not changed.
        expected_names = ['id', 'uuid', 'int', 'float']
        expected_types = ['str', 'str', 'str', 'float']
        self.assertEqual(sorted([x['name'] for x in partition.schema]), sorted(expected_names))
        self.assertEqual(sorted([x['type'] for x in partition.schema]), sorted(expected_types))

        try:
            # create foreign data table
            PostgreSQLTestBase._create_postgres_test_db()
            conn = psycopg2.connect(**PostgreSQLTestBase.pg_test_db_data)

            try:
                with conn.cursor() as cursor:
                    # we have to close opened transaction.
                    cursor.execute('commit;')
                    add_partition(cursor, partition)

                # try to query just added partition foreign data table.
                with conn.cursor() as cursor:
                    table_name = _table_name(partition)

                    # count all rows
                    query = 'SELECT count(*) FROM {};'.format(table_name)
                    cursor.execute(query)
                    result = cursor.fetchall()
                    self.assertEqual(result, [(10000,)])

                    # check first row
                    cursor.execute('SELECT id, uuid, int, float FROM {} LIMIT 1;'.format(table_name))
                    result = cursor.fetchall()
                    self.assertEqual(len(result), 1)
                    expected_first_row = ('1eb385', 'c36-9298-4427-8925-fe09294dbd 30',
                                          '99.', Decimal('734691532'))
                    self.assertEqual(result[0], expected_first_row)

            finally:
                conn.close()
        finally:
            PostgreSQLTestBase._drop_postgres_test_db()
