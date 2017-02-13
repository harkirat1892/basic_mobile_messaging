A Tornado based basic messaging application, which makes persistent connections with all clients. Requires Python3+.


Goals:
-------

1. Maintaining a persistent socket connection to every mobile device that has requested a connection to the server.

=> The server maintains a persistent connection to every client


2. 	Routes messages tagged with the destinationId to a particular mobile device.

=> When a message is sent to a user with "@john <MESSAGE TEXT>", wherever the user john is logged in from right now, the message gets delivered there. Similarly, any user can be sent a message.


3. Does not send duplicate messages. Defined as ((“message1, destinationId1” == “message2, destinationId2”) && (arrivalTime2-arrivalTime1)<= 5sec)

=> If a user sends the same message to any users more than once within a 5 second window, the new messages are ignored by the server.


How to:
-------

Run the server using "python3 run_server.py" in terminal. It will be accessible on localhost:8888

As of now, no password authentication is there.
If you want to login as user "hodor", go to "localhost:8888?username=hodor"

Password authentication will be there soon!


Requires:
-------

MongoDB <https://www.mongodb.com>
=> MongoDB is used to maintain a list of registered users, and to keep track of messages being sent.
If an offline user receives messages, they are saved in the MongoDB "messages" collection and flagged as pending. Once the user logs in, all pending messages are delivered to the user.


PyMongo <https://api.mongodb.com/python/current>
=> The Python distribution to work with MongoDB.


Tornado <http://www.tornadoweb.org>
=> Python web framework that helps in keeping connections persistent. Highly scalable as compared to most other frameworks.


Python3+
=> Works on Python3+ only.
