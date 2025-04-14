Okay, let's prepare a comprehensive project document for your **Online Exam Portal**. This document explains the project's purpose, flow, technology stack, usage, and overall structure.

---

## Project Documentation: Online Exam Portal

**Version:** 1.0
**Date:** April 14, 2025

### 1. Introduction & Overview

The Online Exam Portal is a web-based application designed specifically for college environments to streamline the process of creating, administering, taking, and evaluating online examinations. It caters to three distinct user roles: **Admin**, **Teacher**, and **Student**, each with tailored permissions and functionalities.

A key feature of this portal is its integration with **Google's Gemini 1.5 Flash AI model** for automated evaluation of subjective answers (Short and Long Answer questions), providing quick feedback and potentially reducing grading workload. The system emphasizes security through JWT authentication and role-based access control, ensuring data integrity and appropriate user access.

Built with an Angular frontend and a Flask (Python) backend, communicating via a RESTful API and backed by a PostgreSQL database, the portal aims to provide a robust, scalable, and modern solution for online assessments.

### 2. Project Objectives

*   **Centralized Platform:** Provide a single platform for exam creation, scheduling, participation, and result management.
*   **Role-Based Access:** Implement distinct functionalities and data visibility for Admins, Teachers, and Students.
*   **Flexible Question Types:** Allow Teachers to create exams with Multiple Choice Questions (MCQ), Short Answer, and Long Answer questions.
*   **Secure Authentication:** Utilize JWT for secure user login and session management.
*   **Automated Evaluation:** Leverage Gemini AI to evaluate subjective answers based on defined criteria (relevance, grammar, coherence, word count).
*   **User Management:** Enable Admins to verify and manage Teacher and Student accounts.
*   **Efficient Workflow:** Streamline the exam lifecycle from creation to result publication.

### 3. System Architecture & Workflow

The system operates on a client-server architecture:

1.  **Frontend (Angular):** Provides the user interface for Admins, Teachers, and Students to interact with the system. It communicates with the backend via REST API calls.
2.  **Backend (Flask):** Handles business logic, API request processing, database interactions, authentication, and communication with the AI service.
3.  **Database (PostgreSQL):** Stores all persistent data, including user information, exams, questions, student responses, and evaluations.
4.  **AI Service (Gemini 1.5 Flash):** Accessed via API call from the backend to evaluate student responses for subjective questions.

**Core Workflow:**

1.  **Registration & Verification:**
    *   Teachers/Students register via the Angular frontend (`POST /auth/register`).
    *   Their accounts are initially marked as unverified.
    *   An Admin logs in, views pending users (`GET /admin/users/pending`), and verifies accounts (`POST /admin/users/verify/<id>`).
2.  **Login & Authentication:**
    *   Verified users log in (`POST /auth/login`).
    *   The Flask backend verifies credentials and returns a JWT access token.
    *   The Angular frontend stores this token and includes it (`Authorization: Bearer <token>`) in headers for subsequent requests to protected API routes.
    *   Backend decorators (`@jwt_required`, `@admin_required`, etc.) validate the token and user role/status before granting access.
3.  **Exam Creation (Teacher):**
    *   Teacher logs in.
    *   Teacher creates a new exam (`POST /teacher/exams`), specifying title, description, schedule time (UTC), and duration.
    *   Teacher adds questions to the exam (`POST /teacher/exams/<id>/questions`), selecting the type (`MCQ`, `Short Answer`, `Long Answer`) and providing necessary details (text, marks, options/correct answer for MCQ, word limit for subjective).
4.  **Exam Participation (Student):**
    *   Student logs in.
    *   Student views available/active exams (`GET /student/exams/available`).
    *   Student selects an active exam and starts it (`GET /student/exams/<id>/take`). The frontend receives questions and remaining time.
    *   Student answers questions within the time limit.
    *   Student submits the exam (`POST /student/exams/<id>/submit`) with their answers in the specified JSON format `{"answers": [{"question_id": X, "response_text": "..."}]}`.
5.  **Evaluation:**
    *   MCQ answers might be auto-evaluated upon submission (if implemented) or during result processing based on the stored `correct_answer`.
    *   An **Admin** triggers AI evaluation for a specific subjective `StudentResponse` (`POST /admin/evaluate/response/<id>`).
    *   The Flask backend prepares a prompt including the question, student answer, max marks, word limit, and evaluation criteria.
    *   The backend calls the Gemini 1.5 Flash API via the `google-generativeai` library.
    *   The backend parses the AI's JSON response (containing `marks_awarded` and `feedback`).
    *   The backend stores the evaluation details (marks, feedback, evaluator ID) in the `Evaluations` table, linked to the `StudentResponse`.
6.  **Result Viewing:**
    *   **Student:** Views their own graded results, including marks per question and AI feedback (`GET /student/results/my`).
    *   **Teacher:** Views aggregated results and individual responses/evaluations for exams they created (`GET /teacher/exams/results/<id>`).
    *   **Admin:** Can view all results across all exams (`GET /admin/results/all`).

### 4. Technology Stack

*   **Frontend:** Angular (TypeScript, HTML, CSS/SCSS) - For building a dynamic, component-based user interface.
*   **Backend:** Flask (Python) - A lightweight, flexible microframework for building the REST API and handling logic.
*   **Database:** PostgreSQL - A robust, open-source relational database for data persistence.
*   **Authentication:** Flask-JWT-Extended - Library for handling JWT creation, verification, and management (including custom claims).
*   **AI Evaluation:** Google Gemini 1.5 Flash (via `google-generativeai` Python library) - For evaluating subjective answers.
*   **ORM:** SQLAlchemy (with Flask-SQLAlchemy) - For object-relational mapping, simplifying database interactions in Python.
*   **Migrations:** Flask-Migrate (Alembic) - For managing database schema changes systematically.
*   **API Testing:** Postman / Insomnia (Recommended) - Tools for sending requests to the API endpoints during development and testing.

### 5. Usage / Target Audience

*   **College Administrators (Admin Role):** Responsible for overall system setup, user account management (verification, deletion), ensuring system integrity, and potentially overseeing the evaluation process.
*   **College Faculty/Teachers (Teacher Role):** Responsible for creating courses/subjects (if applicable), creating and managing exams (questions, scheduling), and reviewing student performance on their exams.
*   **College Students (Student Role):** Responsible for viewing available exams, participating in exams within the allotted time, submitting answers, and viewing their results and feedback.

### 6. Document Explanation

This document provides a high-level overview suitable for stakeholders, new developers joining the project, or anyone needing to understand the system's purpose and structure.

*   **Sections 1-3 (Intro, Objectives, Flow):** Explain the *what* and *why* of the project and how users interact with it.
*   **Section 4 (Tech Stack):** Lists the *how* - the tools used to build the system.
*   **Section 5 (Usage):** Defines the *who* - the intended users and their general roles.
*   **Database/API:** While not fully detailed here, mentions of the schema and API point towards where more specific technical details can be found (in `models.py` and the detailed API documentation provided separately).

This document serves as a central reference point before diving into the specific code implementation or the detailed API endpoint specifications.

---