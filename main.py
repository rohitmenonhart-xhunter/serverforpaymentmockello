from flask import Flask, request, jsonify, redirect, url_for
import uuid
import time
import concurrent.futures
from flask_cors import CORS

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
    if session_duration > 600:  # Expire after 10 minutes (adjust as needed)
        del dynamic_urls[unique_id]  # Remove expired session
        return redirect(url_for('access_denied'))

    # Return the access key for the user
    return jsonify({
        "message": f"Payment successful! Your access key is: {session_data['key']}. Please use it within this session."
    }), 200

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
    app.run(debug=True, threaded=True)
