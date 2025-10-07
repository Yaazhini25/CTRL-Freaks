from flask import Flask, request, jsonify, render_template, session 
import sqlite3
import qrcode
from io import BytesIO
import base64

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Set a secret key for session management

# Initialize session cart if not present
def check_product(barcode, barcode_type='12'):
    conn = sqlite3.connect('barcode_data.db')
    c = conn.cursor()

    if barcode_type == '12':
        c.execute(
            "SELECT product_name, product_price FROM products WHERE barcode_12_digits = ?", (barcode,))
    else:
        c.execute(
            "SELECT product_name, product_price FROM products WHERE barcode_16_digits = ?", (barcode,))

    result = c.fetchone()
    conn.close()
    return result

@app.before_request
def initialize_cart():
    if 'cart' not in session:
        session['cart'] = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    data = request.json
    barcode_16 = data.get('barcode_16_digits', '')
    barcode_12 = barcode_16[:12]  # Extract the first 12 digits

    print(f"Scanned Barcode (16 digits): {barcode_16}")
    print(f"Scanned Barcode (12 digits): {barcode_12}")

    if not barcode_16:
        return jsonify({"success": False, "error": "No barcode provided."}), 400

    # Check for the product in the database
    product_info = check_product(barcode_12, '12')
    if product_info:
        product_name, product_price = product_info

        # Log current session cart before modification 
        print(f"Current cart before modification: {session.get('cart', {})}")

        # Toggle add/remove functionality
        if barcode_16 in session['cart']:
            # Product is already in the cart, remove it
            del session['cart'][barcode_16]
            session.modified = True  # Mark session as modified
            print(f"Removed {product_name} from cart.")
            message = f"Product {product_name} removed from cart." 
        else:
            # Product is not in the cart, add it
            session['cart'][barcode_16] = {"name": product_name, "price": product_price}
            session.modified = True  # Mark session as modified
            print(f"Added {product_name} to cart.")
            message = f"Product {product_name} added to cart."

        # Log current session cart after modification
        print(f"Current cart after modification: {session.get('cart', {})}")
        return jsonify({"success": True, "message": message, "price": product_price}), 200

    print("No valid barcode found in the database.")
    return jsonify({"success": False, "error": "No valid barcode found."}), 400

@app.route('/generate_qr_code', methods=['POST'])
def generate_qr_code():
    data = request.form
    amount = data.get('amount')
    upi_id = '9342447865@ptyes'  # Replace with your actual UPI ID
    name = 'YAAZHINI S' 

    if not amount:
        return jsonify({"success": False, "message": "No amount provided."}), 400

    # Create the UPI payment URL
    upi_url = f"upi://pay?pa={upi_id}&pn={name}&am={amount}&cu=INR"

    # Generate the QR code using the UPI URL
    qr = qrcode.make(upi_url)
    buffered = BytesIO()
    qr.save(buffered, format="PNG")
    qr_code_url = base64.b64encode(buffered.getvalue()).decode('utf-8')

    return jsonify({"success": True, "qr_code_url": f"data:image/png;base64,{qr_code_url}", "upi_url": upi_url})



@app.route('/clear_cart', methods=['POST'])
def clear_cart():
    session['cart'] = {}  # Clear the cart in the session
    session.modified = True
    print("Cart cleared.")
    return jsonify({"success": True, "message": "Cart cleared successfully."})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
