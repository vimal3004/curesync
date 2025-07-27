from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
import hashlib
from datetime import datetime, date
import os
from flask_mail import Mail, Message
import os
from werkzeug.utils import secure_filename



app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'vimalthulasiraj008@gmail.com'
app.config['MAIL_PASSWORD'] = 'mdrg dixp yqby psul'  # Use app password, not your Gmail password

mail = Mail(app)

# Database setup
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            phone TEXT,
            is_admin INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    doctor_id INTEGER NOT NULL,
    rating INTEGER CHECK(rating >= 1 AND rating <= 5),
    comments TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (doctor_id) REFERENCES doctors(id)
)
''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS doctors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            specialization TEXT NOT NULL,
            experience INTEGER,
            fee INTEGER NOT NULL,
            available_days TEXT,
            available_time TEXT,
            room_id INTEGER,
            FOREIGN KEY (room_id) REFERENCES rooms (id)
        )
    ''')

    
    # In init_db() in app.py
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS health_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        appointment_id INTEGER NOT NULL,
        filename TEXT NOT NULL,
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (appointment_id) REFERENCES appointments(id)
    )
''')

    # Rooms table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_number TEXT NOT NULL,
            room_type TEXT NOT NULL,
            capacity INTEGER,
            facilities TEXT,
            status TEXT DEFAULT 'available'
        )
    ''')

   
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        doctor_id INTEGER NOT NULL,
        room_id INTEGER,
        appointment_date DATE NOT NULL,
        appointment_time TIME NOT NULL,
        status TEXT DEFAULT 'pending',
        payment_status TEXT DEFAULT 'pending',
        notes TEXT,
        token_number INTEGER,
        health_record TEXT,  
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (doctor_id) REFERENCES doctors (id),
        FOREIGN KEY (room_id) REFERENCES rooms (id)
    )
''')


        # Insert sample data
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        admin_password = hashlib.sha256('admin123'.encode()).hexdigest()
        cursor.execute('''
            INSERT INTO users (name, email, password, phone, is_admin)
            VALUES ('Admin User', 'admin@hospital.com', ?, '1234567890', 1)
        ''', (admin_password,))

        user_password = hashlib.sha256('user123'.encode()).hexdigest()
        cursor.execute('''
            INSERT INTO users (name, email, password, phone)
            VALUES ('John Doe', 'john@email.com', ?, '9876543210')
        ''', (user_password,))

        doc_password = hashlib.sha256('doc123'.encode()).hexdigest()

        doctors = [
            ('Dr. Sarah Johnson', 'sarah@hospital.com', doc_password, 'Cardiologist', 10, 500, 'Mon,Wed,Fri', '9:00-17:00', 1),
            ('Dr. Mike Chen', 'mike@hospital.com', doc_password, 'Neurologist', 8, 600, 'Tue,Thu,Sat', '10:00-18:00', 2),
            ('Dr. Emily Davis', 'emily@hospital.com', doc_password, 'Pediatrician', 5, 400, 'Mon,Tue,Wed,Thu,Fri', '8:00-16:00', 3)
        ]

        cursor.executemany('''
            INSERT INTO doctors (name, email, password, specialization, experience, fee, available_days, available_time, room_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', doctors)

        rooms = [
            ('101', 'Consultation', 2, 'Basic examination equipment', 'available'),
            ('102', 'Specialist', 3, 'Advanced diagnostic tools', 'available'),
            ('103', 'Pediatric', 4, 'Child-friendly equipment', 'available'),
            ('201', 'Surgery', 8, 'Operating theater', 'available')
        ]
        cursor.executemany('''
            INSERT INTO rooms (room_number, room_type, capacity, facilities, status)
            VALUES (?, ?, ?, ?, ?)
        ''', rooms)

        conn.commit()
        conn.close()

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def is_logged_in():
    return 'user_id' in session

def is_admin():
    return session.get('is_admin', False)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = hash_password(request.form['password'])

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ? AND password = ?', (email, password)).fetchone()
        conn.close()

        if user:
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['is_admin'] = user['is_admin']
            return redirect(url_for('admin_panel') if user['is_admin'] else url_for('dashboard'))
        else:
            flash('Invalid email or password')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = hash_password(request.form['password'])
        phone = request.form['phone']

        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (name, email, password, phone) VALUES (?, ?, ?, ?)', (name, email, password, phone))
            conn.commit()
            flash('Registration successful! Please login.')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Email already exists!')
        finally:
            conn.close()

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/dashboard')
def dashboard():
    if not is_logged_in():
        return redirect(url_for('login'))

    conn = get_db_connection()
    appointments = conn.execute('''
        SELECT a.*, d.name as doctor_name, d.specialization, r.room_number
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.id
        LEFT JOIN rooms r ON a.room_id = r.id
        WHERE a.user_id = ?
        ORDER BY a.appointment_date DESC, a.appointment_time DESC
    ''', (session['user_id'],)).fetchall()
    conn.close()

    return render_template('dashboard.html', appointments=appointments)

@app.route('/doctors')
def doctors():
    conn = get_db_connection()
    doctors = conn.execute('''
        SELECT d.*, r.room_number
        FROM doctors d
        LEFT JOIN rooms r ON d.room_id = r.id
        ORDER BY d.name
    ''').fetchall()
    conn.close()
    return render_template('doctors.html', doctors=doctors)

@app.route('/rooms')
def rooms():
    conn = get_db_connection()
    rooms = conn.execute('SELECT * FROM rooms ORDER BY room_number').fetchall()
    conn.close()
    return render_template('rooms.html', rooms=rooms)

@app.route('/appointment', methods=['GET', 'POST'])
def appointment():
    if not is_logged_in():
        return redirect(url_for('login'))

    conn = get_db_connection()

    if request.method == 'POST':
        if 'book_appointment' in request.form:
            doctor_id = request.form['doctor_id']
            appointment_date = request.form['appointment_date']
            appointment_time = request.form['appointment_time']
            notes = request.form.get('notes', '')

            # Check if slot is already booked
            existing = conn.execute('''
                SELECT COUNT(*) FROM appointments 
                WHERE doctor_id = ? AND appointment_date = ? AND appointment_time = ?
                AND status != 'cancelled'
            ''', (doctor_id, appointment_date, appointment_time)).fetchone()[0]

            if existing > 0:
                flash('This time slot is already booked!')
                doctors = conn.execute('SELECT * FROM doctors ORDER BY name').fetchall()
                conn.close()
                return render_template('appointment.html', doctors=doctors, step='book')

            # Generate token number
            max_token = conn.execute('''
                SELECT MAX(token_number) FROM appointments
                WHERE doctor_id = ? AND appointment_date = ?
            ''', (doctor_id, appointment_date)).fetchone()[0]
            token_number = (max_token or 0) + 1

            # Get doctor info
            doctor = conn.execute('SELECT * FROM doctors WHERE id = ?', (doctor_id,)).fetchone()

            # Insert appointment
            cursor = conn.execute('''
                INSERT INTO appointments (user_id, doctor_id, room_id, appointment_date, appointment_time, notes, token_number)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (session['user_id'], doctor_id, doctor['room_id'], appointment_date, appointment_time, notes, token_number))
            appointment_id = cursor.lastrowid
            conn.commit()

            # Send email notification
            user_email = conn.execute('SELECT email FROM users WHERE id = ?', (session['user_id'],)).fetchone()['email']
            try:
                msg = Message(
                    subject="Appointment Confirmation - MedBook",
                    sender=app.config['MAIL_USERNAME'],
                    recipients=[user_email],
                    body=f"""Dear {session['user_name']},

Your appointment with {doctor['name']} on {appointment_date} at {appointment_time} is confirmed.

Thanks,
MedBook Team"""
                )
                mail.send(msg)
            except Exception as e:
                print(f"Email send failed: {e}")

            # Fetch appointment to show confirmation
            appointment = conn.execute('''
                SELECT a.*, d.name as doctor_name, d.specialization, d.fee, r.room_number
                FROM appointments a
                JOIN doctors d ON a.doctor_id = d.id
                LEFT JOIN rooms r ON a.room_id = r.id
                WHERE a.id = ?
            ''', (appointment_id,)).fetchone()

            conn.close()
            return render_template('appointment.html', appointment=appointment, step='confirm')

        elif 'confirm_booking' in request.form:
            appointment_id = request.form['appointment_id']
            conn.execute('UPDATE appointments SET status = "confirmed" WHERE id = ? AND user_id = ?', (appointment_id, session['user_id']))
            conn.commit()
            conn.close()
            return redirect(url_for('payment', appointment_id=appointment_id))

    # GET method – show doctor list
    doctors = conn.execute('SELECT * FROM doctors ORDER BY name').fetchall()
    conn.close()
    return render_template('appointment.html', doctors=doctors, step='book')

