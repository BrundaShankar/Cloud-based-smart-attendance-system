import boto3
import os
import csv
import io
from datetime import datetime
from PIL import Image
from botocore.exceptions import NoCredentialsError, ClientError

# ============================================================
# AWS CONFIGURATION
# ============================================================

AWS_REGION = "us-east-1"   # Change to your actual AWS region

S3_BUCKET = "student-attendance-photos"
COLLECTION_ID = "student-attendance-collection"

# ============================================================
# PROJECT PATHS
# ============================================================

# Get the folder where attendance_system.py is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

STUDENTS_FOLDER = os.path.join(BASE_DIR, "students")
CHECK_FOLDER = os.path.join(BASE_DIR, "check_photos")
ATTENDANCE_FILE = os.path.join(BASE_DIR, "attendance.csv")

# ============================================================
# SUPPORTED IMAGE FORMATS
# ============================================================

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png")

# ============================================================
# AWS CLIENTS
# ============================================================

try:
    s3 = boto3.client(
        "s3",
        region_name=AWS_REGION
    )

    rekognition = boto3.client(
        "rekognition",
        region_name=AWS_REGION
    )

except Exception as e:
    print(f"❌ Error creating AWS clients: {e}")
    raise


# ============================================================
# CHECK LOCAL FOLDERS
# ============================================================

def check_required_folders():

    if not os.path.exists(STUDENTS_FOLDER):
        raise FileNotFoundError(
            f"\n❌ Students folder not found:\n{STUDENTS_FOLDER}\n"
            "Create the 'students' folder and add student images."
        )

    if not os.path.exists(CHECK_FOLDER):
        raise FileNotFoundError(
            f"\n❌ Check photos folder not found:\n{CHECK_FOLDER}\n"
            "Create the 'check_photos' folder and add classroom images."
        )

    print(f"📂 Project folder: {BASE_DIR}")
    print(f"✅ Students folder found")
    print(f"✅ Check photos folder found")


# ============================================================
# UPLOAD FOLDER TO S3
# ============================================================

def upload_folder_to_s3(local_folder, s3_prefix):

    uploaded_count = 0

    for file_name in os.listdir(local_folder):

        local_path = os.path.join(local_folder, file_name)

        # Skip folders
        if not os.path.isfile(local_path):
            continue

        # Skip non-image files
        if not file_name.lower().endswith(IMAGE_EXTENSIONS):
            print(f"ℹ Skipping non-image file: {file_name}")
            continue

        s3_key = f"{s3_prefix}/{file_name}"

        try:

            s3.upload_file(
                local_path,
                S3_BUCKET,
                s3_key
            )

            print(
                f"✅ Uploaded {file_name} "
                f"→ s3://{S3_BUCKET}/{s3_key}"
            )

            uploaded_count += 1

        except NoCredentialsError:

            print(
                "\n❌ AWS credentials not found.\n"
                "Run 'aws configure' and configure your AWS credentials."
            )

            raise

        except ClientError as e:

            print(
                f"⚠ Upload failed for {file_name}: {e}"
            )

        except Exception as e:

            print(
                f"⚠ Unexpected upload error for {file_name}: {e}"
            )

    return uploaded_count


# ============================================================
# ENSURE REKOGNITION COLLECTION EXISTS
# ============================================================

def ensure_collection():

    try:

        rekognition.describe_collection(
            CollectionId=COLLECTION_ID
        )

        print(
            f"ℹ Rekognition collection already exists: "
            f"{COLLECTION_ID}"
        )

    except rekognition.exceptions.ResourceNotFoundException:

        rekognition.create_collection(
            CollectionId=COLLECTION_ID
        )

        print(
            f"✅ Created Rekognition collection: "
            f"{COLLECTION_ID}"
        )


# ============================================================
# CLEAR EXISTING FACES
# ============================================================

def clear_collection(collection_id):

    print("\n🧹 Clearing old faces from Rekognition collection...")

    total_deleted = 0

    response = rekognition.list_faces(
        CollectionId=collection_id
    )

    while True:

        faces = response.get("Faces", [])

        if faces:

            face_ids = [
                face["FaceId"]
                for face in faces
            ]

            rekognition.delete_faces(
                CollectionId=collection_id,
                FaceIds=face_ids
            )

            total_deleted += len(face_ids)

            print(
                f"🧹 Deleted {len(face_ids)} faces"
            )

        next_token = response.get("NextToken")

        if not next_token:
            break

        response = rekognition.list_faces(
            CollectionId=collection_id,
            NextToken=next_token
        )

    if total_deleted == 0:
        print("ℹ Collection was already empty.")

    else:
        print(
            f"✅ Total faces deleted: {total_deleted}"
        )


