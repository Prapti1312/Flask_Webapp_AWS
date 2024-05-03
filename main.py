from flask import Flask, render_template, request, redirect, url_for, session
from io import BytesIO
import base64
import boto3
from config import *
from helper import *

app = Flask(__name__)
app.secret_key = os.urandom(24)

s3_bucket = S3_BUCKET
aws_region = AWS_REGION

rds_params = {
    'host': RDS_HOST,
    'user': RDS_USER,
    'port': 3306,
    'password': RDS_PASSWORD,
    'db': RDS_DB,
}

db_conn = establish_connection(rds_params)

def generate_sid():
    cursor = db_conn.cursor()
    try:
        cursor.execute("SELECT MAX(row_index) FROM registration_table")
        last_row_index = cursor.fetchone()[0]
        next_row_index = last_row_index + 1 if last_row_index is not None else 1
        sid = f"sid_{next_row_index}"
        return sid
    finally:
        cursor.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/verify', methods=['GET', 'POST'])
def verify():
    if request.method == 'POST':
        email = request.form['email']
        session['email'] = email
        ses_client = boto3.client('ses', region_name=aws_region)
        response = ses_client.verify_email_identity(EmailAddress=email)
        return "Verification email sent. Please check your inbox."
    return render_template('verify.html')

@app.route('/submit', methods=['POST'])
def submit():
    try:
        if 'email' not in session:
            return redirect(url_for('verify'))
        
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        mobile_number = request.form['mobile_number']
        location = request.form['location']
        image_option = request.form['imageOption']

        sid = generate_sid()

        if image_option == 'upload':
            image = request.files['image']
            filename = image.filename
            img_extension = filename.split(".")[-1]
        elif image_option == 'capture':
            image = request.form['capturedImage']
            image = image.split(',')[1]
            filename = "captured_image"  # Assuming a default filename
            img_extension = "jpg"  # Assuming a default extension

        insert_sql = "INSERT INTO registration_table (sid, first_name, last_name, email, mobile_number, location) VALUES (%s, %s, %s, %s, %s, %s)"
        with db_conn.cursor() as cursor:
            cursor.execute(insert_sql, (sid, first_name, last_name, email, mobile_number, location))
            db_conn.commit()

            insert_attendance_sql = "INSERT INTO attendance_table (sid) VALUES (%s)"
            cursor.execute(insert_attendance_sql, (sid,))
            db_conn.commit()

            s3_image_filename = sid + img_extension
            s3 = boto3.resource('s3')
            try:
                s3.Bucket(s3_bucket).put_object(Key=s3_image_filename, Body=image)
                bucket_location = boto3.client('s3').get_bucket_location(Bucket=s3_bucket)
                s3_location = (bucket_location['LocationConstraint'])

                if s3_location is None:
                    s3_location = ''
                else:
                    s3_location = '-' + s3_location

                object_url = "https://s3{0}.amazonaws.com/{1}/{2}".format(
                    s3_location,
                    s3_bucket,
                    s3_image_filename)

                dynamodb_client = boto3.client('dynamodb', region_name=aws_region)
                dynamodb_client.put_item(
                    TableName='student_image_table',
                    Item={
                        'sid': {'S': sid},
                        'image_url': {'S': object_url}
                    }
                )

            except Exception as e:
                return str(e)

    except Exception as e:
        return str(e)

    print("All modifications done...")
    return redirect(url_for('index'))

@app.route('/student/<path:student_sid>')
def show_student(student_sid):
    cursor = db_conn.cursor()
    sid_query = "SELECT * FROM registration_table WHERE sid = %s"
    cursor.execute(sid_query, (student_sid,))
    student_info = cursor.fetchone()
    if student_info:
        return render_template('student_details.html', student=student_info)
    else:
        return 'Student not found', 404

@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        student_id = int(request.form['student_id'])
        return redirect(url_for('show_student', student_sid=student_id))
    return render_template('search.html')

@app.route('/registered_users')
def get_registered_users():
    cursor = db_conn.cursor()
    get_students_query = "SELECT * FROM registration_table"
    cursor.execute(get_students_query)
    students_list = cursor.fetchall()
    return jsonify(students_list)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)