@app.route('/payment/<int:appointment_id>')
def payment(appointment_id):
    if not is_logged_in():
        return redirect(url_for('login'))

    conn = get_db_connection()
    appointment = conn.execute('''
        SELECT a.*, d.name as doctor_name, d.specialization, d.fee, r.room_number
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.id
        LEFT JOIN rooms r ON a.room_id = r.id
        WHERE a.id = ? AND a.user_id = ?
    ''', (appointment_id, session['user_id'])).fetchone()
    conn.close()

    if not appointment:
        flash('Appointment not found!')
        return redirect(url_for('dashboard'))

    return render_template('payment.html', appointment=appointment)

@app.route('/process_payment', methods=['POST'])
def process_payment():
    if not is_logged_in():
        return redirect(url_for('login'))

    appointment_id = request.form['appointment_id']
    conn = get_db_connection()
    conn.execute('''
        UPDATE appointments 
        SET payment_status = 'paid', status = 'confirmed'
        WHERE id = ? AND user_id = ?
    ''', (appointment_id, session['user_id']))
    conn.commit()
    conn.close()

    flash('Payment successful! Your appointment is confirmed.')
    return redirect(url_for('dashboard'))

@app.route('/token_queue', methods=['GET', 'POST'])
def token_queue():
    if not is_logged_in() or not is_admin():
        return redirect(url_for('login'))

    selected_date = request.form.get('selected_date') if request.method == 'POST' else datetime.today().strftime('%Y-%m-%d')

    conn = get_db_connection()
    doctors = conn.execute('SELECT id, name FROM doctors').fetchall()

    token_data = {}
    for doc in doctors:
        appointments = conn.execute('''
            SELECT a.token_number, u.name AS patient_name, a.appointment_time, a.status, a.notes
            FROM appointments a
            JOIN users u ON a.user_id = u.id
            WHERE a.doctor_id = ? AND a.appointment_date = ?
            ORDER BY a.token_number
        ''', (doc['id'], selected_date)).fetchall()

        token_data[doc['name']] = appointments

    conn.close()
    return render_template('token_queue.html', token_data=token_data, selected_date=selected_date)


