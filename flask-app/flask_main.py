from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, jsonify
import pymysql
from dotenv import load_dotenv
import os
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from email_validator import validate_email, EmailNotValidError
from werkzeug.utils import secure_filename
import csv
from html_sanitizer import Sanitizer
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from makeCampaign import makeCampaign
from makeEmailTemplate import render_email_template

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')  # Secret key for session management

ALLOWED_EXTENSIONS = {'csv'}
UPLOAD_FOLDER = 'uploads/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
        flash('An error occurred. Please try again.', 'danger')
        return redirect(url_for('email_list'))
    finally:
        cursor.close()
        conn.close()

@app.route('/uploadEmails', methods=['POST'])
@login_required
def uploadEmails():
    if 'emailfile' not in request.files:
        flash('No file part!', 'danger')
        return redirect(url_for('email_list'))
    file = request.files['emailfile']
    if file.filename == '':
        flash('No selected file!', 'danger')
        return redirect(url_for('email_list'))
    if not allowed_file(file.filename):
        flash('Invalid file format! Only .csv files are allowed.', 'danger')
        return redirect(url_for('email_list'))
    # Sanitize the filename
    filename = secure_filename(file.filename)
    try:
        # Save the file temporarily
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        # Validate file content as a CSV
        with open(filepath, 'r') as csvfile:
            csv_reader = csv.reader(csvfile)
            header = next(csv_reader)
            if header != ['Name', 'Email']:
                flash('Invalid CSV format! Expected columns: Name, Email.', 'danger')
                os.remove(filepath)  # Delete the invalid file
                return redirect(url_for('email_list'))
            # Collect valid rows from the file
            unique_emails = set()
            rows_to_insert = []
            for row in csv_reader:
                if len(row) < 2:
                    continue 
                name, email = row[0].strip(), row[1].strip()

                # Validate email - it is mandatory
                if not email:
                    flash('Email cannot be empty. Please try again!', 'danger')
                    os.remove(filepath)
                    return redirect(url_for('email_list'))
                try:
                    validate_email(email)
                except EmailNotValidError as e:
                    flash(f'Invalid email format: {e}', 'danger')
                    os.remove(filepath)
                    return redirect(url_for('email_list'))

                if email not in unique_emails:
                    unique_emails.add(email)
                    rows_to_insert.append((name, email))
            conn = get_db_connection()
            cursor = conn.cursor()
            for name, email in rows_to_insert:
                try:
                    cursor.execute('INSERT IGNORE INTO ca_emailList (name, email) VALUES (%s, %s)', (name, email))
                except Exception as e:
                    flash(f'Error inserting {email}: {e}', 'danger')
            conn.commit()
            cursor.close()
            conn.close()
        flash('File uploaded and processed successfully!', 'success')
    except Exception as e:
        flash(f'Error processing file: {e}', 'danger')
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)

    return redirect(url_for('email_list'))

@app.route('/getSampleFile', methods=['GET'])
@login_required
def getSampleFile():
    try:
        return send_from_directory(directory='static/sample', path='sample.csv', as_attachment=True)
    except Exception as e:
        flash(f"Error downloading sample file: {e}", "danger")
        return redirect(url_for('email_list'))

@app.route('/template',methods=['GET'])
@login_required
def template():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(id) AS template_count from templates')
        template_count = cursor.fetchone()['template_count']
        cursor.execute('SELECT * from templates')
        template_data = cursor.fetchall()
        return render_template("template.html", template_data=template_data, template_count=template_count)
    except Exception as e:
        flash(f"Something went wrong!: {e}", "danger")
    finally:
        conn.close()
        cursor.close()

@app.route('/saveTemplate', methods=['POST'])
@login_required
def saveTemplate():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        template_name = request.form['templateName'].strip()
        template_content = request.form['templateContent']
        if not template_name:
            flash('Template name cannot be empty.', 'danger')
            return redirect(url_for('template'))
        if not template_content:
            flash('Template content cannot be empty.', 'danger')
            return redirect(url_for('template'))
        if "(_start)" not in template_content or "(_end)" not in template_content:
            flash('Template content must contain "(_start)" and "(_end)"', 'danger')
            return redirect(url_for('template'))
        cursor.execute('SELECT template_name FROM templates WHERE template_name = %s', (template_name,))
        result = cursor.fetchone()
        if result:
            flash('Template name already exists. Please choose a different name.', 'warning')
            return redirect(url_for('template'))
        cursor.execute('''INSERT INTO templates (template_name, template_content)VALUES (%s, %s)''', (template_name, template_content))
        conn.commit()
        flash('Template saved successfully!', 'success')
    except Exception as e:
        flash(f'Error saving template: {e}', 'danger')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('template'))

