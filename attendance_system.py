import boto3
import os
import io
from datetime import datetime
from PIL import Image
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, Alignment
from botocore.exceptions import NoCredentialsError, ClientError

# ============================================================
# AWS CONFIGURATION
# ============================================================

AWS_REGION = "us-east-1"   # Change if your AWS resources use another region

S3_BUCKET = "student-attendance-photos"
COLLECTION_ID = "student-attendance-collection"

# ============================================================
# PROJECT PATHS
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

STUDENTS_FOLDER = os.path.join(BASE_DIR, "students")
CHECK_FOLDER = os.path.join(BASE_DIR, "check_photos")

ATTENDANCE_FILE = os.path.join(
    BASE_DIR,
    "attendance.xlsx"
)

# ============================================================
# SUPPORTED IMAGE FORMATS
# ============================================================

IMAGE_EXTENSIONS = (
    ".jpg",
    ".jpeg",
    ".png"
)

# ============================================================
# AWS CLIENTS
# ============================================================

s3 = boto3.client(
    "s3",
    region_name=AWS_REGION
)

rekognition = boto3.client(
    "rekognition",
    region_name=AWS_REGION
)


# ============================================================
# CHECK REQUIRED FOLDERS
# ============================================================

def check_required_folders():

    if not os.path.exists(STUDENTS_FOLDER):
        raise FileNotFoundError(
            f"\nStudents folder not found:\n"
            f"{STUDENTS_FOLDER}\n\n"
            f"Create a 'students' folder and add "
            f"individual student images."
        )

    if not os.path.exists(CHECK_FOLDER):
        raise FileNotFoundError(
            f"\nCheck photos folder not found:\n"
            f"{CHECK_FOLDER}\n\n"
            f"Create a 'check_photos' folder and add "
            f"classroom/group images."
        )

    print("Students folder found.")
    print("Check photos folder found.")


# ============================================================
# GET STUDENT NAMES FROM INDIVIDUAL IMAGES
# ============================================================

def get_student_names():

    student_names = []

    for file_name in os.listdir(STUDENTS_FOLDER):

        if not file_name.lower().endswith(
            IMAGE_EXTENSIONS
        ):
            continue

        # Remove extension
        name = os.path.splitext(file_name)[0]

        student_names.append(name)

    # Remove duplicates and sort alphabetically
    student_names = sorted(
        set(student_names),
        key=str.lower
    )

    return student_names


# ============================================================
# UPLOAD FOLDER TO S3
# ============================================================

def upload_folder_to_s3(
    local_folder,
    s3_prefix
):

    uploaded_count = 0

    for file_name in os.listdir(local_folder):

        local_path = os.path.join(
            local_folder,
            file_name
        )

        if not os.path.isfile(local_path):
            continue

        if not file_name.lower().endswith(
            IMAGE_EXTENSIONS
        ):
            continue

        s3_key = f"{s3_prefix}/{file_name}"

        try:

            s3.upload_file(
                local_path,
                S3_BUCKET,
                s3_key
            )

            print(
                f"Uploaded: {file_name}"
            )

            uploaded_count += 1

        except Exception as e:

            print(
                f"Error uploading "
                f"{file_name}: {e}"
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
            f"Collection already exists: "
            f"{COLLECTION_ID}"
        )

    except rekognition.exceptions.ResourceNotFoundException:

        rekognition.create_collection(
            CollectionId=COLLECTION_ID
        )

        print(
            f"Created collection: "
            f"{COLLECTION_ID}"
        )


# ============================================================
# CLEAR OLD FACES
# ============================================================

def clear_collection():

    print("\nClearing old Rekognition faces...")

    response = rekognition.list_faces(
        CollectionId=COLLECTION_ID
    )

    total_deleted = 0

    while True:

        faces = response.get(
            "Faces",
            []
        )

        if faces:

            face_ids = [
                face["FaceId"]
                for face in faces
            ]

            rekognition.delete_faces(
                CollectionId=COLLECTION_ID,
                FaceIds=face_ids
            )

            total_deleted += len(face_ids)

            print(
                f"Deleted {len(face_ids)} faces."
            )

        next_token = response.get(
            "NextToken"
        )

        if not next_token:
            break

        response = rekognition.list_faces(
            CollectionId=COLLECTION_ID,
            NextToken=next_token
        )

    print(
        f"Total old faces deleted: "
        f"{total_deleted}"
    )


# ============================================================
# INDEX STUDENT IMAGES
# ============================================================

def index_student_faces():

    print("\nIndexing student faces...")

    indexed_count = 0

    for student_image in os.listdir(
        STUDENTS_FOLDER
    ):

        if not student_image.lower().endswith(
            IMAGE_EXTENSIONS
        ):
            continue

        s3_key = (
            f"students/{student_image}"
        )

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

                DetectionAttributes=[
                    "DEFAULT"
                ],

                MaxFaces=1
            )

            if response.get("FaceRecords"):

                print(
                    f"Indexed: {student_name}"
                )

                indexed_count += 1

            else:

                print(
                    f"No face found in: "
                    f"{student_image}"
                )

        except Exception as e:

            print(
                f"Error indexing "
                f"{student_image}: {e}"
            )

    print(
        f"\nTotal students indexed: "
        f"{indexed_count}"
    )


