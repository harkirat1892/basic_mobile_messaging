- When a connection is made with homepage, the MainHandler function is called. Always, the server maintains a connection with the client.

- If no username is provided via the GET parameter, a username is randomly generated and assigned to the user. Whenever the user sends a message to other users, this username is what identifies this user.

- If at this stage, there are any offline messages for the user, they are shown to the user. They are saved in a collection in MongoDB.

- When a user types in a message and submits it, a request is made to "/a/message/new" which is handled by MessageNewHandler class.

- If any mention is made to any user, e.g.: "@hogwarts abra kadabra", hogwarts is picked up and the message body "abra kadabra" gets marked to be delivered to user hogwarts.

- The message is then checked for duplication as per the criteria, then saved in the MongoDB collection "messages", before making an attempt to deliver it right away.

- If the user is connected to server, message is delivered to the user, else it is marked as pending delivery in the document in "messages" collection.

- If a user sends a message without "@", the message is broadcast to every online member, hence it is a public message readable by everyone online.

- If a user logs in having some pending messages for him/her, those messages are shown to the user, as in the 3rd step above.


This is the basic work flow.


Storage:
-------

MongoDB's 2 collections are used: users and messages.

- Users saves usernames of existing users. In future, password protection and other features can be added.

- Messages contains all messages. If a message is sent to public, the "to" field is '', else a username is there meaning the message with a username is a private message.

