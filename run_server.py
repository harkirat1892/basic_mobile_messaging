import logging
import tornado.escape
import tornado.ioloop
import tornado.web
import os.path
import uuid


import datetime
from datetime import timedelta

# import redis
import pymongo
from pymongo import MongoClient
from bson.objectid import ObjectId

from tornado.concurrent import Future
from tornado import gen
from tornado.options import define, options, parse_command_line

define("port", default=8888, help="run on the given port", type=int)
define("debug", default=False, help="run in debug mode")


"""
Instantiating MongoDB client

Using Mongo defaults, without security or any configurations, for demo purposes

"""

mongo = MongoClient()
db = mongo['niki'] # or mongo.niki, same
messages_collection = db.messages
users_collection = db.users


class Messaging(object):
    def __init__(self):
        # Maintain list of current clients
        self.connected = {}

    def wait_for_messages(self, cursor=None, username=None):
        result_future = Future()
        self.connected[username] = result_future
        return result_future

    def cancel_wait(self, future, username):
        # Deleting user from connected clients list
        del self.connected[username]
        # Set an empty result to unblock any coroutines waiting.
        future.set_result([])

    def new_messages(self, messages, username):
        logging.info("Sending new message to %r listeners", len(self.connected))
        if username != '':
            try:
                self.connected[username].set_result(messages)
            except:
                # User is not online, save the message as pending for that user
                message_id = messages[0]["id"]
                messages_collection.update({"_id":ObjectId(message_id)},{"$set":{"remaining":[username]}})
        else:
            for key, future in self.connected.items():
                future.set_result(messages)


messaging = Messaging()


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        username = ''

        try:
            if self.get_argument("username", default=None, strip=True):
                username = self.get_argument("username", default=None, strip=True)
        except:
            pass

        #TODO username-password authentication
        if not username:
            import string
            import random
            def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
                return ''.join(random.choice(chars) for _ in range(size))

            username = id_generator(5)


        # Check if user exists
        user_exists = users_collection.find_one({"username": username})

        logging.info("New connection from: "+format(username))

        if not user_exists:
            user_insert = {
                "username": username,
                "password": '',
                "last_ip_addr": self.request.remote_ip,
                "last_online": ''
            }
            user_id = users_collection.insert_one(user_insert).inserted_id
        else:
            user_id = str(user_exists["_id"])

        pending = self.pending_messages(username)

        self.render("index.html", username=username, messages=pending)


    def pending_messages(self, username):
        all_msgs = messages_collection.find({"remaining": username})
        pending_messages = []

        for msg in all_msgs:
            current_datetime = msg["time"]
            current_date = current_datetime.date().strftime("%d %b")

            message = {
                "id": str(msg["_id"]),
                "body": msg["body"],
                "time": format(current_date) + ", " + format(current_datetime.time().strftime("%-I:%M %p")),
                "to": msg["to"],
                "from_username": msg["from"],
                "is_private": True
            }

            message["html"] = tornado.escape.to_basestring(
                self.render_string("message.html", message=message))

            pending_messages.append(message)

        # Updating as seen
        messages_collection.update({"remaining": username}, {"$set": {"remaining": []}}, multi=True)
        return pending_messages


class MessageNewHandler(tornado.web.RequestHandler):
    def post(self):
        from_username = self.get_argument("username")
        message_body = self.get_argument("body")

        current_datetime = datetime.datetime.now()
        current_date = current_datetime.date().strftime("%d %b")

        # message for below username
        username = ''

        message = {
            "body": message_body,
            "time": format(current_date) + ", " + format(current_datetime.time().strftime("%-I:%M %p")),
            "from_username": from_username,
            "is_private": False
        }

        if "@" in message_body:
            """Getting all existing users from the mentions
            Below commented line saves messages for ONLY registered users
            """
            # all_mentions = [mention[1:] for mention in message_body.split() if mention.startswith('@') and users_collection.find_one({"username": mention[1:]})]

            # Below line takes any mentioned user
            all_mentions = [mention[1:] for mention in message_body.split() if mention.startswith('@')]


            # TODO for all mentioned users later
            try:
                username = all_mentions[0]
                message["is_private"] = True
                message["to"] = username
                message_body = message_body.split(' ', 1)[1]
                message["body"] = message_body
            except:
                pass

        message_insert = {
            "from": from_username,
            "to": username,
            "time": current_datetime,
            "body": message_body,
            "remaining_receivers": []
        }

        # Duplicate check
        # Looks for latest message with same body
        latest_message = messages_collection.find_one({"body": message_body, "from": from_username}, sort=[("time", pymongo.DESCENDING)])
        
        """
        
        If a same entry is in collection, check time difference
        If difference <= 5, don't process further
        
        """
        if latest_message:
            diff = current_datetime - latest_message['time']
            if diff.total_seconds() <= 5:
                return
        # Duplicate check finished

        message_id = messages_collection.insert_one(message_insert).inserted_id
        message['id'] = str(message_id)


        # to_basestring is necessary for Python 3's json encoder,
        # which doesn't accept byte strings.
        message["html"] = tornado.escape.to_basestring(
            self.render_string("message.html", message=message))

        if self.get_argument("next", None):
            self.redirect(self.get_argument("next"))
        else:
            self.write(message)

        messaging.new_messages([message], username)


class MessageUpdatesHandler(tornado.web.RequestHandler):
    @gen.coroutine
    def post(self):
        cursor = self.get_argument("cursor", None)
        self.username = self.get_argument("username", None)

        self.future = messaging.wait_for_messages(cursor=cursor, username=self.username)
        messages = yield self.future

        if self.request.connection.stream.closed():
            return
        self.write(dict(messages=messages))

    def on_connection_close(self):
        messaging.cancel_wait(self.future, self.username)


def main():
    parse_command_line()
    app = tornado.web.Application(
        [
            (r"/", MainHandler),
            (r"/a/message/new", MessageNewHandler),
            (r"/a/message/updates", MessageUpdatesHandler),
            ],
        cookie_secret="PO_there_are_no_secrets",
        template_path=os.path.join(os.path.dirname(__file__), "templates"),
        static_path=os.path.join(os.path.dirname(__file__), "static"),
        xsrf_cookies=True,
        debug=options.debug,
        )
    app.listen(options.port)
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()