@app.route('/manage_schedule', methods=['GET', 'POST'])
def manage_schedule():
    if not is_logged_in() or not is_admin():
        return redirect(url_for('login'))

    conn = get_db_connection()

    if request.method == 'POST':
        doctor_id = request.form['doctor_id']
        available_days = request.form['available_days']
        available_time = request.form['available_time']
        conn.execute('''
            UPDATE doctors SET available_days = ?, available_time = ?
            WHERE id = ?
        ''', (available_days, available_time, doctor_id))
        conn.commit()
        flash('Schedule updated successfully.')

    doctors = conn.execute('SELECT * FROM doctors').fetchall()
    conn.close()
    return render_template('manage_schedule.html', doctors=doctors)


@app.route('/admin_panel')
def admin_panel():
    if not is_logged_in() or not is_admin():
        return redirect(url_for('login'))

    conn = get_db_connection()

    total_appointments = conn.execute('SELECT COUNT(*) FROM appointments').fetchone()[0]
    total_doctors = conn.execute('SELECT COUNT(*) FROM doctors').fetchone()[0]
    total_rooms = conn.execute('SELECT COUNT(*) FROM rooms').fetchone()[0]
    total_users = conn.execute('SELECT COUNT(*) FROM users WHERE is_admin = 0').fetchone()[0]

    selected_date = request.args.get('filter_date')
    if not selected_date:
        selected_date = date.today().isoformat()

    appointments = conn.execute('''
        SELECT a.*, u.name AS user_name, d.name AS doctor_name, r.room_number
        FROM appointments a
        JOIN users u ON a.user_id = u.id
        JOIN doctors d ON a.doctor_id = d.id
        LEFT JOIN rooms r ON a.room_id = r.id
        WHERE a.appointment_date = ?
        ORDER BY a.token_number ASC
    ''', (selected_date,)).fetchall()

    conn.close()

    stats = {
        'total_appointments': total_appointments,
        'total_doctors': total_doctors,
        'total_rooms': total_rooms,
        'total_users': total_users
    }

    return render_template('admin_panel.html', stats=stats, appointments=appointments, selected_date=selected_date)

@app.route('/doctor/login', methods=['GET', 'POST'])
def doctor_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        doctor = conn.execute('SELECT * FROM doctors WHERE email = ?', (email,)).fetchone()
        conn.close()

        if doctor and doctor['password'] == hashlib.sha256(password.encode()).hexdigest():
            session['doctor_id'] = doctor['id']
            session['doctor_name'] = doctor['name']
            return redirect(url_for('doctor_dashboard'))
        else:
            flash("Invalid credentials.")
    
    return render_template('doctor_login.html')