# ============================================================
# INDEX STUDENT FACES
# ============================================================

def index_student_faces():

    print("\n🧠 Indexing student faces...")

    indexed_count = 0

    for student_image in os.listdir(STUDENTS_FOLDER):

        if not student_image.lower().endswith(IMAGE_EXTENSIONS):
            continue

        s3_key = f"students/{student_image}"

        student_name = os.path.splitext(
            student_image
        )[0]

        try:

            response = rekognition.index_faces(

                CollectionId=COLLECTION_ID,

                Image={
                    "S3Object": {
                        "Bucket": S3_BUCKET,
                        "Name": s3_key
                    }
                },

                ExternalImageId=student_name,

                DetectionAttributes=["DEFAULT"],

                MaxFaces=1
            )

            indexed_faces = response.get(
                "FaceRecords",
                []
            )

            if indexed_faces:

                print(
                    f"✅ Indexed: {student_image}"
                )

                indexed_count += 1

            else:

                print(
                    f"⚠ No face indexed in: "
                    f"{student_image}"
                )

        except Exception as e:

            print(
                f"⚠ Error indexing "
                f"{student_image}: {e}"
            )

    print(
        f"\n📊 Total student images indexed: "
        f"{indexed_count}"
    )


# ============================================================
# CREATE ATTENDANCE FILE
# ============================================================

def create_attendance_file():

    if not os.path.exists(ATTENDANCE_FILE):

        with open(
            ATTENDANCE_FILE,
            "w",
            newline="",
            encoding="utf-8"
        ) as file:

            writer = csv.writer(file)

            writer.writerow(
                ["Name", "Timestamp"]
            )

        print("✅ Created attendance.csv")

    else:

        print("ℹ attendance.csv already exists")


# ============================================================
# CROP FACE FROM S3 IMAGE
# ============================================================

def crop_face_from_s3(bucket, key, box):

    s3_object = s3.get_object(
        Bucket=bucket,
        Key=key
    )

    image_data = s3_object["Body"].read()

    image = Image.open(
        io.BytesIO(image_data)
    )

    image = image.convert("RGB")

    width, height = image.size

    left = int(
        box["Left"] * width
    )

    top = int(
        box["Top"] * height
    )

    right = int(
        (box["Left"] + box["Width"]) * width
    )

    bottom = int(
        (box["Top"] + box["Height"]) * height
    )

    # Make sure coordinates remain inside image
    left = max(0, left)
    top = max(0, top)
    right = min(width, right)
    bottom = min(height, bottom)

    cropped_image = image.crop(
        (left, top, right, bottom)
    )

    image_bytes = io.BytesIO()

    cropped_image.save(
        image_bytes,
        format="JPEG"
    )

    image_bytes.seek(0)

    return image_bytes.getvalue()


# ============================================================
# PROCESS CLASSROOM / CHECK IMAGES
# ============================================================

