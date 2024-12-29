from flask import Flask, request, jsonify, redirect, url_for
import uuid
import time
import concurrent.futures
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

# Predefined keys
available_keys = [
    "KEY1", "KEY2", "KEY3", "KEY4", "KEY5",
    "KEY6", "KEY7", "KEY8", "KEY9", "KEY10"
]

# List of used keys (initially empty)
used_keys = []

# Temporary URL mapping (masked URLs)
dynamic_urls = {}

# Thread pool for concurrent task execution
executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)

# Route for Razorpay redirection (after successful payment)
@app.route('/payment-success', methods=['GET'])
def payment_success():
    # Check if there are any available keys left
    if not available_keys:
        return jsonify({"error": "No available keys at the moment!"}), 500

    # Assign a unique key from the available keys
    assigned_key = available_keys.pop(0)  # Take the first key and remove it from the available list

    # Mark the key as used immediately (to prevent re-use)
    used_keys.append(assigned_key)

    # Generate a unique dynamic URL identifier
    unique_id = str(uuid.uuid4())  # Generate a unique identifier for this session

    # Store the unique identifier and associated key in the dynamic URLs mapping
    dynamic_urls[unique_id] = {'key': assigned_key, 'timestamp': time.time()}

    # Redirect user to the dynamic masked URL (the user is effectively masked)
    masked_url = url_for('masked_url', unique_id=unique_id)
    return redirect(masked_url)

# Route for the masked dynamic URL (valid only for the session duration)
@app.route('/masked/<unique_id>', methods=['GET'])
def masked_url(unique_id):
    # Check if the unique ID exists in the dynamic URLs mapping
    if unique_id not in dynamic_urls:
        return redirect(url_for('access_denied'))

    # Fetch the associated key and timestamp for the unique ID
    session_data = dynamic_urls[unique_id]

    # Validate the session time (expire after 10 minutes)
    session_duration = time.time() - session_data['timestamp']
    if session_duration > 600:  # Expire after 10 minutes
        del dynamic_urls[unique_id]  # Remove expired session
        return redirect(url_for('access_denied'))

    # Render a custom HTML page to display the access key and allow copy functionality
    access_key = session_data['key']
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Payment Success</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                text-align: center;
                margin: 50px;
            }}
            .key-box {{
                display: inline-block;
                padding: 15px;
                border: 1px solid #ddd;
                background-color: #f9f9f9;
                font-size: 18px;
                margin: 20px 0;
                cursor: pointer;
            }}
            .message {{
                font-size: 16px;
                margin-bottom: 10px;
            }}
        </style>
    </head>
    <body>
        <h1>Payment Successful!</h1>
        <p class="message">Click below to copy your access key:</p>
        <div class="key-box" id="accessKey" onclick="copyKey()">{access_key}-click here now</div>
        <p id="status" style="color: green;"></p>
        <script>
            function copyKey() {{
                const keyBox = document.getElementById('accessKey');
                navigator.clipboard.writeText(keyBox.textContent).then(() => {{
                    document.getElementById('status').textContent = 'Key copied! Redirecting...';
                    setTimeout(() => {{
                        window.location.href = 'https://mockello-hr-round2.vercel.app/'; // Replace with your target URL
                    }}, 1500);
                }}).catch(err => {{
                    document.getElementById('status').textContent = 'Failed to copy the key!';
                    console.error('Failed to copy text: ', err);
                }});
            }}
        </script>
    </body>
    </html>
    """

# Route for users to enter the key on the main website
@app.route('/validate-key', methods=['POST'])
def validate_key():
    user_key = request.json.get('access_key')

    if not user_key:
        return jsonify({"error": "Missing key!"}), 400

    # Check if the key exists in the "used" keys list
    if user_key in used_keys:
        # If the key is found, delay the deletion by 4-5 seconds in a background thread
        executor.submit(delayed_key_removal, user_key)

        return jsonify({"message": "Key validated successfully! You can now access the site."}), 200
    else:
        # If the key is not found or already used, deny access
        return jsonify({"error": "Invalid or already used key!"}), 400

# Function to add the key to used_keys immediately and remove it after a delay
def delayed_key_removal(key):
    time.sleep(5)  # Delay for 4-5 seconds (adjust as needed)
    if key in used_keys:
        used_keys.remove(key)  # Remove the key after the delay

# Route to display access denied message if user tries to access without validation
@app.route('/access-denied', methods=['GET'])
def access_denied():
    return "Access Denied! Please ensure you completed the payment and received the key."

@app.route('/ping', methods=['GET'])
def ping():
    return jsonify({"status": "Server is up and running!"}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))  # Use PORT environment variable if set, otherwise default to 5000
    app.run(host='0.0.0.0', port=port, debug=True, threaded=True)
