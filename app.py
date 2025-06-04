from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId
import os

app = Flask(__name__)
app.secret_key = 'your-secret-key-for-appointments'

# MongoDB Configuration
try:
    client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=5000)
    client.server_info()  # Test connection
    db = client["hospital_appointments_db"]
    appointments_collection = db["appointments"]
    print("✅ Connected to MongoDB successfully!")
except Exception as e:
    print(f"❌ MongoDB connection failed: {e}")
    print("Please make sure MongoDB is running on localhost:27017")

@app.route('/')
def home():
    """Home page with appointment booking form"""
    return render_template('index.html')

@app.route('/book-appointment', methods=['POST'])
def book_appointment():
    """Book a new appointment"""
    try:
        # Get form data
        patient_name = request.form.get('patientName', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        doctor = request.form.get('doctor', '').strip()
        appointment_date = request.form.get('appointmentDate', '').strip()
        appointment_time = request.form.get('appointmentTime', '').strip()
        reason = request.form.get('reason', '').strip()
        
        # Validate required fields
        if not all([patient_name, email, phone, doctor, appointment_date, appointment_time]):
            flash('All fields are required!', 'error')
            return redirect(url_for('home'))
        
        # Check if appointment date is not in the past
        appointment_datetime = datetime.strptime(f"{appointment_date} {appointment_time}", "%Y-%m-%d %H:%M")
        if appointment_datetime < datetime.now():
            flash('Cannot book appointments in the past!', 'error')
            return redirect(url_for('home'))
        
        # Check if slot is already booked
        existing_appointment = appointments_collection.find_one({
            "doctor": doctor,
            "appointmentDate": appointment_date,
            "appointmentTime": appointment_time,
            "status": "active"
        })
        
        if existing_appointment:
            flash('This time slot is already booked. Please choose another time.', 'error')
            return redirect(url_for('home'))
        
        # Create appointment document
        appointment_data = {
            "patientName": patient_name,
            "email": email,
            "phone": phone,
            "doctor": doctor,
            "appointmentDate": appointment_date,
            "appointmentTime": appointment_time,
            "reason": reason,
            "status": "active",
            "createdAt": datetime.now(),
            "appointmentDateTime": appointment_datetime
        }
        
        # Save to database
        result = appointments_collection.insert_one(appointment_data)
        
        flash(f'Appointment booked successfully for {patient_name} with {doctor} on {appointment_date} at {appointment_time}!', 'success')
        return redirect(url_for('view_appointment', appointment_id=str(result.inserted_id)))
        
    except ValueError as e:
        flash('Invalid date or time format!', 'error')
        return redirect(url_for('home'))
    except Exception as e:
        flash(f'Error booking appointment: {str(e)}', 'error')
        return redirect(url_for('home'))

@app.route('/view-appointments')
def view_appointments():
    """View all appointments"""
    try:
        # Get all active appointments, sorted by appointment date and time
        appointments = list(appointments_collection.find(
            {"status": "active"}
        ).sort("appointmentDateTime", 1))
        
        # Convert ObjectId to string and format dates
        for appointment in appointments:
            appointment['_id'] = str(appointment['_id'])
            appointment['createdAt'] = appointment['createdAt'].strftime("%Y-%m-%d %H:%M:%S")
        
        return render_template('view_appointments.html', appointments=appointments)
        
    except Exception as e:
        flash(f'Error retrieving appointments: {str(e)}', 'error')
        return redirect(url_for('home'))

@app.route('/view-appointment/<appointment_id>')
def view_appointment(appointment_id):
    """View individual appointment"""
    try:
        appointment = appointments_collection.find_one({"_id": ObjectId(appointment_id)})
        if not appointment:
            flash('Appointment not found!', 'error')
            return redirect(url_for('view_appointments'))
        
        appointment['_id'] = str(appointment['_id'])
        appointment['createdAt'] = appointment['createdAt'].strftime("%Y-%m-%d %H:%M:%S")
        
        return render_template('view_single_appointment.html', appointment=appointment)
        
    except Exception as e:
        flash(f'Error retrieving appointment: {str(e)}', 'error')
        return redirect(url_for('view_appointments'))

# API Routes for AJAX requests
@app.route('/api/appointments', methods=['GET'])
def get_appointments():
    """API: Get all active appointments"""
    try:
        appointments = list(appointments_collection.find(
            {"status": "active"}
        ).sort("appointmentDateTime", 1))
        
        # Convert ObjectId to string for JSON serialization
        for appointment in appointments:
            appointment['_id'] = str(appointment['_id'])
            appointment['id'] = str(appointment['_id'])  # For compatibility
            del appointment['_id']
            # Remove datetime objects that can't be serialized
            if 'createdAt' in appointment:
                appointment['createdAt'] = appointment['createdAt'].isoformat()
            if 'appointmentDateTime' in appointment:
                appointment['appointmentDateTime'] = appointment['appointmentDateTime'].isoformat()
        
        return jsonify(appointments)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/appointments/<appointment_id>', methods=['DELETE'])
def cancel_appointment(appointment_id):
    """API: Cancel an appointment"""
    try:
        result = appointments_collection.update_one(
            {"_id": ObjectId(appointment_id)},
            {"$set": {"status": "cancelled", "cancelledAt": datetime.now()}}
        )
        
        if result.modified_count > 0:
            return jsonify({"message": "Appointment cancelled successfully"})
        else:
            return jsonify({"error": "Appointment not found"}), 404
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/appointments/<appointment_id>', methods=['GET'])
def get_appointment(appointment_id):
    """API: Get single appointment"""
    try:
        appointment = appointments_collection.find_one({"_id": ObjectId(appointment_id)})
        if not appointment:
            return jsonify({"error": "Appointment not found"}), 404
        
        appointment['_id'] = str(appointment['_id'])
        appointment['id'] = str(appointment['_id'])
        del appointment['_id']
        
        # Handle datetime serialization
        if 'createdAt' in appointment:
            appointment['createdAt'] = appointment['createdAt'].isoformat()
        if 'appointmentDateTime' in appointment:
            appointment['appointmentDateTime'] = appointment['appointmentDateTime'].isoformat()
        
        return jsonify(appointment)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/available-slots')
def get_available_slots():
    """API: Get available time slots for a specific doctor and date"""
    doctor = request.args.get('doctor')
    date = request.args.get('date')
    
    if not doctor or not date:
        return jsonify({"error": "Doctor and date are required"}), 400
    
    try:
        # Get booked slots for the doctor on the specified date
        booked_slots = appointments_collection.find({
            "doctor": doctor,
            "appointmentDate": date,
            "status": "active"
        }, {"appointmentTime": 1})
        
        booked_times = [slot['appointmentTime'] for slot in booked_slots]
        
        # All possible time slots
        all_slots = ["09:00", "10:00", "11:00", "12:00", "14:00", "15:00", "16:00", "17:00"]
        
        # Filter out booked slots
        available_slots = [slot for slot in all_slots if slot not in booked_times]
        
        return jsonify({"available_slots": available_slots})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/stats')
def get_appointment_stats():
    """API: Get appointment statistics"""
    try:
        total_appointments = appointments_collection.count_documents({"status": "active"})
        today = datetime.now().strftime("%Y-%m-%d")
        today_appointments = appointments_collection.count_documents({
            "appointmentDate": today,
            "status": "active"
        })
        
        return jsonify({
            "total_appointments": total_appointments,
            "today_appointments": today_appointments
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("🏥 Starting Hospital Appointment System...")
    print("📊 Make sure MongoDB is running on localhost:27017")
    print("🌐 Open http://127.0.0.1:5000 in your browser")
    app.run(debug=True, host='127.0.0.1', port=5000)