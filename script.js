// Set minimum date to today
document.addEventListener('DOMContentLoaded', function() {
    const dateInput = document.getElementById('appointmentDate');
    const today = new Date().toISOString().split('T')[0];
    dateInput.min = today;
    
    // Load recent appointments
    loadRecentAppointments();
});

// Form validation and submission
document.getElementById('appointmentForm').addEventListener('submit', function(e) {
    if (!validateForm()) {
        e.preventDefault();
        return false;
    }
    
    const formData = new FormData(this);
    const appointmentData = Object.fromEntries(formData.entries());
    
    // Show confirmation message
    showConfirmation(`Appointment request submitted for ${appointmentData.patientName} with ${appointmentData.doctor}`, 'success');
});

function validateForm() {
    const patientName = document.getElementById('patientName').value.trim();
    const email = document.getElementById('email').value.trim();
    const phone = document.getElementById('phone').value.trim();
    const doctor = document.getElementById('doctor').value;
    const appointmentDate = document.getElementById('appointmentDate').value;
    const appointmentTime = document.getElementById('appointmentTime').value;

    // Check required fields
    if (!patientName || !email || !phone || !doctor || !appointmentDate || !appointmentTime) {
        showConfirmation('Please fill in all required fields', 'error');
        return false;
    }

    // Validate email format
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        showConfirmation('Please enter a valid email address', 'error');
        return false;
    }

    // Validate phone number (basic validation)
    const phoneRegex = /^[\d\s\-\+\(\)]{10,}$/;
    if (!phoneRegex.test(phone)) {
        showConfirmation('Please enter a valid phone number', 'error');
        return false;
    }

    // Check if appointment date is not in the past
    const selectedDate = new Date(appointmentDate);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    if (selectedDate < today) {
        showConfirmation('Please select a future date', 'error');
        return false;
    }

    // Check if selected date is not a Sunday (assuming clinic is closed on Sundays)
    if (selectedDate.getDay() === 0) {
        showConfirmation('Sorry, we are closed on Sundays. Please select another date.', 'error');
        return false;
    }

    return true;
}

function showConfirmation(message, type) {
    const confirmationDiv = document.getElementById('confirmation');
    confirmationDiv.textContent = message;
    confirmationDiv.className = `confirmation ${type}`;
    confirmationDiv.style.display = 'block';
    
    // Auto-hide success messages after 5 seconds
    if (type === 'success') {
        setTimeout(() => {
            confirmationDiv.style.display = 'none';
        }, 5000);
    }
}

// Load recent appointments from server
async function loadRecentAppointments() {
    try {
        const response = await fetch('/api/appointments');
        if (response.ok) {
            const appointments = await response.json();
            displayAppointments(appointments.slice(0, 5)); // Show only recent 5
        }
    } catch (error) {
        console.log('Could not load appointments:', error);
        // Don't show error to user as this is optional functionality
    }
}

function displayAppointments(appointments) {
    const appointmentsList = document.getElementById('appointmentsList');
    
    if (appointments.length === 0) {
        appointmentsList.innerHTML = '<div class="no-appointments">No recent appointments found</div>';
        return;
    }
    
    appointmentsList.innerHTML = appointments.map(appointment => `
        <div class="appointment-card">
            <div class="appointment-info">
                <div class="info-item">
                    <span class="info-label">Patient</span>
                    <span class="info-value">${appointment.patientName}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Doctor</span>
                    <span class="info-value">${appointment.doctor}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Date</span>
                    <span class="info-value">${formatDate(appointment.appointmentDate)}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Time</span>
                    <span class="info-value">${formatTime(appointment.appointmentTime)}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Email</span>
                    <span class="info-value">${appointment.email}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Phone</span>
                    <span class="info-value">${appointment.phone}</span>
                </div>
            </div>
            ${appointment.reason ? `<div class="appointment-reason">"${appointment.reason}"</div>` : ''}
            <div class="appointment-actions">
                <button class="btn-small btn-cancel" onclick="cancelAppointment('${appointment.id}')">Cancel</button>
                <button class="btn-small btn-reschedule" onclick="rescheduleAppointment('${appointment.id}')">Reschedule</button>
            </div>
        </div>
    `).join('');
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
        weekday: 'short', 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric' 
    });
}

function formatTime(timeString) {
    const [hours, minutes] = timeString.split(':');
    const hour = parseInt(hours);
    const ampm = hour >= 12 ? 'PM' : 'AM';
    const hour12 = hour % 12 || 12;
    return `${hour12}:${minutes} ${ampm}`;
}

async function cancelAppointment(appointmentId) {
    if (!confirm('Are you sure you want to cancel this appointment?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/appointments/${appointmentId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            showConfirmation('Appointment cancelled successfully', 'success');
            loadRecentAppointments(); // Refresh the list
        } else {
            showConfirmation('Failed to cancel appointment', 'error');
        }
    } catch (error) {
        showConfirmation('Error cancelling appointment', 'error');
    }
}

function rescheduleAppointment(appointmentId) {
    // For now, just show a message. In a real app, you'd open a modal or redirect
    showConfirmation('Please call us at (555) 123-4567 to reschedule your appointment', 'success');
}

// Real-time form feedback
document.getElementById('patientName').addEventListener('input', function() {
    this.value = this.value.replace(/[^a-zA-Z\s]/g, ''); // Only letters and spaces
});

document.getElementById('phone').addEventListener('input', function() {
    // Format phone number as user types
    let value = this.value.replace(/\D/g, '');
    if (value.length >= 6) {
        value = value.replace(/(\d{3})(\d{3})(\d{4})/, '($1) $2-$3');
    } else if (value.length >= 3) {
        value = value.replace(/(\d{3})(\d{3})/, '($1) $2');
    }
    this.value = value;
});