@app.route('/delTemplate', methods=['GET'])
@login_required
def delTemplate():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        template_id = request.args.get('template_id').strip()
        cursor.execute("SELECT id from templates where id = %s", (template_id,))
        template_exist_check = cursor.fetchone()
        if not template_exist_check:
            flash("Template Not Found!","danger")
            return redirect(url_for('template'))
        else:
            cursor.execute("DELETE from templates where id = %s", (template_id,))
            conn.commit()
            flash("Template Deleted Successfully!","success")
            return redirect(url_for('template'))
    except Exception as e:
        flash(f"Something went wrong: {e}", "danger")
        return redirect(url_for('template'))
    finally:
        conn.close()
        cursor.close()

@app.route('/editTemplate', methods=['GET'])
@login_required
def editTemplate():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        template_id = request.args.get('template_id').strip()
        cursor.execute("SELECT id from templates where id = %s", (template_id,))
        template_exist_check = cursor.fetchone()
        if not template_exist_check:
            flash("Template Not Found!","danger")
            return redirect(url_for('template'))
        else:
            cursor.execute("SELECT * from templates where id= %s", (template_id,))
            template_data = cursor.fetchone()
            if template_data:
                return render_template('editTemplate.html', template_data=template_data)
            else:
                flash("Template details could not be retrieved.", "danger")
                return redirect(url_for('template'))
    except Exception as e:
        flash(f"Something went wrong: {e}", "danger")
        return redirect(url_for("template"))
    finally:
        conn.close()
        cursor.close()

@app.route('/saveEditTemplate', methods=['POST'])
@login_required
def saveEditTemplate():
    try:
        template_name = request.form['templateName'].strip()
        template_content = request.form['templateContent'].strip()
        template_id = request.form['templateID'].strip()
        if not template_name:
            flash("Template Name cannot be empty!", "danger")
            return redirect(url_for("editTemplate"))
        if not template_content:
            flash("Template content cannot be empty!", "danger")
            return redirect(url_for("editTemplate"))
        if "(_start)" not in template_content or "(_end)" not in template_content:
            flash('Template content must contain "(_start)" and "(_end)"', 'danger')
            return redirect(url_for('editTemplate'))
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM templates WHERE id = %s", (template_id, ))
        template_exist_check = cursor.fetchone()
        if template_exist_check:
            cursor.execute("UPDATE templates SET template_name = %s, template_content = %s WHERE id = %s", 
                (template_name, template_content, template_id))
            conn.commit()
            flash("Template updated successfully!", "success")
            return redirect(url_for('template'))
        else:
            flash("Template Not Found", "danger")
            return redirect(url_for('editTemplate'))
    except Exception as e:
        flash(f"Something went wrong: {e}", "danger")
        return redirect(url_for("template"))
    finally:
        conn.close()
        cursor.close()

