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
import logging
import re
import html
import math
import time
import smtplib

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from configparser import SafeConfigParser

from bottle import route, run, request, response, install, HTTPResponse
from bottle_sqlite import SQLitePlugin
from users import (check_login, check_admin, register_user,
                   log_in, log_out, change_password,
                   User, admin_change_password)

DEBUG = False

if not DEBUG:
    DATABASE = '/var/quotes/quotes.db'

else:
    DATABASE = 'quotes.db'

EMAIL_FILE = 'html/email.html'
EMAIL_ADDRESS = 'noreply@example.com'
DOMAIN = 'www.example.com'
HOST = '0.0.0.0'
PORT = 6000


logging.basicConfig(format='localhost - - [%(asctime)s] %(message)s',
                    level=logging.DEBUG)
log = logging.getLogger(__name__)


class EnableCors(object):
    name = 'enable_cors'
    api = 2

    def apply(self, fn, context):
        def _enable_cors(*args, **kwargs):
            # set CORS headers
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token, Authorization'

            if request.method != 'OPTIONS':
                # actual request; reply with the actual response
                return fn(*args, **kwargs)

        return _enable_cors


install(SQLitePlugin(dbfile=DATABASE))
install(EnableCors())


def responseGenerator(status_code, message):
    headers = {}
    headers['Access-Control-Allow-Origin'] = '*'
    headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, OPTIONS'
    headers['Access-Control-Allow-Headers'] = 'Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token, Authorization'

    return HTTPResponse(body=message,
                        status=status_code,
                        headers=headers)


def sendRegisteredEmail(email, user, password):
    me = EMAIL_ADDRESS

    # Create message container - the correct MIME type is multipart/alternative.
    msg = MIMEMultipart('alternative')
    msg['Subject'] = "Registered in the quotes system."
    msg['From'] = me
    msg['To'] = email

    # Create the body of the message (a plain-text and an HTML version).
    text = "Hi!\nNow you've got access to Quote Server\nYour user is {} and your pass is {}".format(user, password)
    text += "\n---\nVisit {} and change your password.".format(DOMAIN)
    with open(EMAIL_FILE, 'r') as f:
        html = f.read()

    user_rgx = re.compile(r'\$\{user\}')
    pass_rgx = re.compile(r'\$\{password\}')

    html = user_rgx.sub(html, user)
    html = pass_rgx.sub(html, password)

    # Record the MIME types of both parts - text/plain and text/html.
    part1 = MIMEText(text, 'plain')
    part2 = MIMEText(html, 'html')

    # Attach parts into message container.
    # According to RFC 2046, the last part of a multipart message, in this case
    # the HTML message, is best and preferred.
    msg.attach(part1)
    msg.attach(part2)

    # Send the message via local SMTP server.
    s = smtplib.SMTP('localhost')
    # sendmail function takes 3 arguments: sender's address, recipient's address
    # and message to send - here it is sent as one string.
    s.sendmail(me, email, msg.as_string())
    s.quit()


@route('/', method=['OPTIONS', 'GET'])
def index(db):
    user = check_login(db, request)
    if not user:
        return responseGenerator(401, "Not logged in")

    quotes = db.execute('SELECT * FROM quotes ORDER BY date ASC')
    result = []
    for quote in quotes:
        element = {"id": quote[0],
                   "author": quote[1],
                   "date": quote[2],
                   "text": quote[3],
                   "rating": quote[4],
                   "votes": quote[5]}

        result.append(element)

    return {"quotes": result}


@route('/quote/<quote_id:int>', method=['OPTIONS', 'GET'])
def quote_detail(db, quote_id=None):
    user = check_login(db, request)
    if not user:
        return responseGenerator(401, "Not logged in")

    if not quote_id:
        return responseGenerator(400, "Invalid quote request")

    query = db.execute('SELECT * FROM quotes WHERE id = ?', (quote_id,))
    quote = query.fetchone()

    if not quote:
        return responseGenerator(404, "Not found")

    return {"quote": {"id": quote[0],
                      "author": quote[1],
                      "date": quote[2],
                      "text": quote[3],
                      "rating": quote[4],
                      "votes": quote[5]}}


@route('/quote', method=['OPTIONS', 'POST'])
def quote_add(db):
    user = check_login(db, request)
    if not user:
        return responseGenerator(401, "Not logged in")

    new_quote = request.json
    new_quote["date"] = int(time.time())
    new_quote["text"] = html.escape(new_quote["text"])
    log.debug("Received {0}".format(new_quote))
    log.debug("Received type {0}".format(type(new_quote)))

    query = db.execute("INSERT INTO quotes (author, quote_text, date, rating, votes) VALUES(?, ?, ?, 0, 0)",
                       (new_quote["author"],
                        new_quote["text"],
                        new_quote["date"],))

    new_quote["id"] = query.lastrowid
    new_quote["votes"] = 0
    new_quote["rating"] = 0
    return {"quote": new_quote}


