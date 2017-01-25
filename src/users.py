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


import uuid
import time
import bcrypt
import hashlib
import random
import string


class User:
    def __init__(self, user_id, name, email, admin, active):
        self.id = user_id
        self.name = name
        self.email = email
        self.admin = admin
        self.active = active

    def is_admin(self):
        return self.admin

    def is_active(self):
        return self.active

    def todict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "active": self.active,
            "admin": self.admin
        }


def hash_pwd(password):
    return bcrypt.hashpw(password.encode(encoding='utf-8'), bcrypt.gensalt(12)).decode('utf-8')


def create_token(db, user):
    current_time = int(time.time())
    old_time = current_time - (((3600) * 24) * 7)

    db.execute("DELETE FROM tokens WHERE date_issued < ?",
                       (old_time,))

    hasher = hashlib.sha256()
    rndsequence = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(20))
    hasher.update(rndsequence.encode(encoding='utf-8'))
    token = hasher.hexdigest()

    db.execute("INSERT INTO tokens VALUES(?, ?, 1, ?)",
                       (token, current_time, user.id))

    return token


def log_in(db, name, passwd):
    query = db.execute("SELECT * FROM users WHERE name=?",
                       (name,))

    data = query.fetchone()
    if not data:
        return False, None

    hashed_pass = data[5].encode('utf-8')
    pwd_hash = bcrypt.hashpw(passwd.encode('utf-8'), hashed_pass)

    if bcrypt.hashpw(passwd.encode('utf-8'), hashed_pass) == hashed_pass:
        print("Hash: {} Password Hash: {}".format(hashed_pass, pwd_hash))
        user = User(data[0],
                    data[1],
                    data[2],
                    data[3],
                    data[4])

        token = create_token(db, user)
        return user, token

    else:
        return False, None


def check_login(db, request):
    auth = request.get_header('Authorization')
    if not auth:
        return False

    query = db.execute('SELECT * FROM tokens WHERE id = ? AND active = 1',
                       (auth,))

    token_row = query.fetchone()
    if not token_row:
        return False

    else:
        query = db.execute('UPDATE tokens SET date_issued = ? WHERE id = ?',
                           (int(time.time()), auth))
        user_id = token_row[3]
        query = db.execute('SELECT * FROM users WHERE id = ? and active = 1', (user_id,))

        data = query.fetchone()
        if not data:
            return False

        else:
            user = User(data[0],
                        data[1],
                        data[2],
                        data[3],
                        data[4])

            return user


def check_admin(db, request):
    user = check_login(db, request)

    if user.is_admin():
        return user

    else:
        return False


def register_user(db, userdata):
    query = db.execute('SELECT * FROM users WHERE email = ? OR name = ?',
                       (userdata["email"],
                        userdata["name"]))

    user_row = query.fetchone()

    if user_row:
        return False, "Email account or name already exists"

    new_uuid = str(uuid.uuid4())
    password = hash_pwd(userdata["password"])

    query = db.execute('INSERT INTO users VALUES(?, ?, ?, 0, 1, ?)',
                       (new_uuid,
                        userdata["name"],
                        userdata["email"],
                        password))

    return User(new_uuid, userdata["name"], userdata["email"], False, True), None


def change_password(db, user_id, old_passwd, new_passwd):
    query = db.execute("SELECT * FROM users WHERE id=?",
                       (user_id,))

    user_row = query.fetchone()

    if not user_row:
        return False

    hashed_pass = user_row[5].encode('utf-8')
    if bcrypt.hashpw(old_passwd.encode('utf-8'), hashed_pass) == hashed_pass:

        new_pwd = hash_pwd(new_passwd)
        query = db.execute("UPDATE users SET password=? WHERE id=?",
                        (new_pwd, user_id))

        return True

    else:
        return False


def admin_change_password(db, username, new_passwd):
    new_pwd = hash_pwd(new_passwd)

    query = db.execute("SELECT * FROM users WHERE name=?",
                       (username, ))

    user_row = query.fetchone()
    if not user_row:
        return False

    query = db.execute("UPDATE users SET password = ? WHERE id=?",
                       (username, new_pwd))

    return True


def log_out(db, request):
    auth = request.get_header('Authorization')

    db.execute("DELETE FROM tokens WHERE id = ?", (auth,))

    return True
