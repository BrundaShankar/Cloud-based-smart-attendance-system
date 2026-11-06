# ☁️ Cloud-Based Smart Attendance System using AWS

An AI-powered **Smart Attendance Management System** that automates student or employee attendance using facial recognition and cloud computing. The system uses **Amazon Rekognition** for face detection and comparison, **Amazon S3** for secure cloud image storage, and Python for application logic.

## 📌 Project Overview

Traditional attendance systems rely on manual roll calls, paper registers, or physical ID cards. These methods can be time-consuming, inefficient, and prone to proxy attendance.

This project introduces a cloud-based attendance system that uses facial recognition to identify registered individuals and automatically record their attendance.

The system captures a person's image, stores or accesses the image through Amazon S3, and uses Amazon Rekognition to compare the captured face against registered reference faces.

Once a match is identified, the system records the individual's attendance with the corresponding date and time.

## 🎯 Objectives

- Automate the attendance recording process.
- Reduce manual effort and human errors.
- Minimize proxy attendance through facial recognition.
- Use AWS cloud services for image storage and recognition.
- Provide a scalable and efficient attendance management solution.
- Maintain organized attendance records.

## 🏗️ System Architecture

![Cloud-Based Smart Attendance System Architecture](architecture.png)

### Workflow

1. **User Registration:** Register students or employees and collect their reference face images.
2. **Image Capture:** Capture the person's image using a camera or upload an image.
3. **Amazon S3 Storage:** Upload and store images in an AWS S3 bucket.
4. **Face Recognition:** Amazon Rekognition detects and compares faces against registered reference images.
5. **Identity Verification:** Identify the individual based on the configured similarity threshold.
6. **Attendance Recording:** Record the matched person's ID, name, date, and time.
7. **Attendance Management:** Store and display attendance records for further monitoring and reporting.

## 🛠️ Technologies Used

| Technology | Purpose |
|---|---|
| Python | Application development and processing |
| AWS S3 | Cloud storage for face images |
| Amazon Rekognition | Face detection and comparison |
| AWS IAM | Access management and permissions |
| Boto3 | Python SDK for AWS services |
| OpenCV | Image capture and preprocessing, if used |
| Streamlit / Flask | User interface, if implemented |
| CSV / Database | Attendance record storage |

## ☁️ AWS Services
