from flask import Flask, render_template, request, session, redirect, url_for
from flask_session import Session
import google.generativeai as genai
import os
import markdown

# --- Configuration ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "YOUR_API_KEY_HERE")

# --- Flask App Initialization ---
app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# --- Gemini AI Configuration and Error Handling ---
model = None
app_error = None

try:
    if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_API_KEY_HERE":
        raise ValueError("API key is not configured. Please replace 'YOUR_API_KEY_HERE' or set the GEMINI_API_KEY environment variable.")
    
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    print(f"--- FATAL ERROR: Failed to configure Gemini AI ---")
    print(e)
    app_error = f"Failed to initialize the AI model. Please check your API key and server logs. Error: {e}"

# This is a system instruction to guide the model's behavior
SYSTEM_INSTRUCTION = "You are a helpful and friendly AI assistant. Please format your responses using Markdown. Use lists, bold text, and code blocks where appropriate to make the output clear and readable."

@app.route("/", methods=["GET", "POST"])
def index():
    # --- POST request: Handle user input and AI interaction ---
    if request.method == "POST":
        if app_error:
            return redirect(url_for("index"))

        user_input = request.form["user_input"]
        
        # Ensure history exists in session
        if "history" not in session:
            session["history"] = []
        
        try:
            # Start a new chat with the full history
            chat = model.start_chat(history=session["history"])
            response = chat.send_message(user_input)
            
            # Update the history with the new user input and AI response
            session["history"].append({"role": "user", "parts": [user_input]})
            session["history"].append({"role": "model", "parts": [response.text]})
            session.modified = True

        except Exception as e:
            # If there's an error, store it in a temporary flash message
            session["error_flash"] = f"⚠️ Error: Could not get a response from the AI. {e}"

        # Redirect to the GET route to display the updated chat
        return redirect(url_for("index"))

    # --- GET request: Display the chat interface ---
    if "history" not in session:
        # On first visit, initialize with the system instruction
        session["history"] = [
            {"role": "user", "parts": [SYSTEM_INSTRUCTION]},
            {"role": "model", "parts": ["Understood! I will format my responses in Markdown."]}
        ]

    # Convert the raw API history to a user-friendly format for the template
    display_history = []
    # Loop through the raw history, starting after the initial system prompt
    for i in range(2, len(session.get("history", [])), 2):
        user_parts = session["history"][i]["parts"]
        model_parts = session["history"][i+1]["parts"]
        
        display_history.append({
            'user': "".join(user_parts),
            'bot': markdown.markdown("".join(model_parts), extensions=['fenced_code', 'codehilite'])
        })

    # Check for a flashed error message from the POST request
    flashed_error = session.pop("error_flash", None)
    
    return render_template("index.html", history=display_history, error=app_error or flashed_error)


@app.route("/reset")
def reset():
    session.clear()
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)