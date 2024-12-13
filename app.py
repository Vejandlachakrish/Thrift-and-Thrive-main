from flask import Flask, render_template, request, redirect, url_for, flash
from flask import session, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename
from functools import wraps
from faker import Faker
from datetime import datetime, timedelta
from jinja2 import TemplateNotFound
import os
import random
import csv

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key' 
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///thrift_and_thrive.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

UPLOAD_FOLDER = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'uploads') 
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER 

os.makedirs(UPLOAD_FOLDER, exist_ok=True) 
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    products = db.relationship('Product', backref='user', lazy=True)  
    is_admin = db.Column(db.Boolean, default=False)  


class Address(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) 
    street = db.Column(db.String(200), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(100), nullable=False)
    zip_code = db.Column(db.String(20), nullable=False)
    country = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(20))  
    label = db.Column(db.String(50))  

    # Define a relationship back to the User table
    user = db.relationship('User', backref=db.backref('addresses', lazy=True))


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    condition = db.Column(db.String(20), nullable=False)
    rating = db.Column(db.Float, default=0)
    image_filename = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) 


class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), 
                           nullable=False)
    quantity = db.Column(db.Integer, default=1)


class PurchaseEvent(db.Model):
    __tablename__ = 'purchase_event'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    address_id = db.Column(db.Integer, db.ForeignKey('address.id'), 
                           nullable=False)
    purchase_date = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='purchase_events')
    address = db.relationship('Address', backref='purchase_events')
    purchases = db.relationship('Purchase', backref='purchase_event', 
                                cascade='all, delete-orphan')


