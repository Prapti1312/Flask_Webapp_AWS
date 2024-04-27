import os
import base64  # Add this import
import uuid  # Add this import
from flask import Flask, render_template, request, redirect, url_for, jsonify

app = Flask(__name__)

# Ensure the "images" directory exists in the current working directory
UPLOAD_FOLDER = 'images'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Store form data in a list with an ID
student_data = []

# Set the upload folder for Flask app
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Rest of your code remains the same...

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    # Retrieve form data
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    email = request.form['email']
    mobile_number = request.form['mobile_number']
    location = request.form['location']
    image_option = request.form['imageOption']
    # Check if the image is uploaded or captured
    if image_option == 'upload':
        image = request.files['image']
        image_filename = image.filename
        print('this is image filename', image_filename)
        image.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
    elif image_option == 'capture':
        # Retrieve captured image from canvas
        image = request.form['capturedImage']
        # Convert base64 image data to bytes
        image = image.split(',')[1]
        img_bytes = base64.b64decode(image)
        # Generate a unique filename
        image_filename = str(uuid.uuid4()) + '.png'
        # Save the image to the upload folder
        with open(os.path.join(app.config['UPLOAD_FOLDER'], image_filename), 'wb') as f:
            f.write(img_bytes)
    
    # Store form data with an ID
    student = {
        'id': len(student_data) + 1,
        'first_name': first_name,
        'last_name': last_name,
        'email': email,
        'mobile_number': mobile_number,
        'location':location,  # Store the filename or path
        'image': image_filename
    }
    student_data.append(student)

    # Redirect to home page after submission
    return redirect(url_for('index'))

@app.route('/student/<int:student_id>')
def show_student(student_id):
    # Find student by ID
    for student in student_data:
        if student['id'] == student_id:
            return render_template('student_details.html', student=student)
    return 'Student not found', 404

@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        student_id = int(request.form['student_id'])
        return redirect(url_for('show_student', student_id=student_id))
    return render_template('search.html')

@app.route('/registered_users')
def get_registered_users():
    return jsonify(student_data)

if __name__ == '__main__':
    app.run(debug=True)
