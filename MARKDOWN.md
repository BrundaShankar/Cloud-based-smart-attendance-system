# AWS-Based Student Attendance System

An automated student attendance system using Python, Amazon S3, and Amazon Rekognition for face recognition.

## Features

- Upload student images to Amazon S3
- Store registered student images in an Amazon Rekognition collection
- Detect multiple faces in classroom/group photographs
- Match detected faces with registered students
- Automatically mark recognized students as present
- Record student name and timestamp in an attendance CSV file
- Avoid duplicate attendance marking during a session

## Technologies Used

- Python
- Boto3
- Pillow
- Amazon S3
- Amazon Rekognition

## System Workflow

Student Images
↓
Amazon S3
↓
Amazon Rekognition Face Collection
↓
Classroom / Group Image
↓
Face Detection
↓
Face Cropping
↓
Face Matching
↓
Student Identification
↓
Attendance Recording

## Project Structure

student-attendance/
│
├── attendance_system.py
├── requirements.txt
├── README.md
└── .gitignore

The student images, classroom images, attendance file, and virtual environment are kept locally and are not included in the repository.

## Requirements

- Python 3.x
- AWS account
- Amazon S3 bucket
- Amazon Rekognition
- AWS credentials with appropriate permissions

## Installation

Clone the repository:

```bash
git clone YOUR_REPOSITORY_URL
cd student-attendance
