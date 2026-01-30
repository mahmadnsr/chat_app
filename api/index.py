import os
from flask import Flask, request, jsonify, render_template, session

# Vercel relative import fix
try:
    from . import storage 
except (ImportError, ValueError):
    import storage

# Path safety for Vercel
base_dir = os.path.dirname(os.path.abspath(__file__))
template_dir = os.path.join(base_dir, '../templates')
static_dir = os.path.join(base_dir, '../static')

app = Flask(__name__, 
            template_folder=template_dir, 
            static_folder=static_dir)

# Secret key for sessions
app.secret_key = os.getenv("SESSION_KEY", "secret123")

# DATABASE INITIALIZATION
# Isse tables tabhi banengi jab app pehli baar load hogi
with app.app_context():
    try:
        storage.init_db()
        print("Database initialized successfully!")
    except Exception as e:
        print(f"Database init error: {e}")

@app.route("/")
def home():
    if "user" in session:
        return render_template("chat.html", user=session["user"])
    return render_template("home.html")

@app.route("/register", methods=["POST"])
def register():
    data = request.json
    if not data: return {"error": "No data received"}, 400
    
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    
    if not username or not email or not password:
        return {"error": "Please fill all fields"}, 400
        
    if storage.create_user(username, email, password):
        session["user"] = username
        return {"status": "registered"}
    return {"error": "Username or email already exists"}, 409

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    if not data: return {"error": "No data received"}, 400
    
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
    if "user" not in session: return {"error": "Login required"}, 401
    data = request.json
    sender = session["user"]
    receiver = data.get("to")
    msg = data.get("msg")
    
    if not storage.user_exists(receiver): return {"error": "User does not exist"}, 404
    if storage.is_blocked(receiver, sender): return {"error": "You are blocked"}, 403
    
    storage.store_message(sender, receiver, msg)
    return {"status": "sent"}

@app.route("/inbox/<chat_with>")
def inbox(chat_with):
    if "user" not in session: return {"error": "Login required"}, 401
    messages = storage.get_messages_between(session["user"], chat_with)
    return jsonify(messages)

@app.route("/conversations")
def conversations():
    if "user" not in session: return {"error": "Login required"}, 401
    user = session["user"]
    users = storage.get_conversations(user)
    data = [{"user": u, 
             "unread": storage.get_unread_count(user, u), 
             "last": storage.get_last_message(user, u)} for u in users]
    return jsonify(data)

@app.route("/chat")
def chat():
    if "user" not in session:
        return render_template("home.html")
    return render_template("chat.html", user=session["user"])

@app.route("/search_user/<username>")
def search_user(username):
    exists = storage.user_exists(username)
    return jsonify({"exists": exists})

# Needed for Vercel deployment
app = app