@app.route('/addCVEQueue', methods=['GET'])
@login_required
def addCVEQueue():
    conn = None
    cursor = None
    try:
        cve_id = request.args.get('cve_id').strip()
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT cve_queue_stat FROM ca_cve WHERE cve_id = %s", (cve_id,))
        exist_queue_status = cursor.fetchone()
        if not exist_queue_status:
            return jsonify({"status": "error", "message": "CVE Not Found!"})
        queue_status = int(exist_queue_status['cve_queue_stat'])
        if queue_status == 1:
            cursor.execute("UPDATE ca_cve SET cve_queue_stat = '0' WHERE cve_id = %s", (cve_id,))
            conn.commit()
            return jsonify({"status": "success", "message": "CVE successfully removed from the queue!", "queue_status": "0"})
        elif queue_status == 0:
            cursor.execute("UPDATE ca_cve SET cve_queue_stat = '1' WHERE cve_id = %s", (cve_id,))
            conn.commit()
            return jsonify({"status": "success", "message": "CVE successfully added to the queue!", "queue_status": "1"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/addNewsQueue', methods=['GET'])
@login_required
def addNewsQueue():
    conn = None
    cursor = None
    try:
        news_id = request.args.get('news_id').strip()
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT news_queue_stat FROM ca_news WHERE news_id = %s", (news_id,))
        exist_queue_status = cursor.fetchone()
        if not exist_queue_status:
            return jsonify({"status": "error", "message": "News Not Found!"})
        queue_status = int(exist_queue_status['news_queue_stat'])
        if queue_status == 1:
            cursor.execute("UPDATE ca_news SET news_queue_stat = '0' WHERE news_id = %s", (news_id,))
            conn.commit()
            return jsonify({"status": "success", "message": "News successfully removed from the queue!", "queue_status": "0"})
        elif queue_status == 0:
            cursor.execute("UPDATE ca_news SET news_queue_stat = '1' WHERE news_id = %s", (news_id,))
            conn.commit()
            return jsonify({"status": "success", "message": "News successfully added to the queue!", "queue_status": "1"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/getcampaign', methods=['GET'])
@login_required
def getcampaign():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT * from ca_cve WHERE cve_queue_stat = '1' ORDER BY cve_id")
        campaign_data = cursor.fetchall()
        cursor.execute("SELECT * from ca_news WHERE news_queue_stat = '1' ORDER BY news_id")
        news_data = cursor.fetchall()
        return render_template("campaign.html", campaign_data=campaign_data, news_data=news_data)
    except Exception as e:
        flash(f"Something went wrong: {e}", "danger")
        return redirect(url_for("home"))
    finally:
        conn.close()
        cursor.close()

@app.route('/removeCVEQueue', methods=['GET'])
@login_required
def removeCVEQueue():
    conn = None
    cursor = None
    try:
        cve_id = request.args.get('cve_id').strip()
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT cve_queue_stat FROM ca_cve WHERE cve_id = %s", (cve_id,))
        exist_queue_status = cursor.fetchone()
        if not exist_queue_status:
            return jsonify({"status": "error", "message": "CVE not found in the database!"})
        queue_status = int(exist_queue_status['cve_queue_stat'])
        if queue_status == 1:
            cursor.execute("UPDATE ca_cve SET cve_queue_stat = '0' WHERE cve_id = %s", (cve_id,))
            conn.commit()
            return jsonify({"status": "success", "message": "CVE successfully removed from the queue!"})
        else:
            return jsonify({"status": "error", "message": "CVE is not queued!"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
    finally:
        cursor.close()
        conn.close()

@app.route('/removeNewsQueue', methods=['GET'])
@login_required
def removeNewsQueue():
    conn = None
    cursor = None
    try:
        news_id = request.args.get('news_id').strip()
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT news_queue_stat FROM ca_news WHERE news_id = %s", (news_id,))
        exist_queue_status = cursor.fetchone()
        if not exist_queue_status:
            return jsonify({"status": "error", "message": "News not found in the database!"})
        queue_status = int(exist_queue_status['news_queue_stat'])
        if queue_status == 1:
            cursor.execute("UPDATE ca_news SET news_queue_stat = '0' WHERE news_id = %s", (news_id,))
            conn.commit()
            return jsonify({"status": "success", "message": "News successfully removed from the queue!"})
        else:
            return jsonify({"status": "error", "message": "News is not queued!"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
    finally:
        cursor.close()
        conn.close()

@app.route("/fetchTemplates", methods=['GET'])
@login_required
def fetchTemplates():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT id, template_name FROM templates")
        template_data = cursor.fetchall()
        if not template_data:
            return jsonify({"status": "error", "message": "No templates found"}), 404
        return jsonify({"status": "success", "templates": template_data}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": f"Something went wrong: {e}"}), 500

@app.route("/sendEmails", methods=["POST"])
@login_required
def send_emails():
    try:
        data = request.json
        items = data.get("items", [])
        template_id = data.get("template_id")
        if not items or not template_id:
            return jsonify({"status": "error", "message": "Missing items or template ID."}), 400
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT template_content FROM templates WHERE id = %s", (template_id,))
        result = cursor.fetchone()
        if not result:
            return jsonify({"status": "error", "message": "Template not found."}), 404
        
        template = result.get("template_content")
        email_data = []
        for item in items:
            item_id = item.get("id")
            item_type = item.get("type")
            if not item_id or not item_type:
                continue
            email_data_temp = []
            if item_type == "cve":
                cursor.execute("SELECT cve_number from ca_cve WHERE cve_id = %s AND ca_type='cve'", (item_id))
                exist_type_check = cursor.fetchone()
                if exist_type_check:
                    cursor.execute(""" SELECT cve_number AS cve_number, 
                                    cve_name AS title, 
                                    cve_description AS description, 
                                    cve_link AS link, 
                                    cve_severity AS severity, 
                                    cve_pubdate AS pub_date FROM ca_cve WHERE cve_id = %s""",
                    (item_id,))
                    email_data_temp = cursor.fetchall()
            elif item_type == "news":
                cursor.execute("SELECT news_title from ca_news WHERE news_id = %s AND ca_type='news'", (item_id))
                exist_type_check = cursor.fetchone()
                if exist_type_check:
                    cursor.execute("""SELECT news_id AS id, 
                                    news_title AS title, 
                                    news_description AS description, 
                                    news_link AS link, 
                                    news_bannerUrl AS img_URL,
                                    news_pubdate AS pub_date FROM ca_news WHERE news_id = %s""", 
                    (item_id,))
                    email_data_temp = cursor.fetchall()
            else:
                email_data_temp = []

            if email_data_temp:
                email_data.extend(email_data_temp)

        if not email_data:
            return jsonify({"status": "error", "message": "No data found for the selected items."}), 400
        rendered_email = render_email_template(template, email_data)

        if rendered_email=="Missing (_start) or (_end) in the template":
            return jsonify({"status":"error","message":"Missing (_start) or (_end) in the template"})

        return jsonify({"status": "success", "message": "Emails sent successfully."}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        conn.close()
        cursor.close()

if __name__ == '__main__':
    app.run(port=8080, debug=True)