def process_check_images():

    print("\n🔍 Processing classroom images...")

    # Prevent duplicate attendance during this execution
    marked_names = set()

    for image_name in os.listdir(CHECK_FOLDER):

        if not image_name.lower().endswith(
            IMAGE_EXTENSIONS
        ):
            continue

        s3_key = f"check_photos/{image_name}"

        print(
            f"\n📸 Checking image: {image_name}"
        )

        try:

            # ------------------------------------------------
            # Detect all faces
            # ------------------------------------------------

            detect_response = rekognition.detect_faces(

                Image={
                    "S3Object": {
                        "Bucket": S3_BUCKET,
                        "Name": s3_key
                    }
                },

                Attributes=["DEFAULT"]
            )

            faces = detect_response.get(
                "FaceDetails",
                []
            )

            if not faces:

                print(
                    "❌ No faces detected."
                )

                continue

            print(
                f"👤 Faces detected: {len(faces)}"
            )

            # ------------------------------------------------
            # Process every detected face
            # ------------------------------------------------

            for index, face_detail in enumerate(faces):

                print(
                    f"\n🔎 Processing face "
                    f"{index + 1}/{len(faces)}"
                )

                box = face_detail["BoundingBox"]

                # Crop face
                face_bytes = crop_face_from_s3(
                    S3_BUCKET,
                    s3_key,
                    box
                )

                # ------------------------------------------------
                # Search face in Rekognition collection
                # ------------------------------------------------

                search_response = (
                    rekognition.search_faces_by_image(

                        CollectionId=COLLECTION_ID,

                        Image={
                            "Bytes": face_bytes
                        },

                        FaceMatchThreshold=90,

                        MaxFaces=1
                    )
                )

                matches = search_response.get(
                    "FaceMatches",
                    []
                )

                # ------------------------------------------------
                # Face recognized
                # ------------------------------------------------

                if matches:

                    match = matches[0]

                    name = (
                        match["Face"]
                        ["ExternalImageId"]
                    )

                    confidence = match[
                        "Similarity"
                    ]

                    # --------------------------------------------
                    # Mark attendance only once
                    # --------------------------------------------

                    if name not in marked_names:

                        marked_names.add(name)

                        timestamp = (
                            datetime.now()
                            .strftime(
                                "%Y-%m-%d %H:%M:%S"
                            )
                        )

                        with open(
                            ATTENDANCE_FILE,
                            "a",
                            newline="",
                            encoding="utf-8"
                        ) as file:

                            writer = csv.writer(file)

                            writer.writerow(
                                [
                                    name,
                                    timestamp
                                ]
                            )

                        print(
                            f"✅ {name} marked present"
                        )

                        print(
                            f"   Confidence: "
                            f"{confidence:.2f}%"
                        )

                    else:

                        print(
                            f"ℹ {name} "
                            f"already marked present"
                        )

                # ------------------------------------------------
                # Face not recognized
                # ------------------------------------------------

                else:

                    print(
                        f"❌ Face {index + 1} "
                        f"not recognized"
                    )

        except ClientError as e:

            print(
                f"⚠ AWS error while processing "
                f"{image_name}: {e}"
            )

        except Exception as e:

            print(
                f"⚠ Error processing "
                f"{image_name}: {e}"
            )

    return marked_names


# ============================================================
# MAIN PROGRAM
# ============================================================

def main():

    print("=" * 60)
    print("       AWS FACE RECOGNITION ATTENDANCE SYSTEM")
    print("=" * 60)

    print(
        f"\n🌎 AWS Region: {AWS_REGION}"
    )

    print(
        f"☁ S3 Bucket: {S3_BUCKET}"
    )

    print(
        f"🧠 Rekognition Collection: "
        f"{COLLECTION_ID}"
    )

    # --------------------------------------------------------
    # Check local folders
    # --------------------------------------------------------

    check_required_folders()

    # --------------------------------------------------------
    # Upload student images
    # --------------------------------------------------------

    print(
        "\n📤 Uploading student images to S3..."
    )

    student_count = upload_folder_to_s3(
        STUDENTS_FOLDER,
        "students"
    )

    print(
        f"📊 Student images uploaded: "
        f"{student_count}"
    )

    # --------------------------------------------------------
    # Upload classroom/check images
    # --------------------------------------------------------

    print(
        "\n📤 Uploading classroom images to S3..."
    )

    check_count = upload_folder_to_s3(
        CHECK_FOLDER,
        "check_photos"
    )

    print(
        f"📊 Classroom images uploaded: "
        f"{check_count}"
    )

    # --------------------------------------------------------
    # Create Rekognition collection
    # --------------------------------------------------------

    ensure_collection()

    # --------------------------------------------------------
    # Clear previous faces
    # --------------------------------------------------------

    clear_collection(
        COLLECTION_ID
    )

    # --------------------------------------------------------
    # Index students
    # --------------------------------------------------------

    index_student_faces()

    # --------------------------------------------------------
    # Create attendance CSV
    # --------------------------------------------------------

    create_attendance_file()

    # --------------------------------------------------------
    # Process classroom images
    # --------------------------------------------------------

    marked_students = process_check_images()

    # --------------------------------------------------------
    # Final result
    # --------------------------------------------------------

    print("\n" + "=" * 60)

    print(
        "🎯 ATTENDANCE MARKING COMPLETE!"
    )

    print(
        f"👥 Students marked present: "
        f"{len(marked_students)}"
    )

    print(
        f"📄 Attendance file: "
        f"{ATTENDANCE_FILE}"
    )

    print("=" * 60)


# ============================================================
# START PROGRAM
# ============================================================

if __name__ == "__main__":
    try:

        main()

    except NoCredentialsError:

        print(
            "\n❌ AWS credentials were not found."
        )

        print(
            "\nConfigure AWS credentials using:"
        )

        print(
            "aws configure"
        )

    except Exception as e:

        print(
            f"\n❌ Program stopped because of an error:"
        )

        print(e)