@route('/vote/<quote_id:int>', method=['OPTIONS', 'POST'])
def vote_quote(db, quote_id=None):
    user = check_login(db, request)
    if not user:
        return responseGenerator(401, "Not logged in")

    if not quote_id:
        return responseGenerator(400, "Wrong ID")

    vote_post = request.json
    vote = vote_post["vote"]

    if vote < 1 or vote > 5:
        return responseGenerator(400, "Cast votes between one and five")

    query = db.execute("SELECT * FROM quotes WHERE id=?", (quote_id,))
    row = query.fetchone()

    if not row:
        return responseGenerator(404, "Quote not found")

    total_votes = row[5] + 1
    if total_votes > 1:
        new_rating = int(math.floor((row[4] + vote) / 2))

    else:
        new_rating = vote

    query = db.execute("UPDATE quotes SET rating=?, votes=? WHERE id=?", (new_rating, total_votes, quote_id))

    return {"quote": {"id": row[0],
                      "author": row[1],
                      "date": row[2],
                      "text": row[3],
                      "rating": new_rating,
                      "votes": total_votes}}


@route('/best', method=['OPTIONS', 'GET'])
def best_quotes(db):
    user = check_login(db, request)
    if not user:
        return responseGenerator(401, "Not logged in")

    quotes = db.execute('SELECT * FROM quotes ORDER BY (votes / rating) DESC LIMIT 10')
    result = []
    for quote in quotes:
        element = {"id": quote[0],
                   "author": quote[1],
                   "date": quote[2],
                   "text": quote[3],
                   "rating": quote[4],
                   "votes": quote[5]}

        result.append(element)

    return {"quotes": result}


@route('/latest', method=['OPTIONS', 'GET'])
def latest_quotes(db):
    user = check_login(db, request)
    if not user:
        return responseGenerator(401, "Not logged in")

    quotes = db.execute('SELECT * FROM quotes ORDER BY date ASC LIMIT 10')
    result = []
    for quote in quotes:
        element = {"id": quote[0],
                   "author": quote[1],
                   "date": quote[2],
                   "text": quote[3],
                   "rating": quote[4],
                   "votes": quote[5]}

        result.append(element)

    return {"quotes": result}


# User control


@route('/register', method=['OPTIONS', 'POST'])
def register(db):
    admin = check_admin(db, request)
    if not admin:
        return responseGenerator(403, 'Invalid user')

    new_user_data = request.json
    log.debug("New User Data Received: {}".format(new_user_data))

    if not re.match(r'[^@]+@[^@]+\.[^@]+', new_user_data["email"]):
        return responseGenerator(400, "Invalid email address")

    userdata = {
        "name": html.escape(new_user_data["username"]),
        "email": new_user_data["email"],
        "password": new_user_data["password"]
    }

    user, msg = register_user(db, userdata)

    if not user and msg:
        return responseGenerator(400, msg)

    else:
        try:
            sendRegisteredEmail(userdata["email"], userdata["name"], userdata["password"])

        except Exception as e:
            log.error("Error sending registration email: {}".format(e))

        return {"user": user.todict()}


@route('/login', method=['OPTIONS', 'POST'])
def login(db):
    login_data = request.json
    if "username" not in login_data or "password" not in login_data:
        return responseGenerator(400, "Missing data for login")

    user, token = log_in(db, login_data["username"], login_data["password"])

    if not user:
        return responseGenerator(404, "Username or password mismatch.")

    else:
        return {"token": token,
                "user": user.todict()}


@route('/me', method=['OPTIONS', 'GET'])
def me_get(db):
    user = check_login(db, request)
    if not user:
        return responseGenerator(401, "Not logged in")

    return {"user": user.todict()}


@route('/logout', method=['OPTIONS', 'POST', 'GET'])
def logout(db):
    user = check_login(db, request)
    if not user:
        return responseGenerator(200, "Logged out")

    log_out(db, request)

    return responseGenerator(200, "Logged out")


@route('/change_password', method=['OPTIONS', 'POST'])
def change_pass(db):
    user = check_login(db, request)
    if not user:
        return responseGenerator(401, "Not logged in")

    data = request.json

    if "old_pass" not in data or "new_pass" not in data:
        return(400, "Missing fields")

    if change_password(db, user.id, data["old_pass"], data["new_pass"]):
        return {"result": True}

    else:
        return {"result": False}


@route('/admin_change_password', method=['OPTIONS', 'POST'])
def admin_change_pass(db):
    user = check_admin(db, request)
    if not user:
        return responseGenerator(401, "Not logged in")

    data = request.json

    if "username" not in data or "new_pass" not in data:
        return(400, "Missing fields")

    if admin_change_password(db, data["username"], data["new_pass"]):
        return {"result": True}

    else:
        return {"result": False}


@route('/users', method=['OPTIONS', 'GET'])
def list_users(db):
    admin = check_admin(db, request)
    if not admin:
        return responseGenerator(403, "Forbidden")

    query = db.execute("SELECT * FROM users")

    result = []
    for row in query:
        user = User(row[0],
                    row[1],
                    row[2],
                    row[3],
                    row[4])

        result.append(user.todict())

    return {"users": result}


if __name__ == "__main__":
    config = SafeConfigParser()
    config.read('config.ini')

    if len(sys.argv) > 1:
        if sys.argv[1] == '--debug':
            DEBUG = True
            log.debug("****************************")
            log.debug("**** Debug mode active! ****")
            log.debug("****************************")

        else:
            DEBUG = config.getboolean('main', 'debug')

    EMAIL_FILE = config.get('main', 'email_file')
    HOST = config.get('main', 'host')
    PORT = config.getint('main', 'port')
    DOMAIN = config.get('main', 'domain')

    run(host=HOST, port=PORT, server='paste', debug=DEBUG)
