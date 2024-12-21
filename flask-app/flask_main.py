from flask import Flask, render_template, request, redirect, url_for, session, flash
import pymysql
from dotenv import load_dotenv
import os
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from email_validator import validate_email, EmailNotValidError

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')  # Secret key for session management

# Initialize LoginManager and Bcrypt
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.unauthorized_handler
def unauthorized():
    flash('Please log in to access the page.', 'danger')
    return redirect(url_for('login'))

bcrypt = Bcrypt(app)

# MySQL connection setup
def get_db_connection():
    return pymysql.connect(
        host=os.getenv('DB_HOST'),
        port=int(os.getenv('DB_PORT')),
        user=os.getenv('DB_USERNAME'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME'),
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

# User class
class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
    user_data = cursor.fetchone()
    conn.close()
    if user_data:
        return User(user_data['id'], user_data['username'])
    return None

@app.route('/')
@login_required
def home():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(cve_number) AS cve_count FROM ca_cve')
        cve_Counter = cursor.fetchone()['cve_count']
        cursor.execute('SELECT * FROM ca_cve ORDER BY cve_id ASC')
        cve_data = cursor.fetchall()
        cursor.execute('SELECT SUM(campaignSentCount) AS TotalEmailSentCount FROM ca_cve_emailSentCount')
        cve_emailSentCount = cursor.fetchone()['TotalEmailSentCount']
        cursor.execute('SELECT COUNT(news_pubdate) AS news_count FROM ca_news')
        news_Counter = cursor.fetchone()['news_count']
        cursor.execute('SELECT * FROM ca_news ORDER BY news_id ASC')
        news_data = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template("index.html", cve_data=cve_data, cve_Counter=cve_Counter, cve_emailSentCount=cve_emailSentCount, news_Counter=news_Counter, news_data=news_data)
    
    except Exception as e:
        print(f"500 Server Error: {e}")
        return f"500 Server Error: {e}", 500

# Login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        user_data = cursor.fetchone()
        conn.close()

        if user_data and bcrypt.check_password_hash(user_data['password_hash'], password):
            user = User(user_data['id'], user_data['username'])
            login_user(user)
            session['username'] = username
            return redirect(url_for('home'))
        else:
            flash('Invalid credentials. Please try again.', 'danger')

    return render_template('login.html')

# Logout route
@app.route('/logout')
def logout():
    logout_user()
    session.clear()
    return redirect(url_for('login'))

@app.route('/profile')
@login_required
def profile():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        username = session['username']
        cursor.execute('SELECT * from users WHERE username = %s', (username))
        user_data = cursor.fetchall()
        cursor.close()
        conn.close()
        if user_data:
            return render_template("profile.html", user_data=user_data)
        else:
            return redirect(url_for('/'))
    except Exception as e:
        return f"500 Server Error: {e}", 500

@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    try:
        if 'username' not in request.form or 'password' not in request.form:
            flash('Missing form fields. Please try again.', 'danger')
            return redirect(url_for('profile'))  

        current_username = session.get('username')
        new_username = request.form['username'].strip()
        new_password = request.form['password'].strip()
        if not new_username:
            flash('Username cannot be empty. Please try again.', 'danger')
            return redirect(url_for('profile'))
        conn = get_db_connection()
        cursor = conn.cursor()
        # Check for duplicate username
        if new_username != current_username:
            cursor.execute('SELECT * FROM users WHERE username = %s', (new_username,))
            existing_user = cursor.fetchone()
            if existing_user:
                flash('Error: Username already exists. Please choose another one.', 'danger')
                return redirect(url_for('profile'))
        # Update username
        if new_username != current_username:
            cursor.execute('UPDATE users SET username = %s WHERE username = %s', (new_username, current_username))
            session['username'] = new_username
        # Update password if provided
        if new_password:
            hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
            cursor.execute('UPDATE users SET password_hash = %s WHERE username = %s', (hashed_password, new_username))

        conn.commit()
        cursor.close()
        conn.close()

        logout_user()
        session.clear()

        flash('Profile updated successfully! Login to continue', 'success')
        return redirect(url_for('login'))

    except Exception as e:
        print(f"500 Server Error: {e}")
        flash(f'An unexpected error occurred: {e}', 'danger')
        return redirect(url_for('profile'))

@app.route('/email_list')
@login_required
def email_list():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM ca_emailList')
        email_data = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('email-List.html', email_data=email_data)
    except Exception as e:
        flash(f'An unexpected error occurred: {e}', 'danger')
        return redirect(url_for('email_list'))

@app.route('/addEmail', methods=['POST'])
@login_required
def addEmail():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        name = request.form['name'].strip()
        email = request.form['email'].strip()
        try:
            validate_email(email)
        except EmailNotValidError as e:
            flash(f'Invalid email format: {e}', 'danger')
            return redirect(url_for('email_list'))
        cursor.execute('SELECT email from ca_emailList WHERE email = %s', (email))
        email_exist_check = cursor.fetchone()
        if email_exist_check:
            flash('Email Already Exists!', 'danger')
            return redirect(url_for('email_list'))
        else:
            cursor.execute('INSERT INTO ca_emailList (name, email) VALUES (%s, %s)', (name, email))
            conn.commit()
            flash('Email successfully added!', 'success')
            return redirect(url_for('email_list'))
    except Exception as e:
        flash('Error: Something went wrong unable to add new mail', 'danger')
        return redirect(url_for('email_list'))
    finally:
        cursor.close()
        conn.close()

@app.route('/deleteEmail', methods=['GET'])
@login_required
def deleteEmail():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        email = request.args.get('email').strip()
        cursor.execute('SELECT email from ca_emailList WHERE email = %s', (email))
        email_exist_check = cursor.fetchone()
        if not email_exist_check:
            flash('Email not found!', 'danger')
            return redirect(url_for('email_list'))
        else:
            cursor.execute('DELETE from ca_emailList WHERE email = %s', (email))
            conn.commit()

            flash('Email deleted successfully!', 'success')
            return redirect(url_for('email_list'))
    except Exception as e:
        # Handle any errors that occur during the process
        flash('An error occurred. Please try again.', 'danger')
        return redirect(url_for('email_list'))

    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    app.run(port=8080, debug=True)