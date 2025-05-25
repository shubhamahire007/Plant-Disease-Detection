from flask import Flask, flash, render_template, request, redirect, send_from_directory, session
import numpy as np
import uuid
import json
import tensorflow as tf
from auth_routes import auth  # Register authentication blueprint
from datetime import datetime, timedelta
import os
from flask import send_file
from datetime import datetime
import pdfkit

# config = pdfkit.configuration(wkhtmltopdf="C:/Program Files/wkhtmltopdf/bin/wkhtmltopdf.exe")
# pdfkit.from_string(html_content, pdf_path, configuration=config)

app = Flask(__name__)
app.secret_key = 'secret-key'
app.register_blueprint(auth)

app.permanent_session_lifetime = timedelta(days=2)

# Load plant disease data
with open("plant_disease.json", 'r') as file:
    plant_disease = json.load(file)

# Load pre-trained model
model = tf.keras.models.load_model("models/plant_disease_recog_model_pwp.keras")

@app.route('/uploadimages/<path:filename>')
def uploaded_images(filename):
    return send_from_directory('./uploadimages', filename)

@app.route('/')
def home():
    return render_template('home.html', prediction_data=plant_disease, home_page=True,request=request)

def extract_features(image):
    image = tf.keras.utils.load_img(image, target_size=(160, 160))
    feature = tf.keras.utils.img_to_array(image)
    return np.array([feature])

def model_predict(image_path):
    img = extract_features(image_path)
    prediction = model.predict(img)[0]
    print("pred:", prediction)
    print("pred:", round(prediction[prediction.argmax()]*100,2))
    prediction_label = plant_disease[prediction.argmax()]

    # Save history if user is logged in
    user_email = session.get('user')
    if user_email:
        with open('users.json', 'r') as f:
            users = json.load(f)
        
        if user_email in users:
            users[user_email].setdefault('history', []).append({
                'image': image_path.replace('\\', '/'),  # Ensure forward slashes
                'prediction': prediction_label['name'],
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
            with open('users.json', 'w') as f:
                json.dump(users, f, indent=4)

    return prediction_label

@app.route('/upload/', methods=['POST', 'GET'])
def uploadimage():
    if 'user' not in session:
        # flash('Please log in to upload an image.', 'warning')
        return redirect('/login')

    if request.method == "POST":
        image = request.files['img']
        temp_name = f"uploadimages/temp_{uuid.uuid4().hex}"
        image_path = f'{temp_name}_{image.filename}'
        image.save(image_path)
        prediction = model_predict(image_path)
        return render_template('home.html', result=True, imagepath=f'/{image_path}', prediction=prediction, home_page=False, request=request)
    else:
        return redirect('/')

@app.route('/diseases/<plant>')
def disease_info(plant):
    plant = plant.lower()
    filtered = [entry for entry in plant_disease if entry['name'].lower().split()[0] == plant]
    if not filtered:
        return f"No diseases found for plant: {plant}", 404
    return render_template('disease_info.html', plant_name=plant.capitalize(), disease_list=filtered,request=request)

@app.route('/history')
def history():
    user_email = session.get('user')
    if not user_email:
        return redirect('/login')

    with open('users.json', 'r') as f:
        users = json.load(f)
    
    user_data = users.get(user_email, {})
    history = user_data.get('history', [])

    return render_template('history.html', history=history,request=request)

@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    if 'user' not in session:
        # flash('Please log in to upload an image.', 'warning')
        return redirect('/login')
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')

        feedback_entry = {
            'name': name,
            'email': email,
            'message': message
        }

        # Save feedback to a file
        if not os.path.exists('feedback.json'):
            with open('feedback.json', 'w') as f:
                json.dump([], f)

        with open('feedback.json', 'r+') as f:
            data = json.load(f)
            data.append(feedback_entry)
            f.seek(0)
            json.dump(data, f, indent=4)

        flash('Thank you for your feedback!', 'success')
        return redirect('/feedback')

    return render_template('feedback.html',request=request)


@app.route('/admin')
def admin_dashboard():
    # Admin access check
    if session.get('user') != 'admin@plantshield.com':
        # flash('Access denied.', 'danger')
        return redirect('/')

    # Load users
    users = {}
    if os.path.exists('users.json'):
        with open('users.json', 'r') as f:
            users = json.load(f)
            
    users.pop('admin@plantshield.com', None)
    
    # Load feedback
    feedback = []
    if os.path.exists('feedback.json'):
        with open('feedback.json', 'r') as f:
            feedback = json.load(f)

    return render_template('admin.html', users=users, feedback=feedback)


import pdfkit
@app.route('/download_report/<filename>')
def download_report(filename):
    image_path = f'uploadimages/{filename}'
    user_email = session.get('user')

    if not user_email:
        return redirect('/login')

    # Load user history
    with open('users.json', 'r') as f:
        users = json.load(f)

    history = users.get(user_email, {}).get('history', [])
    entry = next((item for item in history if item['image'].endswith(filename)), None)

    if not entry:
        return "No matching history found for this image.", 404

    # Get disease info
    disease_name = entry['prediction']
    timestamp = entry['timestamp']
    prediction_data = next((d for d in plant_disease if d['name'] == disease_name), None)

    cause = prediction_data.get('cause', 'N/A') if prediction_data else 'N/A'
    cure = prediction_data.get('cure', 'N/A') if prediction_data else 'N/A'
    confidence = "Not stored"  # Optional: add to model output + history if needed

    image_url = f"http://127.0.0.1:5000/uploadimages/{filename}"

    html_content = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            h1 {{ color: #2e6c80; }}
        </style>
    </head>
    <body>
        <h1>Plant Disease Report</h1>
        <p><strong>Disease:</strong> {disease_name}</p>
        <p><strong>Cause:</strong> {cause}</p>
        <p><strong>Cure:</strong> {cure}</p>
        <p><strong>Timestamp:</strong> {timestamp}</p>
        <strong>Plant Image:</strong>
        <p><img src="{image_url}" width="300"></p>
    </body>
    </html>
    """

    config = pdfkit.configuration(wkhtmltopdf=r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe")
    pdf_path = f'static/reports/report_{filename}.pdf'

    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
    pdfkit.from_string(html_content, pdf_path, configuration=config)
    return send_file(pdf_path, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