# ============================================================
# CREATE / UPDATE EXCEL ATTENDANCE FILE
# ============================================================

def prepare_attendance_excel(
    student_names,
    timestamp
):

    if os.path.exists(
        ATTENDANCE_FILE
    ):

        workbook = load_workbook(
            ATTENDANCE_FILE
        )

        worksheet = workbook.active

        print(
            "Existing attendance.xlsx found."
        )

    else:

        workbook = Workbook()

        worksheet = workbook.active

        worksheet.title = "Attendance"

        # First column title
        worksheet.cell(
            row=1,
            column=1,
            value="Student Name"
        )

        worksheet.cell(
            row=1,
            column=1
        ).font = Font(
            bold=True
        )

        print(
            "Created new attendance.xlsx."
        )

    # --------------------------------------------------------
    # Find existing student names
    # --------------------------------------------------------

    existing_names = {}

    for row in range(
        2,
        worksheet.max_row + 1
    ):

        value = worksheet.cell(
            row=row,
            column=1
        ).value

        if value:

            existing_names[
                str(value).lower()
            ] = row

    # --------------------------------------------------------
    # Add any new students
    # --------------------------------------------------------

    for name in student_names:

        if name.lower() not in existing_names:

            new_row = (
                worksheet.max_row + 1
            )

            worksheet.cell(
                row=new_row,
                column=1,
                value=name
            )

            existing_names[
                name.lower()
            ] = new_row

    # --------------------------------------------------------
    # Create new timestamp column
    # --------------------------------------------------------

    new_column = (
        worksheet.max_column + 1
    )

    worksheet.cell(
        row=1,
        column=new_column,
        value=timestamp
    )

    worksheet.cell(
        row=1,
        column=new_column
    ).font = Font(
        bold=True
    )

    worksheet.cell(
        row=1,
        column=new_column
    ).alignment = Alignment(
        horizontal="center"
    )

    # --------------------------------------------------------
    # Initially mark everyone ABSENT
    # --------------------------------------------------------

    for name in student_names:

        row = existing_names[
            name.lower()
        ]

        worksheet.cell(
            row=row,
            column=new_column,
            value="Absent"
        )

        worksheet.cell(
            row=row,
            column=new_column
        ).alignment = Alignment(
            horizontal="center"
        )

    workbook.save(
        ATTENDANCE_FILE
    )

    return new_column


# ============================================================
# MARK STUDENT PRESENT IN EXCEL
# ============================================================

def mark_student_present(
    student_name,
    attendance_column
):

    workbook = load_workbook(
        ATTENDANCE_FILE
    )

    worksheet = workbook.active

    for row in range(
        2,
        worksheet.max_row + 1
    ):

        name = worksheet.cell(
            row=row,
            column=1
        ).value

        if (
            name
            and str(name).lower()
            == student_name.lower()
        ):

            worksheet.cell(
                row=row,
                column=attendance_column,
                value="Present"
            )

            break

    workbook.save(
        ATTENDANCE_FILE
    )


# ============================================================
# CROP FACE FROM S3
# ============================================================

def crop_face_from_s3(
    bucket,
    key,
    box
):

    response = s3.get_object(
        Bucket=bucket,
        Key=key
    )

    image_data = response[
        "Body"
    ].read()

    image = Image.open(
        io.BytesIO(image_data)
    )

    image = image.convert(
        "RGB"
    )

    width, height = image.size

    left = int(
        box["Left"] * width
    )

    top = int(
        box["Top"] * height
    )

    right = int(
        (
            box["Left"]
            + box["Width"]
        ) * width
    )

    bottom = int(
        (
            box["Top"]
            + box["Height"]
        ) * height
    )

    # Keep coordinates within image
    left = max(0, left)
    top = max(0, top)
    right = min(width, right)
    bottom = min(height, bottom)

    cropped_image = image.crop(
        (
            left,
            top,
            right,
            bottom
        )
    )

    image_bytes = io.BytesIO()

    cropped_image.save(
        image_bytes,
        format="JPEG"
    )

    image_bytes.seek(0)

    return image_bytes.getvalue()


# ============================================================
# PROCESS CLASSROOM IMAGES
# ============================================================

