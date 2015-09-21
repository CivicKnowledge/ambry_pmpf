# -*- coding: utf-8 -*-

import unittest

from fs.opener import fsopendir

import pytest

from ambry_sources import get_source
from ambry_sources.mpf import MPRowsFile

from tests import TestBase


class BasicTestSuite(TestBase):
    """Basic test cases."""

    @unittest.skip('Useful for debugging, but doesnt add test coverage')
    def test_just_download(self):
        """Just check that all of the sources can be downloaded without exceptions"""

        cache_fs = fsopendir('temp://')

        sources = self.load_sources()

        for source_name, spec in sources.items():
            try:
                s = get_source(spec, cache_fs)

                for i, row in enumerate(s):
                    if i > 10:
                        break
            except Exception as exc:
                raise AssertionError('Failed to download {} source because of {} error.'
                                     .format(s.url, exc))

    @unittest.skip('Useful for debugging, but doesnt add test coverage')
    def test_just_load(self):
        """Just check that all of the sources can be loaded without exceptions"""

        cache_fs = fsopendir('temp://')

        sources = self.load_sources()

        for source_name, spec in sources.items():

            s = get_source(spec, cache_fs)

            print spec.name

            f = MPRowsFile(cache_fs, spec.name)

            if f.exists:
                f.remove()

            with f.writer as w:
                w.load_rows(s)

            with f.reader as r:
                print r.headers

    #@unittest.skip('Useful for debugging, but doesnt add test coverage')
    def test_full_load(self):
        """Just check that all of the sources can be loaded without exceptions"""

        cache_fs = fsopendir('temp://')

        sources = self.load_sources()

        for source_name, spec in sources.items():

            s = get_source(spec, cache_fs)

            print spec.name

            f = MPRowsFile(cache_fs, spec.name)

            if f.exists:
                f.remove()

            f.load_rows(s)

            with f.reader as r:
                print r.headers


    def test_fixed(self):
        cache_fs = fsopendir(self.setup_temp_dir())
        sources = self.load_sources()
        spec = sources['simple_fixed']
        s = get_source(spec, cache_fs)
        f = MPRowsFile(cache_fs, spec.name).load_rows(s)
        self.assertEqual(f.headers, ['id', 'uuid', 'int', 'float'])

    def test_type_intuit(self):
        """Just check that all of the sources can be downloaded without exceptions"""
        from ambry_sources.intuit import TypeIntuiter

        cache_fs = fsopendir(self.setup_temp_dir())
        sources = self.load_sources()
        spec = sources['simple_fixed']
        s = get_source(spec, cache_fs)

        f = MPRowsFile(cache_fs, spec.name)

        with f.writer as w:
            w.load_rows(s)

        with f.reader as r:
            ti = TypeIntuiter().process_header(r.headers).run(r.rows, r.n_rows)

        with f.writer as w:
            w.set_types(ti)

        with f.reader as w:
            for col in w.columns:
                print col.pos, col.name, col.type

    def test_row_intuit(self):
        """Check that the sources can be loaded and analyzed without exceptions and that the
        guesses for headers and start are as expected"""

        from ambry_sources.intuit import RowIntuiter

        cache_fs = fsopendir('temp://')
        #cache_fs = fsopendir('/tmp/ritest/')

        sources = self.load_sources('sources-non-std-headers.csv')

        for source_name, spec in sources.items():
            print source_name
            s = get_source(spec, cache_fs)
            ri = RowIntuiter().run(s)

            self.assertEqual(
                spec.expect_headers,
                ','.join(str(e) for e in ri.header_lines),
                'Headers of {} source does not match to row intuiter'.format(spec.name))
            self.assertEqual(
                spec.expect_start, ri.start_line,
                'Start line of {} source does not match to row intuiter start line.'.format(spec.name))

    def test_row_load_intuit(self):
        """Check that the soruces can be loaded and analyzed without exceptions and that the
        guesses for headers and start are as expected"""

        from itertools import ifilter, islice

        cache_fs = fsopendir('temp://')
        cache_fs.makedir('/mpr')
        cache_fs = fsopendir('/tmp/ritest/')

        sources = self.load_sources('sources-non-std-headers.csv')

        for source_name, spec in sources.items():

            #if source_name != 'ed_cohort': continue

            s = get_source(spec, cache_fs)

            print source_name

            f = MPRowsFile(cache_fs, '/mpr/'+source_name)

            if f.exists:
                f.remove()

            f.load_rows(s, intuit_type=False, run_stats=False)

            self.assertEqual(f.info['data_start_row'], spec.expect_start)

            with f.reader as r:
                # First row, marked with metadata, that is marked as a data row
                m1, row1 = next(ifilter(lambda e: e[0][2] == 'D', r.meta_raw))

            with f.reader as r:
                # First row
                row2 = next(r.rows)

            with f.reader as r:
                # First row proxy
                row3 = next(iter(r)).row

            self.assertEqual(row1, row2)
            self.assertEqual(row1, row3)

            with f.reader as r:
                raw_rows = list(islice(r.raw,None,40))

            self.assertEqual(row2, raw_rows[f.info['data_start_row']])


    def test_headers(self):

        fs = fsopendir('mem://')

        df = MPRowsFile(fs, 'foobar')

        with df.writer as w:

            schema = lambda row, col: w.meta['schema'][row][col]

            w.headers = list('abcdefghi')

            self.assertEqual('a', schema(1, 1))
            self.assertEqual('e', schema(5, 1))
            self.assertEqual('i', schema(9, 1))

            for h in w.columns:
                h.description = "{}-{}".format(h.pos, h.name)

            self.assertEqual('1-a', schema(1, 3))
            self.assertEqual('5-e', schema(5, 3))
            self.assertEqual('9-i', schema(9, 3))

            w.column(1).description  = 'one'
            w.column(2).description = 'two'
            w.column('c').description = 'C'
            w.column('d')['description'] = 'D'

            self.assertEqual('one', schema(1,3))
            self.assertEqual('two', schema(2, 3))
            self.assertEqual('C', schema(3, 3))
            self.assertEqual('D', schema(4, 3))

        with df.reader as r:
            schema = lambda row, col: r.meta['schema'][row][col]

            self.assertEqual([u'a', u'b', u'c', u'd', u'e', u'f', u'g', u'h', u'i'], r.headers)

            self.assertEqual('one', schema(1, 3))
            self.assertEqual('two', schema(2, 3))
            self.assertEqual('C', schema(3, 3))
            self.assertEqual('D', schema(4, 3))


    @pytest.mark.slow
    def test_datafile_read_write(self):
        from fs.opener import fsopendir
        import datetime
        from random import randint, random
        from contexttimer import Timer
        from uuid import uuid4

        fs = fsopendir('mem://')

        # fs = fsopendir('/tmp/pmpf')

        N = 50000

        # Basic read/ write tests.

        def rand_date_a():
            return datetime.date(randint(2000, 2015), randint(1, 12), 10)

        epoch = datetime.date(1970, 1, 1)

        def rand_date_b():
            return (datetime.date(randint(2000, 2015), randint(1, 12), 10) - epoch).total_seconds()

        row = lambda: (None, 1, random(), str(uuid4()), rand_date_b(), rand_date_b() )

        headers = list('abcdefghi')[:len(row())]

        rows = [row() for i in range(N)]

        def write_large_blocks():

            df = MPRowsFile(fs, 'foobar')

            if df.exists:
                df.remove()

            with Timer() as t, df.writer as w:
                w.headers = headers
                w.insert_rows(rows)

            print "MSGPack write ", float(N) / t.elapsed, w.n_rows

        def write_small_blocks():
            df = MPRowsFile(fs, 'foobar')

            if df.exists:
                df.remove()

            with Timer() as t, df.writer as w:

                for i in range(N):
                    w.headers = headers
                    w.insert_row(rows[i])

            print "MSGPack write ", float(N) / t.elapsed, w.n_rows

        write_large_blocks()

        return

        write_small_blocks()

        df = MPRowsFile(fs, 'foobar')

        with Timer() as t:
            count = 0
            i = 0
            s = 0

            r = df.reader

            for i, row in enumerate(r):
                count += 1


            r.close()

        print "MSGPack read  ", float(N) / t.elapsed, i, count, s

        with Timer() as t:
            count = 0

            r = df.reader

            for row in r.rows:

                count += 1

            r.close()

        print "MSGPack rows  ", float(N) / t.elapsed

        with Timer() as t:
            count = 0

            r = df.reader

            for row in r.raw:
                count += 1

            r.close()

        print "MSGPack raw   ", float(N) / t.elapsed

    def x_test_mpr_meta(self):

        # Saving code for later.
        r = None
        df = None

        self.assertEqual('blah blah', r.meta['source']['url'])

        w = df.writer

        w.meta['source']['url'] = 'bingo'

        w.close()

        r = df.reader

        self.assertEqual('bingo', r.meta['source']['url'])

    def generate_rows(self, N):
        import datetime
        import string

        rs = string.ascii_letters

        row = lambda x: [x, x * 2, x % 17, rs[x % 19:x % 19 + 20],
                         datetime.date(2000 + x % 15, 1 + x % 12, 10),
                         datetime.date(2000 + (x + 1) % 15, 1 + (x + 1) % 12, 10)]

        headers = list('abcdefghi')[:len(row(0))]

        rows = [row(i) for i in range(1, N+1)]

        return rows, headers

    def test_stats(self):
        """Check that the soruces can be loaded and analyzed without exceptions and that the
        guesses for headers and start are as expected"""

        from contexttimer import Timer

        cache_fs = fsopendir('temp://')
        # cache_fs = fsopendir('/tmp/ritest/')

        sources = self.load_sources('sources-non-std-headers.csv')

        for source_name, spec in sources.items():

            s = get_source(spec, cache_fs)

            # if source_name != 'immunize': continue

            print spec.name, spec.url

            with Timer() as t:
                f = MPRowsFile(cache_fs, source_name).load_rows(s, spec, run_stats=True)

            with f.reader as r:
                print 'Loaded ', r.n_rows, float(r.n_rows) / t.elapsed, 'rows/sec'

            # with f.reader as r:
            #    stats = r.meta['stats']
            #    print [ sd['mean'] for col_name, sd in r.meta['stats'].items() ]

    def test_datafile(self):
        """
        Test Loading and interating over data files, exercising the three header cases, and the use
        of data start and end lines.

        :return:
        """
        from itertools import islice

        N = 500

        rows, headers = self.generate_rows(N)

        def first_row_header(data_start_row=None, data_end_row=None):

            # Normal Headers
            f = MPRowsFile('mem://frh')
            w = f.writer

            w.columns = headers

            for row in rows:
                w.insert_row(row)

            if data_start_row is not None:
                w.data_start_row = data_start_row

            if data_end_row is not None:
                w.data_end_row = data_end_row

            w.close()

            self.assertEqual((u'a', u'b', u'c', u'd', u'e', u'f'), tuple(w.parent.reader.headers))

            w.parent.reader.close()

            return f

        def no_header(data_start_row=None, data_end_row=None):

            # No header, column labels.
            f = MPRowsFile('mem://nh')
            w = f.writer

            for row in rows:
                w.insert_row(row)

            if data_start_row is not None:
                w.data_start_row = data_start_row

            if data_end_row is not None:
                w.data_end_row = data_end_row

            w.close()

            self.assertEqual(['col1', 'col2', 'col3', 'col4', 'col5', 'col6'], w.parent.reader.headers)

            w.parent.reader.close()

            return f

        def schema_header(data_start_row=None, data_end_row=None):
            # Set the schema
            f = MPRowsFile('mem://sh')
            w = f.writer

            w.headers = [ 'x' + str(e) for e in range(len(headers))]

            for row in rows:
                w.insert_row(row)

            if data_start_row is not None:
                w.data_start_row = data_start_row

            if data_end_row is not None:
                w.data_end_row = data_end_row

            w.close()

            self.assertEqual((u'x0', u'x1', u'x2', u'x3', u'x4', u'x5'),tuple(w.parent.reader.headers))

            w.parent.reader.close()

            return f

        # Try a few header start / data start values.

        for ff in (first_row_header, schema_header, no_header):
            print '===', ff
            f = ff()

            with f.reader as r:
                l = list(r.rows)

                self.assertEqual(N, len(l))

            with f.reader as r:
                # Check that the first row value starts at one and goes up from there.
                map(lambda f: self.assertEqual(f[0], f[1][0]), enumerate(islice(r.rows, 5), 1))

        for ff in (first_row_header, schema_header, no_header):
            print '===', ff
            data_start_row = 5
            data_end_row = 15
            f = ff(data_start_row, data_end_row)

            with f.reader as r:
                l = list(r.rows)
                self.assertEqual(11, len(l))


    def test_spec_load(self):
        """Test that setting a SourceSpec propertly sets the header_lines data start position"""

        from ambry_sources.sources import SourceSpec
        import string

        rs = string.ascii_letters

        n = 500

        rows, headers = self.generate_rows(n)

        blank = ['' for e in rows[0]]

        # Append a complex header, to give the RowIntuiter something to do.
        rows = [
            ['Dataset Title'] + blank[1:],
            blank,
            blank,
            [rs[i] for i, e in enumerate(rows[0])],
            [rs[i+1] for i, e in enumerate(rows[0])],
            [rs[i+2] for i, e in enumerate(rows[0])],
        ] + rows

        f = MPRowsFile('mem://frh').load_rows(rows)

        d = f.info

        self.assertEqual(6, d['data_start_row'])
        self.assertEqual(506, d['data_end_row'])
        self.assertEqual([3, 4, 5], d['header_rows'])
        self.assertEqual([u'a_b_c', u'b_c_d', u'c_d_e', u'd_e_f', u'e_f_g', u'f_g_h'], d['headers'])

        f = MPRowsFile('mem://frh').load_rows(rows, SourceSpec(None, header_lines=(3, 4), start_line=5))

        d = f.info

        self.assertEqual(5, d['data_start_row'])
        self.assertEqual(506, d['data_end_row'])
        self.assertEqual([3, 4], d['header_rows'])
        self.assertEqual([u'a_b', u'b_c', u'c_d', u'd_e', u'e_f', u'f_g'], d['headers'])
