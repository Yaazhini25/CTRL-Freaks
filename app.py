from flask import Flask, request, jsonify, render_template, session
import sqlite3
import qrcode
from io import BytesIO
import base64
import pandas as pd
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'

CSV_FILE = "product_discounts_output.csv"

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
    barcode_12 = barcode_16[:12]

    if not barcode_16:
        return jsonify({"success": False, "error": "No barcode provided."}), 400

    product_info = check_product(barcode_12, '12')
    if product_info:
        product_name, product_price = product_info

        if barcode_16 in session['cart']:
            del session['cart'][barcode_16]
            session.modified = True
            message = f"Product {product_name} removed from cart."
        else:
            session['cart'][barcode_16] = {"name": product_name, "price": product_price}
            session.modified = True
            message = f"Product {product_name} added to cart."

        return jsonify({"success": True, "message": message, "price": product_price}), 200

    return jsonify({"success": False, "error": "No valid barcode found."}), 400

# Save purchased products to CSV
def save_bought_products(cart_dict):
    if not cart_dict:
        return
    aggregated = {}
    for barcode, info in cart_dict.items():
        name = info['name']
        price = info['price']
        if name in aggregated:
            aggregated[name]['quantity'] += 1
            aggregated[name]['total_price'] += price
        else:
            aggregated[name] = {'quantity': 1, 'total_price': price, 'discount': 0}

    data = []
    for name, details in aggregated.items():
        data.append({
            "Product_Name": name,
            "Quantity": details['quantity'],
            "Total_Price": details['total_price'],
            "Predicted_Discount": details['discount']
        })

    df = pd.DataFrame(data)
    df.to_csv(CSV_FILE, index=False)
    print("Cart saved to product_discounts_output.csv")

@app.route('/generate_qr_code', methods=['POST'])
def generate_qr_code():
    data = request.form
    amount = data.get('amount')
    upi_id = '9342447865@ptyes'
    name = 'YAAZHINI S'

    if not amount:
        return jsonify({"success": False, "message": "No amount provided."}), 400

    # Generate UPI QR
    upi_url = f"upi://pay?pa={upi_id}&pn={name}&am={amount}&cu=INR"
    qr = qrcode.make(upi_url)
    buffered = BytesIO()
    qr.save(buffered, format="PNG")
    qr_code_url = base64.b64encode(buffered.getvalue()).decode('utf-8')

    # Save purchased products after payment
    save_bought_products(session['cart'])

    # Clear cart after purchase
    session['cart'] = {}
    session.modified = True

    return jsonify({"success": True, "qr_code_url": f"data:image/png;base64,{qr_code_url}", "upi_url": upi_url})

@app.route('/clear_cart', methods=['POST'])
def clear_cart():
    session['cart'] = {}
    session.modified = True
    return jsonify({"success": True, "message": "Cart cleared successfully."})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