def process_check_images(
    attendance_column
):

    print(
        "\nProcessing classroom images..."
    )

    # Prevent duplicate marking
    # within this attendance session
    marked_names = set()

    for image_name in os.listdir(
        CHECK_FOLDER
    ):

        if not image_name.lower().endswith(
            IMAGE_EXTENSIONS
        ):
            continue

        s3_key = (
            f"check_photos/{image_name}"
        )

        print(
            f"\nChecking: {image_name}"
        )

        try:

            # ------------------------------------------------
            # Detect faces
            # ------------------------------------------------

            response = rekognition.detect_faces(

                Image={
                    "S3Object": {
                        "Bucket": S3_BUCKET,
                        "Name": s3_key
                    }
                },

                Attributes=["DEFAULT"]
            )

            faces = response.get(
                "FaceDetails",
                []
            )

            if not faces:

                print(
                    "No faces detected."
                )

                continue

            print(
                f"Faces detected: "
                f"{len(faces)}"
            )

            # ------------------------------------------------
            # Process each face
            # ------------------------------------------------

            for index, face in enumerate(
                faces
            ):

                box = face[
                    "BoundingBox"
                ]

                face_bytes = (
                    crop_face_from_s3(
                        S3_BUCKET,
                        s3_key,
                        box
                    )
                )

                # ------------------------------------------------
                # Search face
                # ------------------------------------------------

                search_response = (
                    rekognition
                    .search_faces_by_image(

                        CollectionId=(
                            COLLECTION_ID
                        ),

                        Image={
                            "Bytes": face_bytes
                        },

                        FaceMatchThreshold=90,

                        MaxFaces=1
                    )
                )

                matches = (
                    search_response
                    .get(
                        "FaceMatches",
                        []
                    )
                )

                if matches:

                    match = matches[0]

                    student_name = (
                        match["Face"]
                        ["ExternalImageId"]
                    )

                    confidence = (
                        match["Similarity"]
                    )

                    # --------------------------------------------
                    # Mark only once
                    # --------------------------------------------

                    if (
                        student_name
                        not in marked_names
                    ):

                        marked_names.add(
                            student_name
                        )

                        mark_student_present(
                            student_name,
                            attendance_column
                        )

                        print(
                            f"Present: "
                            f"{student_name}"
                        )

                        print(
                            f"Confidence: "
                            f"{confidence:.2f}%"
                        )

                    else:

                        print(
                            f"{student_name} "
                            f"already marked present."
                        )

                else:

                    print(
                        f"Face {index + 1} "
                        f"not recognized."
                    )

        except Exception as e:

            print(
                f"Error processing "
                f"{image_name}: {e}"
            )

    return marked_names


# ============================================================
# MAIN PROGRAM
# ============================================================

def main():

    print("=" * 60)

    print(
        "     AWS FACE RECOGNITION ATTENDANCE SYSTEM"
    )

    print("=" * 60)

    print(
        f"\nAWS Region: {AWS_REGION}"
    )

    print(
        f"S3 Bucket: {S3_BUCKET}"
    )

    print(
        f"Collection: {COLLECTION_ID}"
    )

    # --------------------------------------------------------
    # Check folders
    # --------------------------------------------------------

    check_required_folders()

    # --------------------------------------------------------
    # Get student names
    # --------------------------------------------------------

    student_names = get_student_names()

    if not student_names:

        raise ValueError(
            "No student images found in "
            "the students folder."
        )

    print(
        f"\nStudents found: "
        f"{len(student_names)}"
    )

    for name in student_names:

        print(
            f"  - {name}"
        )

    # --------------------------------------------------------
    # Upload student images
    # --------------------------------------------------------

    print(
        "\nUploading student images..."
    )

    upload_folder_to_s3(
        STUDENTS_FOLDER,
        "students"
    )

    # --------------------------------------------------------
    # Upload classroom images
    # --------------------------------------------------------

    print(
        "\nUploading classroom images..."
    )

    upload_folder_to_s3(
        CHECK_FOLDER,
        "check_photos"
    )

    # --------------------------------------------------------
    # Ensure collection exists
    # --------------------------------------------------------

    ensure_collection()

    # --------------------------------------------------------
    # Clear old collection
    # --------------------------------------------------------

    clear_collection()

    # --------------------------------------------------------
    # Index student faces
    # --------------------------------------------------------

    index_student_faces()

    # --------------------------------------------------------
    # Create timestamp
    # --------------------------------------------------------

    timestamp = datetime.now().strftime(
        "%d-%m-%Y %H:%M:%S"
    )

    # --------------------------------------------------------
    # Create new attendance column
    # --------------------------------------------------------

    attendance_column = (
        prepare_attendance_excel(
            student_names,
            timestamp
        )
    )

    # --------------------------------------------------------
    # Process classroom images
    # --------------------------------------------------------

    marked_students = (
        process_check_images(
            attendance_column
        )
    )

    # --------------------------------------------------------
    # Final result
    # --------------------------------------------------------

    print("\n" + "=" * 60)

    print(
        "ATTENDANCE MARKING COMPLETE!"
    )

    print(
        f"Present: "
        f"{len(marked_students)}"
    )

    print(
        f"Absent: "
        f"{len(student_names) - len(marked_students)}"
    )

    print(
        f"\nExcel file created/updated:"
    )

    print(
        ATTENDANCE_FILE
    )

    print("=" * 60)


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    try:

        main()

    except NoCredentialsError:

        print(
            "\nAWS credentials not found."
        )

        print(
            "Run 'aws configure' first."
        )

    except Exception as e:

        print(
            f"\nProgram stopped:"
        )

        print(e)
