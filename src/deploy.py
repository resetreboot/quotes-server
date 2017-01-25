#!/usr/bin/env python

#   This file is part of Quotes Server.
#
#   Quotes Server is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   Quotes Server is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with Quotes Server.  If not, see <http://www.gnu.org/licenses/>.


import sys
import sqlite3
import uuid

from users import hash_pwd

VERSION = 2
SUBVERSION = 0
SUBSUBVERSION = 0


def create_db(c):
    """
    Creates the database from scratch
    """
    c.executescript("""
                    PRAGMA foreign_keys = ON;
                    CREATE TABLE quotes (id INTEGER PRIMARY KEY ON CONFLICT FAIL AUTOINCREMENT,
                                         author TEXT,
                                         date INTEGER,
                                         quote_text TEXT,
                                         rating INTEGER,
                                         votes INTEGER);
                    CREATE TABLE users (id TEXT PRIMARY KEY ON CONFLICT FAIL,
                                        name TEXT UNIQUE ON CONFLICT FAIL,
                                        email TEXT UNIQUE ON CONFLICT FAIL,
                                        admin BOOLEAN,
                                        active BOOLEAN,
                                        password TEXT);
                    CREATE TABLE tokens (id TEXT PRIMARY KEY ON CONFLICT FAIL,
                                         date_issued INTEGER,
                                         active BOOLEAN,
                                         user TEXT,
                                         FOREIGN KEY(user) REFERENCES users(id));
                    CREATE TABLE db_version (version INTEGER, subversion INTEGER, subsubversion INTEGER);
                    """)
    c.execute('INSERT INTO db_version VALUES (?, ?, ?)', (VERSION, SUBVERSION, SUBSUBVERSION))


def create_superuser(c, passwd):
    print("Creating super user...")
    query = c.execute("SELECT * FROM users WHERE admin = 1")

    if not query.fetchone():
        pwd = hash_pwd(passwd)
        adm_uuid = str(uuid.uuid4())
        c.execute("INSERT INTO users VALUES(?, 'admin', 'admin@example.com', 1, 1, ?)",
                  (adm_uuid, pwd))

    else:
        print("Super users found, not adding any more.")


def upgrade_to_2_0_0(c):
    print("Executing migration step from 1.0.0 to 2.0.0")
    c.executescript("""
                    PRAGMA foreign_keys = ON;
                    CREATE TABLE users (id TEXT PRIMARY KEY ON CONFLICT FAIL,
                                        name TEXT UNIQUE ON CONFLICT FAIL,
                                        email TEXT UNIQUE ON CONFLICT FAIL,
                                        admin BOOLEAN,
                                        active BOOLEAN,
                                        password TEXT);
                    CREATE TABLE tokens (id TEXT PRIMARY KEY ON CONFLICT FAIL,
                                         date_issued INTEGER,
                                         active BOOLEAN,
                                         user TEXT,
                                         FOREIGN KEY(user) REFERENCES users(id));
                    """)
    c.execute('UPDATE db_version SET version=?, subversion=?, subsubversion=?', (2, 0, 0))


if __name__ == "__main__":
    superuser_pass = 'admin'
    database_file = '/var/quotes/quotes.db'
    if len(sys.argv) > 1:
        database_file = sys.argv[1]
        if len(sys.argv) >= 3:
            superuser_pass = sys.argv[2]

    conn = sqlite3.connect(database_file)
    c = conn.cursor()
    try:
        version_row = c.execute('SELECT * FROM db_version')
        version_check = c.fetchone()

    except sqlite3.OperationalError as e:
        with conn:
            create_db(c)
            create_superuser(c, superuser_pass)

        sys.exit(0)

    # Put here the data migrations for next iterations
    current_version = "{0}.{1}.{2}".format(VERSION, SUBVERSION, SUBSUBVERSION)
    database_version = "{}.{}.{}".format(version_check[0], version_check[1], version_check[2])

    while current_version != database_version:
        if database_version == '1.0.0':
            with conn:
                upgrade_to_2_0_0(c)

        version_row = c.execute('SELECT * FROM db_version')
        version_check = c.fetchone()
        database_version = "{}.{}.{}".format(version_check[0], version_check[1], version_check[2])

    with conn:
        create_superuser(c, superuser_pass)
