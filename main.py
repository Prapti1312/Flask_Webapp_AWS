from flask import Flask, render_template, request, redirect, url_for, jsonify
from io import BytesIO
import base64
import boto3
from config import *
from helper import *

app = Flask(__name__)

s3_bucket = S3_BUCKET
aws_region = AWS_REGION

rds_params = {
    'host': RDS_HOST,
    'user': RDS_USER,
    'port':3306,
    'password': RDS_PASSWORD,
    'db':  RDS_DB,
}

output = {}
table = 'registration_table'

db_conn = establish_connection(rds_params)


last_id = 0

def generate_student_id():
    global last_id
    last_id += 1
    return "sid_" + str(last_id)


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    try:
        # Retrieve form data
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        mobile_number = request.form['mobile_number']
        location = request.form['location']
        image_option = request.form['imageOption']

        # Generate unique ID
        sid = generate_student_id()

        # Check if the image is uploaded or captured
        if image_option == 'upload':
            image = request.files['image']
            image = BytesIO(base64.b64decode(image))
        elif image_option == 'capture':
            image = request.form['capturedImage']
            image = image.split(',')[1]
            image = BytesIO(base64.b64decode(image))

        insert_sql = "INSERT INTO registration_table (sid, first_name, last_name, email, mobile_number, location) VALUES (%s, %s, %s, %s, %s, %s)"
        with db_conn.cursor() as cursor:
            # Insert data extracted from the registration form into RDS
            cursor.execute(insert_sql, (sid, first_name, last_name, email, mobile_number, location))
            db_conn.commit()

            # Insert sid into attendance_table
            insert_attendance_sql = "INSERT INTO attendance_table (sid) VALUES (%s)"
            cursor.execute(insert_attendance_sql, (sid,))
            db_conn.commit()

            # Logic for image filename to be uploaded in S3
            s3_image_filename = sid + '.jpg'
            s3 = boto3.resource('s3')

            try:
                print("Data inserted in MySQL RDS... uploading image to S3...")
                # Upload image file in S3
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

                # Save image file metadata in DynamoDB
                print("Uploading to S3 success... saving metadata in DynamoDB...")
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

    # Query the registration table for the student with the provided SID
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
        return redirect(url_for('show_student', student_id=student_id))
    return render_template('search.html')

@app.route('/registered_users')

def get_registered_users():
    cursor = db_conn.cursor()
    get_students_query = "SELECT * FROM registration_table"
    cursor.execute(get_students_query)
    students_list = cursor.fetchall()
    return students_list