@app.route('/doctor/dashboard')
def doctor_dashboard():
    if 'doctor_id' not in session:
        return redirect(url_for('doctor_login'))

    today = datetime.today().date()

    conn = get_db_connection()
    appointments = conn.execute('''
        SELECT a.*, u.name AS patient_name, r.room_number
        FROM appointments a
        JOIN users u ON a.user_id = u.id
        LEFT JOIN rooms r ON a.room_id = r.id
        WHERE a.doctor_id = ? AND a.appointment_date = ?
        ORDER BY a.appointment_time
    ''', (session['doctor_id'], today)).fetchall()
    conn.close()

    return render_template('doctor_dashboard.html', appointments=appointments)
@app.route('/doctor/upload_notes/<int:appointment_id>', methods=['POST'])
def upload_notes(appointment_id):
    if 'doctor_id' not in session:
        return redirect(url_for('doctor_login'))

    file = request.files['notes_file']
    if file:
        filename = secure_filename(file.filename)
        upload_folder = os.path.join('static', 'uploads')  # or use UPLOAD_FOLDER in config
        os.makedirs(upload_folder, exist_ok=True)
        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)

        conn = get_db_connection()
        conn.execute('''
            UPDATE appointments SET notes = ? WHERE id = ? AND doctor_id = ?
        ''', (filename, appointment_id, session['doctor_id']))
        conn.commit()
        conn.close()

        flash("Notes uploaded successfully.")
    
    return redirect(url_for('doctor_dashboard'))

@app.route('/cancel_appointment/<int:appointment_id>')
def cancel_appointment(appointment_id):
    if not is_logged_in():
        return redirect(url_for('login'))

    conn = get_db_connection()
    conn.execute('UPDATE appointments SET status = "cancelled" WHERE id = ? AND user_id = ?', (appointment_id, session['user_id']))
    conn.commit()
    conn.close()

    flash('Appointment cancelled successfully!')
    return redirect(url_for('dashboard'))

@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', error_code=404, error_message="Page not found"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', error_code=500, error_message="Internal server error"), 500

@app.route('/upload_health_record/<int:appointment_id>', methods=['GET', 'POST'])
def upload_health_record(appointment_id):
    if not is_logged_in():
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    # Verify appointment belongs to current user
    appointment = conn.execute('''
        SELECT a.*, d.name as doctor_name, d.specialization 
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.id
        WHERE a.id = ? AND a.user_id = ?
    ''', (appointment_id, session['user_id'])).fetchone()
    
    if not appointment:
        flash('Appointment not found!')
        conn.close()
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        if 'health_file' not in request.files:
            flash('No file selected')
            conn.close()
            return redirect(request.url)
        
        file = request.files['health_file']
        if file.filename == '':
            flash('No file selected')
            conn.close()
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Add timestamp to avoid conflicts
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
            filename = timestamp + filename
            
            upload_folder = os.path.join('static', 'health_records')
            os.makedirs(upload_folder, exist_ok=True)
            filepath = os.path.join(upload_folder, filename)
            file.save(filepath)
            
            # Save to database
            conn.execute('''
                INSERT INTO health_records (appointment_id, filename)
                VALUES (?, ?)
            ''', (appointment_id, filename))
            conn.commit()
            flash('Health record uploaded successfully!')
        else:
            flash('Invalid file type. Please upload PDF, JPG, PNG, or DOC files.')
    
    # Get existing health records for this appointment
    records = conn.execute('''
        SELECT * FROM health_records 
        WHERE appointment_id = ?
        ORDER BY uploaded_at DESC
    ''', (appointment_id,)).fetchall()
    
    conn.close()
    return render_template('upload_health_record.html', appointment=appointment, records=records)



@app.route('/view_health_records')
def view_health_records():
    if not is_logged_in():
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    # Get all health records for current user
    records = conn.execute('''
        SELECT hr.*, a.appointment_date, a.appointment_time, d.name as doctor_name
        FROM health_records hr
        JOIN appointments a ON hr.appointment_id = a.id
        JOIN doctors d ON a.doctor_id = d.id
        WHERE a.user_id = ?
        ORDER BY hr.uploaded_at DESC
    ''', (session['user_id'],)).fetchall()
    
    conn.close()
    return render_template('view_health_records.html', records=records)

   





if __name__ == '__main__':
    init_db()  # Already present
    # <-- Add this line
    app.run(debug=True)
