#!/usr/bin/env python
"""
Collect and report statistics on job run times
"""
from __future__ import print_function

import re
import sys
import argparse

try:
    import configparser
except:
    import ConfigParser as configparser

import numpy
import psycopg2
from sqlalchemy.engine import url


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Generate walltime statistics')
    parser.add_argument('tool_id', help='Tool to collect stats about')
    parser.add_argument('--like',
                        action='store_true',
                        default=False,
                        help='Use SQL `LIKE` operator to find '
                             'a shed-installed tool using the tool\'s '
                             '"short" id')
    parser.add_argument('-c', '--config', help='Galaxy Config file')
    parser.add_argument('-d', '--debug',
                        action='store_true',
                        default=False,
                        help='Print extra info')
    parser.add_argument('-m', '--min',
                        type=int,
                        default=-1,
                        help='Ignore runtimes less than m seconds')
    parser.add_argument('-M', '--max',
                        type=int,
                        default=-1,
                        help='Ignore runtimes greater than M seconds')
    parser.add_argument('-u', '--user',
                        help='Return stats for only this user')
    args = parser.parse_args()

    if args.like and '/' in args.tool_id:
        print('ERROR: Do not use --like with a tool shed tool id (the tool '
              'id should not contain `/` characters)')
        sys.exit(2)

    if args.config:
        cp = configparser.ConfigParser()
        cp.readfp(open(args.config))
        uri = cp.get('app:main', 'database_connection')
        names = { 'database' : 'dbname' }
        args.connect_args = url.make_url(uri).translate_connect_args(**names)
    else:
        args.connect_args = {}

    if args.debug:
        print('Got options:')
        for i in vars(args).items():
            print('%s: %s' % i)

    return args

def query(tool_id=None, user=None, like=None, connect_args=None, debug=False,
          min=-1, max=-1, **kwargs):

    connect_arg_str = ''
    for k, v in connect_args.items():
        connect_arg_str += '%s=%s' % (k, v)

    pc = psycopg2.connect(connect_arg_str)
    cur = pc.cursor()

    if user:
        try:
            user_id = int(user)
        except:
            if '@' not in user:
                field = 'username'
            else:
                field = 'email'
            sql = 'SELECT id FROM galaxy_user WHERE %s = %s' % (field, '%s')
            cur.execute(sql, (user,))
            if debug:
                print('Executed:')
                print(cur.query)
            row = cur.fetchone()
            if row:
                user_id = row[0]
            else:
                print('Invalid user: %s' % user)
                sys.exit(1)

    if like:
        query_tool_id = '%%/%s/%%' % tool_id
    elif '/' in tool_id and not re.match('\d+\.\d+', tool_id.split('/')[-1]):
        query_tool_id = '%s%%' % tool_id
        like = True
    else:
        query_tool_id = tool_id

    sql_args = [query_tool_id]

    sql = """
        SELECT ctimes[1] - ctimes[2] AS delta
        FROM (SELECT jsh.job_id,
                     array_agg(jsh.create_time ORDER BY jsh.create_time DESC) AS ctimes
              FROM job_state_history jsh
              JOIN job j ON jsh.job_id = j.id
              WHERE jsh.state IN ('running','ok')
    """

    if like:
        sql += """
              AND j.tool_id LIKE %s
        """
    else:
        sql += """
              AND j.tool_id = %s
        """

    if user:
        sql += """
              AND j.user_id = %s
        """
        sql_args.append(user_id)

    sql += """
              GROUP BY jsh.job_id) AS t_arrs
    """

    if min > 0 and max > 0:
        sql += """
        WHERE ctimes[1] - ctimes[2] > interval %s
            AND ctimes[1] - ctimes[2] < interval %s
        """
        sql_args.append('%s seconds' % min)
        sql_args.append('%s seconds' % max)
    elif min > 0:
        sql += """
        WHERE ctimes[1] - ctimes[2] > interval %s
        """
        sql_args.append('%s seconds' % min)
    elif max > 0:
        sql += """
        WHERE ctimes[1] - ctimes[2] < interval %s
        """
        sql_args.append('%s seconds' % max)

    cur.execute(sql, sql_args)
    if debug:
        print('Executed:')
        print(cur.query)
    print('Query returned %d rows' % cur.rowcount)

    times = numpy.array([ r[0].total_seconds() for r in cur if r[0] ])

    print('Collected %d times' % times.size)

    if times.size == 0:
        return

    if user:
        print('Displaying statistics for user %s' % user)

    stats = (('Mean runtime', numpy.mean(times)),
             ('Standard deviation', numpy.std(times)))

    for name, seconds in stats:
        hours, minutes = nice_times(seconds)
        msg = name + ' is %0.0f seconds' % seconds
        if minutes:
            msg += ' (=%0.2f minutes)' % minutes
        if hours:
            msg += ' (=%0.2f hours)' % hours
        print(msg)

def nice_times(seconds):
    if seconds < 60*60:
        hours = None
        if seconds < 60:
            minutes = None
        else:
            minutes = seconds / 60
    else:
        minutes = seconds / 60
        hours = seconds / 60 / 60
    return hours, minutes

def main():
    args = parse_arguments()
    query(**vars(args))


if __name__ == '__main__':
    main()
