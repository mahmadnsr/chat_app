from flask import Flask, request, jsonify, render_template, session
import storage # Import the module to access its functions

app = Flask(__name__)
app.secret_key = "secret123"

@app.route("/")
def home():
    if "user" in session:
        return render_template("chat.html", user=session["user"])
    return render_template("home.html")

@app.route("/register", methods=["POST"])
def register():
    data = request.json
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if not username or not email or not password:
        return {"error": "Please fill all fields"}, 400

    # Fixed: Removed user_id as storage.create_user only takes 3 args
    if storage.create_user(username, email, password):
        session["user"] = username
        return {"status": "registered"}

    return {"error": "Username or email already exists"}, 409

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    username = storage.verify_login(data.get("email"), data.get("password"))
    if username:
        session["user"] = username
        return {"status": "logged_in"}
    return {"error": "Invalid email or password"}, 401

@app.route("/logout")
def logout():
    session.pop("user", None)
    return {"status": "logged_out"}

@app.route("/send", methods=["POST"])
def send():
    if "user" not in session:
        return {"error": "Login required"}, 401

    data = request.json
    sender = session["user"]
    receiver = data.get("to")
    msg = data.get("msg")

    if not storage.user_exists(receiver):
        return {"error": "User does not exist"}, 404

    if storage.is_blocked(receiver, sender):
        return {"error": "You are blocked"}, 403

    storage.store_message(sender, receiver, msg)
    return {"status": "sent"}

@app.route("/inbox/<chat_with>")
def inbox(chat_with):
    if "user" not in session:
        return {"error": "Login required"}, 401
    
    messages = storage.get_messages_between(session["user"], chat_with)
    return jsonify(messages)

@app.route("/conversations")
def conversations():
    if "user" not in session:
        return {"error": "Login required"}, 401

    user = session["user"]
    users = storage.get_conversations(user)
    data = []
    for u in users:
        data.append({
            "user": u,
            "unread": storage.get_unread_count(user, u),
            "last": storage.get_last_message(user, u)
        })
    return jsonify(data)

@app.route("/delete_conversation/<chat_with>", methods=["POST"])
def delete_conv(chat_with):
    if "user" not in session:
        return {"error": "Login required"}, 401
    storage.delete_conversation(session["user"], chat_with)
    return {"status": "deleted"}

@app.route("/block/<username>", methods=["POST"])
def block(username):
    if "user" not in session:
        return {"error": "Login required"}, 401
    storage.block_user(session["user"], username)
    return {"status": "blocked"}

@app.route("/search_user/<username>")
def search_user(username):
    return jsonify({"exists": storage.user_exists(username)})

@app.route("/chat")
def chat():
    if "user" not in session:
        return "Login required", 401
    return render_template("chat.html", user=session["user"])

if __name__ == "__main__":
    app.run(debug=True)
    
    