class Purchase(db.Model):
    __tablename__ = 'purchase'
    
    id = db.Column(db.Integer, primary_key=True)
    purchase_event_id = db.Column(db.Integer, db.ForeignKey(
        'purchase_event.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), 
                           nullable=False)
    quantity = db.Column(db.Integer, default=1)

    product = db.relationship('Product', backref='purchases')


# Model to store report files
class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    file_path = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


with app.app_context():
    db.create_all()


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/contact')
def contact():
    return render_template('contact.html')


@app.route('/profile', methods=['GET'])
def profile():
    if 'user_id' not in session:
        flash("Please log in to view your profile.", "error")
        return redirect(request.referrer or url_for('home'))
    
    user = User.query.get(session['user_id'])
    # Load the user's addresses
    user_addresses = Address.query.filter_by(user_id=user.id).all()
    # Load the user's purchase events
    purchase_events = PurchaseEvent.query.filter_by(user_id=user.id).all()

    return render_template('profile.html', user=user, addresses=user_addresses, 
                           purchase_events=purchase_events)


@app.route('/add_address', methods=['POST'])
def add_address():
    if 'user_id' not in session:
        flash("Please log in to view your cart.", "error")
        return redirect(request.referrer or url_for('home'))
    user = User.query.get(session['user_id'])
    # Handling address addition
    street = request.form.get('street')
    city = request.form.get('city')
    state = request.form.get('state')
    zip_code = request.form.get('zip_code')
    country = request.form.get('country')
    phone_number = request.form.get('phone_number')  # Optional
    label = request.form.get('label')  # Optional

    if street and city and state and zip_code and country:
        new_address = Address(
            user_id=user.id,
            street=street,
            city=city,
            state=state,
            zip_code=zip_code,
            country=country,
            phone_number=phone_number,
            label=label
        )
        db.session.add(new_address)
        db.session.commit()
        flash('Address added successfully!', 'success')
    else:
        flash('Please fill all required fields.', 'danger')
    return redirect(url_for('profile'))


@app.route('/delete_address/<int:address_id>', methods=['POST'])
def delete_address(address_id):
    if 'user_id' not in session:
        flash("Please log in to view your cart.", "error")
        return redirect(request.referrer or url_for('home'))
    user = User.query.get(session['user_id'])
    address = Address.query.get_or_404(address_id)

    if address.user_id != user.id:
        flash("You don't have permission to delete this address.", 'danger')
        return redirect(url_for('profile'))
    
    db.session.delete(address)
    db.session.commit()
    flash('Address deleted successfully!', 'success')
    return redirect(url_for('profile'))


@app.route('/shop')
def shop():
    products = Product.query.all()
    users = {user.id: user.email for user in User.query.all()} 
    return render_template('shop.html', products=products, users=users)


@app.route('/thank_you')
def thank_you():
    return render_template('thank_you.html')


# Error handler for TemplateNotFound
@app.errorhandler(TemplateNotFound)
def handle_template_not_found(error):
    return render_template('404.html'), 404  # Render a custom 404 page


@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']
    
    user = User.query.filter_by(email=email).first()
    if user and bcrypt.check_password_hash(user.password, password):
        session['user_id'] = user.id
        flash("Login successful!", "success")
        # Check if 'next' is valid; if not, default to 'home'
        next_page = request.form.get('next') or url_for('home')
        return redirect(next_page)
    else:
        flash("Invalid email or password!", "error")
        failed_login_redirect = request.form.get('next') or url_for('home')
        return redirect(f"{failed_login_redirect}?login_failed=true")


@app.route('/register', methods=['POST'])
def register():
    email = request.form['reg-email']
    password = request.form['reg-password']
    confirm_password = request.form['confirm-password']

    if password != confirm_password:
        flash("Passwords do not match!", "error")
        # Check if 'next' is valid; if not, default to 'home'
        next_page = request.form.get('next') or url_for('home')
        return redirect(next_page)

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    user = User(email=email, password=hashed_password)

    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        flash("Email already registered!", "error")
        # Check if 'next' is valid; if not, default to 'home'
        next_page = request.form.get('next') or url_for('home')
        return redirect(next_page)

    db.session.add(user)
    db.session.commit()
    session['user_id'] = user.id  # Log the user in
    flash("Registration successful! You are now logged in.", "success")
    # Check if 'next' is valid; if not, default to 'home'
    next_page = request.form.get('next') or url_for('home')
    return redirect(next_page)


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash("You have been logged out.", "success")
    return redirect(url_for('home'))


@app.route('/sell', methods=['POST'])
def sell_product():
    if 'user_id' not in session:
        # Redirect to login page or return with an error flash
        flash("You need to be logged in to sell items.", "error")
        return redirect(url_for('shop'))  # Or redirect to the shop page

    name = request.form['name']
    description = request.form['description']
    price = float(request.form['price'])
    condition = request.form['condition']
    image = request.files['image']
    user_id = session['user_id']  # Retrieve user ID from session

    if image:
        # Save the image
        filename = secure_filename(image.filename)
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image.save(image_path)

        # Create and save the new product in the database
        new_product = Product(
            name=name,
            description=description,
            price=price,
            condition=condition,
            image_filename=filename,
            user_id=user_id  # Associate the product with the user
        )
        db.session.add(new_product)
        db.session.commit()

        flash("Product listed successfully!", "success")
        return redirect(url_for('shop'))

    flash("Failed to list the product. Please try again.", "error")
    return redirect(url_for('shop'))


@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    if 'user_id' not in session:
        # Redirect to login page or return with an error flash
        flash("You need to be logged in to add items to your cart.", "error")
        return redirect(url_for('shop'))  # Or redirect to the shop page

    user_id = session['user_id']
    cart_item = Cart.query.filter_by(
        user_id=user_id, product_id=product_id).first()
    
    if cart_item:
        # Item is already in the cart, flash an error message
        flash("Item already exists in your cart!", "error")
    else:
        # Item is not in the cart, add it as a new item
        cart_item = Cart(user_id=user_id, product_id=product_id, quantity=1)
        db.session.add(cart_item)
        db.session.commit()
        flash("Item successfully added to your cart.", "success")
    
    # Redirect to the 'shop' page or another relevant page
    return redirect(url_for('shop'))


@app.route('/cart')
def cart():
    if 'user_id' not in session:
        flash("Please log in to view your cart.", "error")
        return redirect(request.referrer or url_for('home'))

    user_id = session['user_id']
    # Get all cart items for the user, along with product details
    cart_items = db.session.query(Cart, Product).join(
        Product, Cart.product_id == Product.id).filter(
            Cart.user_id == user_id).all()

    # Calculate total items and total price
    total_items = sum(cart_item.quantity for cart_item, product in cart_items)
    total_price = round(sum(
        cart_item.quantity * product.price for cart_item, 
        product in cart_items), 2)

    # Retrieve all user addresses
    user_addresses = Address.query.filter_by(user_id=user_id).all()

    # Convert Address objects to dictionaries
    serialized_addresses = [
        {
            "id": address.id,
            "street": address.street,
            "city": address.city,
            "state": address.state,
            "zip_code": address.zip_code,
            "country": address.country,
            "phone_number": address.phone_number,
            "label": address.label
        }
        for address in user_addresses
    ]

    # Pass the serialized addresses to the template
    return render_template(
        'cart.html',
        cart_items=cart_items,
        total_items=total_items,
        total_price=total_price,
        user_addresses=serialized_addresses  # Pass the serialized list
    )


@app.route('/updateitem', methods=['POST'])
def updateitem():
    if 'user_id' not in session:
        flash("Please log in to manage your cart.", "error")
        return redirect(url_for('cart'))  

    product_id = request.form.get('product_id')
    action = request.form.get('action')
    user_id = session.get('user_id')

    if action == "remove":
        # Remove the item from the cart
        Cart.query.filter_by(user_id=user_id, product_id=product_id).delete()
        db.session.commit()
        flash("Item removed from your cart.", "success")
    
    elif action == "update":
        # Update the quantity of the item in the cart
        quantity = request.form.get('quantity', type=int)
        cart_item = Cart.query.filter_by(
            user_id=user_id, product_id=product_id).first()
        if cart_item:
            cart_item.quantity = quantity
            db.session.commit()
            flash("Cart updated successfully.", "success")
    
    return redirect(url_for('cart'))


@app.route('/checkout')
def checkout():
    if 'user_id' not in session:
        flash("Please log in to checkout.", "error")
        return redirect(url_for('home'))

    user_id = session['user_id']
    cart_items = db.session.query(
        Cart, Product).join(
            Product, Cart.product_id == Product.id).filter(
                Cart.user_id == user_id).all()
    return render_template('checkout.html', cart_items=cart_items)


@app.route('/confirm_purchase', methods=['POST'])
def confirm_purchase():
    if 'user_id' not in session:
        return jsonify({"error": "User not logged in"}), 401

    user_id = session['user_id']
    address_id = request.json.get('address_id')

    try:
        # Create a new PurchaseEvent with the selected address
        purchase_event = PurchaseEvent(user_id=user_id, address_id=address_id)
        db.session.add(purchase_event)
        db.session.flush()

        # Fetch all items from the cart for the current user
        cart_items = Cart.query.filter_by(user_id=user_id).all()

        for cart_item in cart_items:
            purchase = Purchase(
                purchase_event_id=purchase_event.id,
                product_id=cart_item.product_id,
                quantity=cart_item.quantity
            )
            db.session.add(purchase)

        # Clear the cart after purchase
        Cart.query.filter_by(user_id=user_id).delete()
        
        db.session.commit()
        return jsonify(
            {"status": "success", "purchase_event_id": purchase_event.id}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
    

@app.route('/purchase_details/<int:purchase_event_id>')
def purchase_details(purchase_event_id):
    purchase_event = PurchaseEvent.query.get(purchase_event_id)

    if not purchase_event:
        return jsonify({"error": "Purchase event not found"}), 404

    response = {
        "purchase_event_id": purchase_event.id,
        "user_id": purchase_event.user_id,
        "address": {
            "street": purchase_event.address.street,
            "city": purchase_event.address.city,
            "state": purchase_event.address.state,
            "zip_code": purchase_event.address.zip_code,
            "country": purchase_event.address.country,
            "phone_number": purchase_event.address.phone_number
        },
        "purchase_date": purchase_event.purchase_date,
        "items": [
            {
                "product_id": item.product_id,
                "product_name": item.product.name,
                "quantity": item.quantity
            } for item in purchase_event.purchases
        ]
    }

    return jsonify(response), 200


@app.context_processor
def inject_user_data():
    cart_count = 0
    is_admin = False
    
    if 'user_id' in session:
        # Get cart count
        cart_count = Cart.query.filter_by(user_id=session['user_id']).count()
        
        # Check if the user is an admin
        user = User.query.get(session['user_id'])
        is_admin = user.is_admin if user else False

    return {'cart_count': cart_count, 'is_admin': is_admin}


@app.after_request
def add_cache_control_header(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        user = User.query.get(user_id)
        if not user or not user.is_admin:
            flash("Admin access required.", "error")
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/admin')
@admin_required
def admin():
    # Query all purchases and reports
    purchases = Purchase.query.all()
    reports = Report.query.order_by(Report.created_at.desc()).all()
    
    return render_template('admin.html', purchases=purchases, reports=reports)


@app.route('/generate_report')
@admin_required
def generate_report():
    # Retrieve query parameters
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')

    # Validate date inputs
    if from_date and to_date:
        try:
            from_date = datetime.strptime(from_date, '%Y-%m-%d')
            to_date = datetime.strptime(
                to_date, '%Y-%m-%d') + timedelta(days=1)  
        except ValueError:
            flash("Invalid date format. Please use YYYY-MM-DD.", "danger")
            return redirect(url_for('admin'))

        # Fetch purchase events within the specified date range
        purchase_events = PurchaseEvent.query.filter(
            PurchaseEvent.purchase_date >= from_date,
            PurchaseEvent.purchase_date < to_date
        ).all()
    else:
        purchase_events = []  # Handle case where dates are not provided

    # Generate a unique filename with a timestamp
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    file_path = f'reports/user_purchases_report_{timestamp}.csv'
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # Create and write data to CSV file
    with open(file_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        
        # Write headers for the CSV file
        writer.writerow([
            'User Email', 'User ID', 'Purchase Event ID', 'Address', 
            'Product Name', 'Quantity', 'Purchase Date'
        ])

        # Write data grouped by purchase events
        for event in purchase_events:
            # Get user and address details for each purchase event
            user_email = event.user.email
            address = f"{event.address.street}, {event.address.city}, \
                {event.address.state}, {event.address.zip_code}, \
                    {event.address.country}"
            purchase_date = event.purchase_date.strftime('%Y-%m-%d %H:%M:%S')

            # Write each item in the purchase event
            for purchase in event.purchases:
                writer.writerow([
                    user_email,
                    event.user_id,
                    event.id,
                    address,
                    purchase.product.name,
                    purchase.quantity,
                    purchase_date
                ])

    # Save report path to the database
    report = Report(file_path=file_path)
    db.session.add(report)
    db.session.commit()

    # Notify admin and redirect
    flash("Report generated successfully!", "success")
    return redirect(url_for('admin'))


@app.route('/view_report/<int:report_id>')
@admin_required
def view_report(report_id):
    report = Report.query.get(report_id)
    if report and os.path.exists(report.file_path):
        # Use csv.reader to handle quoted fields correctly
        with open(report.file_path, 'r') as file:
            reader = csv.reader(file)
            content = [row for row in reader]  # Each row is a list of values

        return render_template('view_report.html', report_content=content)
    else:
        flash("Report not found or deleted.", "error")
        return redirect(url_for('admin'))


@app.route('/download_report/<int:report_id>')
@admin_required
def download_report(report_id):
    # Retrieve the report by ID
    report = Report.query.get(report_id)
    if report and os.path.exists(report.file_path):
        return send_file(report.file_path, as_attachment=True)
    else:
        flash("Report not found or deleted.", "error")
        return redirect(url_for('admin'))


@app.route('/delete_all_reports', methods=['POST'])
@admin_required
def delete_all_reports():
    # Retrieve all reports
    reports = Report.query.all()
    
    # Loop through reports and delete each one
    for report in reports:
        if os.path.exists(report.file_path):  # Check if the file exists
            os.remove(report.file_path)  # Delete the file
        db.session.delete(report)  # Delete the report from the database
    
    db.session.commit()  # Commit the changes to the database
    
    flash("All reports have been successfully deleted.", "success")
    return redirect(url_for('admin'))


@app.route('/delete_report/<int:report_id>', methods=['POST'])
@admin_required
def delete_report(report_id):
    report = Report.query.get(report_id)
    if report:
        file_path = report.file_path
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        db.session.delete(report)
        db.session.commit()
        flash("Report and file deleted successfully.", "success")
    else:
        flash("Report not found.", "error")
    return redirect(url_for('admin'))


fake = Faker()


@app.route('/add_sample_products', methods=['POST'])
@admin_required
def add_sample_products():
    # Generate a random number of products between 3 and 8
    num_products = random.randint(3, 8)
    sample_conditions = ["New", "Like New", "Used"]
    sample_images = [
        "sample1.jpg", "sample2.jpg", "sample3.jpg", "sample4.jpg"] 

    # Get the logged-in user's ID
    user_id = session['user_id']

    new_products = []
    
    for _ in range(num_products):
        product = Product(
            name=fake.word().capitalize() + " " + fake.word().capitalize(),
            description=fake.sentence(nb_words=10),
            price=round(fake.random_number(digits=3), 2), 
            condition=random.choice(sample_conditions),
            image_filename=secure_filename(random.choice(sample_images)),
            user_id=user_id  # Assign the logged-in user's ID to the product
        )
        db.session.add(product)
        new_products.append(product)

    # Commit all new products to the database
    db.session.commit()

    flash(f"Successfully added {num_products} sample products.", "success")
    return redirect(url_for('admin'))


@app.route('/delete_all_products', methods=['POST'])
@admin_required
def delete_all_products():
    product_ids = [product.id for product in Product.query.all()]
    # Delete all entries from the Product table
    num_deleted = Product.query.delete()
    # Delete corresponding cart items with those product IDs
    Cart.query.filter(Cart.product_id.in_(product_ids)).delete(
        synchronize_session=False)
    # Commit changes to the database
    db.session.commit()
    flash(f"Successfully deleted {num_deleted} \
          products and corresponding cart entries from the database.", 
          "success")
    return redirect(url_for('admin'))
    

@app.route('/delete_all_purchases', methods=['POST'])
@admin_required
def delete_all_purchases():
    # Delete all entries from the Purchase and PurchaseEvent tables
    num_deleted_purchases = Purchase.query.delete()
    num_deleted_events = PurchaseEvent.query.delete()
    # Commit changes to the database
    db.session.commit()
    flash(f"Successfully deleted {num_deleted_purchases} \
            purchase entries and {num_deleted_events} purchase event entries\
            from the database.", "success")
    return redirect(url_for('admin'))


@app.route('/toggle_admin')
def toggle_admin():
    if 'user_id' not in session:
        flash("You need to be logged in to toggle admin status.", "error")
        return redirect(url_for('home'))
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    if user:
        # Toggle the admin status
        user.is_admin = not user.is_admin
        db.session.commit()
        status = "now an admin" if user.is_admin else "no longer an admin"
        flash(f"You are {status}!", "success")
    else:
        flash("User not found.", "error")
    
    return redirect(request.referrer or url_for('home'))


@app.route('/add_sample_address')
def add_sample_address():
    if 'user_id' not in session:
        flash("Please log in to manage your addresses.", "error")
        return redirect(url_for('home'))
    sample_address = Address(
        user_id=1,
        street="123 Maple Street",
        city="Sample City",
        state="Sample State",
        zip_code="12345",
        country="Sampleland",
        phone_number="123-456-7890",
        label="Home"
    )

    # Add the address to the session and commit to save it in the database
    db.session.add(sample_address)
    db.session.commit()

    flash("Sample address added successfully!", "success")
    return redirect(request.referrer or url_for('home'))


if __name__ == '__main__':
    app.run(debug=True)