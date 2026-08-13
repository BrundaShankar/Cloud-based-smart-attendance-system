import boto3
import os
import csv
import io
from datetime import datetime
from PIL import Image

# --------------------------
# AWS CONFIGURATION
# --------------------------
AWS_REGION = 'us-east-1'  # Change this if your bucket is in another region
S3_BUCKET = 'student-attendance-photos'
COLLECTION_ID = 'student-attendance-collection'

# Local folders
STUDENTS_FOLDER = 'students'
CHECK_FOLDER = 'check_photos'
ATTENDANCE_FILE = 'attendance.csv'

# --------------------------
# AWS CLIENTS
# --------------------------
s3 = boto3.client('s3', region_name=AWS_REGION)
rekognition = boto3.client('rekognition', region_name=AWS_REGION)

# --------------------------
# 1️⃣ Upload images to S3
# --------------------------
def upload_folder_to_s3(local_folder, s3_prefix):
    for file_name in os.listdir(local_folder):
        local_path = os.path.join(local_folder, file_name)
        if os.path.isfile(local_path):
            s3_key = f"{s3_prefix}/{file_name}"
            s3.upload_file(local_path, S3_BUCKET, s3_key)
            print(f"✅ Uploaded {file_name} to s3://{S3_BUCKET}/{s3_key}")

print("Uploading student images to S3...")
upload_folder_to_s3(STUDENTS_FOLDER, "students")

print("Uploading check images to S3...")
upload_folder_to_s3(CHECK_FOLDER, "check_photos")

# --------------------------
# 2️⃣ Ensure Rekognition collection exists
# --------------------------
try:
    rekognition.describe_collection(CollectionId=COLLECTION_ID)
    print(f"ℹ Collection '{COLLECTION_ID}' already exists.")
except rekognition.exceptions.ResourceNotFoundException:
    rekognition.create_collection(CollectionId=COLLECTION_ID)
    print(f"✅ Created new Rekognition collection: {COLLECTION_ID}")

# --------------------------
# 3️⃣ Clear old Rekognition faces before indexing
# --------------------------
def clear_collection(collection_id):
    faces = rekognition.list_faces(CollectionId=collection_id)
    while 'Faces' in faces and len(faces['Faces']) > 0:
        face_ids = [f['FaceId'] for f in faces['Faces']]
        rekognition.delete_faces(CollectionId=collection_id, FaceIds=face_ids)
        print(f"🧹 Cleared {len(face_ids)} old faces from collection.")
        if 'NextToken' in faces:
            faces = rekognition.list_faces(CollectionId=collection_id, NextToken=faces['NextToken'])
        else:
            break

clear_collection(COLLECTION_ID)

# --------------------------
# 4️⃣ Index student images (only 1 main face per image)
# --------------------------
for student_image in os.listdir(STUDENTS_FOLDER):
    s3_key = f"students/{student_image}"
    try:
        rekognition.index_faces(
            CollectionId=COLLECTION_ID,
            Image={'S3Object': {'Bucket': S3_BUCKET, 'Name': s3_key}},
            ExternalImageId=os.path.splitext(student_image)[0],
            DetectionAttributes=['DEFAULT'],
            MaxFaces=1  # 👈 ensures only one (main) face is indexed
        )
        print(f"✅ Indexed {student_image}")
    except Exception as e:
        print(f"⚠ Error indexing {student_image}: {e}")

# --------------------------
# 5️⃣ Ensure attendance.csv exists
# --------------------------
if not os.path.exists(ATTENDANCE_FILE):
    with open(ATTENDANCE_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Name', 'Timestamp'])

# --------------------------
# Helper: Crop face using bounding box
# --------------------------
def crop_face_from_s3(bucket, key, box):
    s3_object = s3.get_object(Bucket=bucket, Key=key)
    img = Image.open(io.BytesIO(s3_object['Body'].read()))

    width, height = img.size
    left = int(box['Left'] * width)
    top = int(box['Top'] * height)
    right = int((box['Left'] + box['Width']) * width)
    bottom = int((box['Top'] + box['Height']) * height)

    cropped_img = img.crop((left, top, right, bottom))
    img_bytes = io.BytesIO()
    cropped_img.save(img_bytes, format='JPEG')
    return img_bytes.getvalue()

# --------------------------
# 6️⃣ Process check images (single/group)
# --------------------------
marked_names = set()  # Avoid duplicate attendance

for image_name in os.listdir(CHECK_FOLDER):
    s3_key = f"check_photos/{image_name}"
    print(f"\n🔍 Checking image: {image_name}")

    try:
        detect_response = rekognition.detect_faces(
            Image={'S3Object': {'Bucket': S3_BUCKET, 'Name': s3_key}},
            Attributes=['DEFAULT']
        )

        faces = detect_response.get('FaceDetails', [])
        if not faces:
            print("❌ No faces detected.")
            continue

        for i, face_detail in enumerate(faces):
            box = face_detail['BoundingBox']
            face_bytes = crop_face_from_s3(S3_BUCKET, s3_key, box)

            # Search each cropped face in the collection
            search_response = rekognition.search_faces_by_image(
                CollectionId=COLLECTION_ID,
                Image={'Bytes': face_bytes},
                FaceMatchThreshold=90,
                MaxFaces=1
            )

            if search_response.get('FaceMatches'):
                match = search_response['FaceMatches'][0]
                name = match['Face']['ExternalImageId']
                confidence = match['Similarity']

                if name not in marked_names:
                    marked_names.add(name)
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    with open(ATTENDANCE_FILE, 'a', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow([name, timestamp])

                    print(f"✅ Detected face {i+1}: {name} (Confidence: {confidence:.2f}%)")
                else:
                    print(f"ℹ {name} already marked present.")
            else:
                print(f"❌ Face {i+1} not recognized.")

    except Exception as e:
        print(f"⚠ Error processing {image_name}: {e}")

print("\n🎯 Attendance marking complete! Check attendance.csv")


