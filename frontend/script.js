document.addEventListener('DOMContentLoaded', () => {
    // --- Configuration ---
    const API_BASE_URL = 'http://127.0.0.1:5000/api'; // Your backend URL

    // --- State Variables ---
    let authToken = localStorage.getItem('authToken');
    let userRole = localStorage.getItem('userRole');
    let currentExamTimer = null; // To hold the interval ID for the exam timer
    let currentTakingExamId = null; // Store the ID of the exam being taken

    // --- DOM References ---
    const loadingIndicator = document.getElementById('loading-indicator');
    // Views
    const loginView = document.getElementById('login-view');
    const registerView = document.getElementById('register-view');
    const teacherView = document.getElementById('teacher-view');
    const studentView = document.getElementById('student-view');
    const allViews = [loginView, registerView, teacherView, studentView];
    // Login/Register Forms
    const loginForm = document.getElementById('login-form');
    const usernameInput = document.getElementById('username');
    const passwordInput = document.getElementById('password');
    const loginError = document.getElementById('login-error');
    const registerForm = document.getElementById('register-form');
    const regUsernameInput = document.getElementById('reg-username');
    const regPasswordInput = document.getElementById('reg-password');
    const regRoleInput = document.getElementById('reg-role');
    const registerError = document.getElementById('register-error');
    const registerSuccess = document.getElementById('register-success');
    const showRegisterBtn = document.getElementById('show-register-btn');
    const showLoginBtn = document.getElementById('show-login-btn');

    // Teacher View Elements
    const teacherContent = document.getElementById('teacher-content');
    const teacherExamsListView = document.getElementById('teacher-exams-list-view');
    const createExamFormView = document.getElementById('create-exam-form-view');
    const submissionsView = document.getElementById('submissions-view');
    const teacherExamsTableBody = document.getElementById('teacher-exams-table-body');
    const showCreateExamFormBtn = document.getElementById('show-create-exam-form-btn');
    const createExamForm = document.getElementById('create-exam-form');
    const questionSelectionArea = document.getElementById('question-selection-area');
    const cancelCreateExamBtn = document.getElementById('cancel-create-exam-btn');
    const createExamError = document.getElementById('create-exam-error');
    const createExamSuccess = document.getElementById('create-exam-success');
    const submissionsTableBody = document.getElementById('submissions-table-body');
    const submissionsExamTitle = document.getElementById('submissions-exam-title');
    const backToExamsBtn = document.getElementById('back-to-exams-btn');
    const submissionDetailModalBody = document.getElementById('submission-detail-modal-body');
    const submissionDetailModal = new bootstrap.Modal(document.getElementById('submissionDetailModal')); // Bootstrap Modal instance

    // Student View Elements
    const studentContent = document.getElementById('student-content');
    const availableExamsView = document.getElementById('available-exams-view');
    const takeExamView = document.getElementById('take-exam-view');
    const resultsView = document.getElementById('results-view');
    const availableExamsTableBody = document.getElementById('available-exams-table-body');
    const takeExamForm = document.getElementById('take-exam-form');
    const takeExamTitle = document.getElementById('take-exam-title');
    const examTimerDisplay = document.getElementById('exam-timer');
    const examQuestionsArea = document.getElementById('exam-questions-area');
    const takeExamQuestionCount = document.getElementById('take-exam-question-count');
    const submitExamError = document.getElementById('submit-exam-error');
    const submitExamSuccess = document.getElementById('submit-exam-success');
    const resultsTableBody = document.getElementById('results-table-body');
    const showResultsBtn = document.getElementById('show-results-btn');
    const showAvailableExamsBtn = document.getElementById('show-available-exams-btn');
    const resultDetailModalBody = document.getElementById('result-detail-modal-body');
    const resultDetailModal = new bootstrap.Modal(document.getElementById('resultDetailModal')); // Bootstrap Modal instance


    // Logout Buttons
    const logoutBtnTeacher = document.getElementById('logout-btn-teacher');
    const logoutBtnStudent = document.getElementById('logout-btn-student');

    // --- Utility Functions ---
    const showLoading = () => loadingIndicator.style.display = 'block';
    const hideLoading = () => loadingIndicator.style.display = 'none';

    const showView = (viewToShow) => {
        allViews.forEach(view => view.style.display = 'none');
        if (viewToShow) {
            viewToShow.style.display = 'block';
        }
    };

    // Reset forms and error messages
    const resetForms = () => {
        loginForm.reset();
        registerForm.reset();
        createExamForm.reset();
        takeExamForm.reset();
        loginError.textContent = '';
        registerError.textContent = '';
        registerSuccess.textContent = '';
        createExamError.textContent = '';
        createExamSuccess.textContent = '';
        submitExamError.textContent = '';
        submitExamSuccess.textContent = '';
        questionSelectionArea.innerHTML = '<p>Loading questions...</p>'; // Reset question area
    };

    // API Request Helper
    const apiRequest = async (method, endpoint, data = null, requiresAuth = true) => {
        showLoading();
        const url = `${API_BASE_URL}${endpoint}`;
        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json',
            },
        };

        if (requiresAuth && authToken) {
            options.headers['Authorization'] = `Bearer ${authToken}`;
        }

        if (data) {
            options.body = JSON.stringify(data);
        }

        try {
            const response = await fetch(url, options);
            const responseData = await response.json(); // Attempt to parse JSON regardless of status

            if (!response.ok) {
                // Use the message from the JSON body if available, otherwise use statusText
                const errorMessage = responseData.message || response.statusText || `Request failed with status ${response.status}`;
                console.error(`API Error (${response.status}): ${errorMessage}`, responseData);
                throw new Error(errorMessage); // Throw error to be caught below
            }

            hideLoading();
            return responseData; // Return parsed JSON data on success
        } catch (error) {
            console.error('API Request Failed:', error);
            hideLoading();
            // Re-throw the refined error message
            throw new Error(error.message || 'An unexpected error occurred. Check the console.');
        }
    };

    // --- Authentication Functions ---
    const handleLogin = async (event) => {
        event.preventDefault();
        loginError.textContent = '';
        const username = usernameInput.value;
        const password = passwordInput.value;

        try {
            const data = await apiRequest('POST', '/auth/login', { username, password }, false);
            authToken = data.access_token;
            userRole = data.role;
            localStorage.setItem('authToken', authToken);
            localStorage.setItem('userRole', userRole);
            navigateToDashboard();
            resetForms();
        } catch (error) {
            loginError.textContent = `Login failed: ${error.message}`;
        }
    };

    const handleRegister = async (event) => {
        event.preventDefault();
        registerError.textContent = '';
        registerSuccess.textContent = '';
        const username = regUsernameInput.value;
        const password = regPasswordInput.value;
        const role = regRoleInput.value;

        try {
            await apiRequest('POST', '/auth/register', { username, password, role }, false);
            registerSuccess.textContent = 'Registration successful! Please login.';
            resetForms();
            showView(loginView); // Switch back to login view after successful registration
        } catch (error) {
            registerError.textContent = `Registration failed: ${error.message}`;
        }
    };

    const handleLogout = () => {
        authToken = null;
        userRole = null;
        localStorage.removeItem('authToken');
        localStorage.removeItem('userRole');
        clearInterval(currentExamTimer); // Clear any running exam timer
        currentExamTimer = null;
        currentTakingExamId = null;
        resetForms();
        showView(loginView);
    };

    const navigateToDashboard = () => {
        if (authToken && userRole) {
            if (userRole === 'teacher') {
                showView(teacherView);
                showTeacherSection(teacherExamsListView); // Default to exams list
                fetchTeacherExams();
            } else if (userRole === 'student') {
                showView(studentView);
                showStudentSection(availableExamsView); // Default to available exams
                fetchAvailableExams();
                fetchResults(); // Also load results for the results tab
            } else {
                showView(loginView); // Fallback
            }
        } else {
            showView(loginView);
        }
    };

    // --- Teacher Functions ---

    const showTeacherSection = (sectionToShow) => {
        [teacherExamsListView, createExamFormView, submissionsView].forEach(s => s.style.display = 'none');
        sectionToShow.style.display = 'block';
    };

    const fetchTeacherExams = async () => {
        try {
            const data = await apiRequest('GET', '/teacher/exams');
            teacherExamsTableBody.innerHTML = ''; // Clear existing rows
            if (data.exams && data.exams.length > 0) {
                data.exams.forEach(exam => {
                    const row = teacherExamsTableBody.insertRow();
                    row.innerHTML = `
                        <td>${exam.title}</td>
                        <td>${exam.duration_minutes}</td>
                        <td>${new Date(exam.start_time).toLocaleString()}</td>
                        <td>${new Date(exam.end_time).toLocaleString()}</td>
                        <td>${exam.question_count}</td>
                        <td>
                            <button class="btn btn-sm btn-info view-submissions-btn" data-exam-id="${exam.id}" data-exam-title="${exam.title}">View Submissions</button>
                            <!-- Add Edit/Delete buttons later if needed -->
                        </td>
                    `;
                });
            } else {
                teacherExamsTableBody.innerHTML = '<tr><td colspan="6" class="text-center">No exams created yet.</td></tr>';
            }
        } catch (error) {
            teacherExamsTableBody.innerHTML = `<tr><td colspan="6" class="text-center text-danger">Error loading exams: ${error.message}</td></tr>`;
        }
    };

    const fetchQuestionsForExamForm = async () => {
        questionSelectionArea.innerHTML = '<p>Loading questions...</p>';
         try {
            const data = await apiRequest('GET', '/teacher/questions');
            questionSelectionArea.innerHTML = ''; // Clear loading message
            if (data.questions && data.questions.length > 0) {
                 data.questions.forEach(q => {
                    const div = document.createElement('div');
                    div.classList.add('form-check');
                    div.innerHTML = `
                        <input class="form-check-input question-checkbox" type="checkbox" value="${q.id}" id="q-${q.id}">
                        <label class="form-check-label" for="q-${q.id}">
                           (${q.points} pts) ${q.question_text.substring(0, 100)}${q.question_text.length > 100 ? '...' : ''}
                        </label>
                    `;
                    questionSelectionArea.appendChild(div);
                 });
            } else {
                 questionSelectionArea.innerHTML = '<p class="text-muted">No questions found in the question bank.</p>';
            }
         } catch (error) {
             questionSelectionArea.innerHTML = `<p class="text-danger">Error loading questions: ${error.message}</p>`;
         }
    };

    const handleCreateExam = async (event) => {
        event.preventDefault();
        createExamError.textContent = '';
        createExamSuccess.textContent = '';

        const selectedCheckboxes = questionSelectionArea.querySelectorAll('.question-checkbox:checked');
        const questionIds = Array.from(selectedCheckboxes).map(cb => parseInt(cb.value));

        if (questionIds.length === 0) {
            createExamError.textContent = 'Please select at least one question.';
            return;
        }

        // Convert local datetime-local input to UTC ISO string
        const startTimeLocal = document.getElementById('exam-start-time').value;
        const endTimeLocal = document.getElementById('exam-end-time').value;

        // Check if values are present before creating Date objects
        if (!startTimeLocal || !endTimeLocal) {
             createExamError.textContent = 'Please select both start and end times.';
             return;
        }

        const startTimeUTC = new Date(startTimeLocal).toISOString();
        const endTimeUTC = new Date(endTimeLocal).toISOString();


        const examData = {
            title: document.getElementById('exam-title').value,
            description: document.getElementById('exam-description').value,
            duration_minutes: parseInt(document.getElementById('exam-duration').value),
            start_time: startTimeUTC,
            end_time: endTimeUTC,
            question_ids: questionIds
        };

        try {
            await apiRequest('POST', '/teacher/exams', examData);
            createExamSuccess.textContent = 'Exam created successfully!';
            createExamForm.reset(); // Reset form fields
            questionSelectionArea.innerHTML = '<p>Loading questions...</p>'; // Reset questions area
            setTimeout(() => {
                 createExamSuccess.textContent = ''; // Clear success message
                 showTeacherSection(teacherExamsListView); // Go back to list view
                 fetchTeacherExams(); // Refresh list
            }, 1500);
        } catch (error) {
             createExamError.textContent = `Failed to create exam: ${error.message}`;
        }
    };

    const fetchSubmissions = async (examId, examTitle) => {
        showTeacherSection(submissionsView);
        submissionsExamTitle.textContent = `Submissions for Exam: ${examTitle}`;
        submissionsTableBody.innerHTML = '<tr><td colspan="5" class="text-center">Loading submissions...</td></tr>';
        try {
            const data = await apiRequest('GET', `/teacher/exams/${examId}/submissions`);
            submissionsTableBody.innerHTML = ''; // Clear loading message
            if (data.submissions && data.submissions.length > 0) {
                 data.submissions.forEach(sub => {
                     const row = submissionsTableBody.insertRow();
                     row.innerHTML = `
                        <td>${sub.student_username}</td>
                        <td>${new Date(sub.submitted_at).toLocaleString()}</td>
                        <td><span class="badge bg-${sub.status === 'evaluated' ? 'success' : 'warning'}">${sub.status}</span></td>
                        <td>${sub.total_score !== null ? sub.total_score : 'N/A'}</td>
                        <td>
                            ${sub.status === 'evaluated' ? `<button class="btn btn-sm btn-outline-primary view-submission-details-btn" data-submission-id="${sub.submission_id}">View Details</button>` : ''}
                        </td>
                     `;
                 });
            } else {
                 submissionsTableBody.innerHTML = '<tr><td colspan="5" class="text-center">No submissions received yet.</td></tr>';
            }
        } catch (error) {
             submissionsTableBody.innerHTML = `<tr><td colspan="5" class="text-center text-danger">Error loading submissions: ${error.message}</td></tr>`;
        }
    };

    const fetchSubmissionDetails = async (submissionId) => {
        submissionDetailModalBody.innerHTML = '<p>Loading details...</p>';
        submissionDetailModal.show();
         try {
            const data = await apiRequest('GET', `/teacher/submissions/${submissionId}/details`);
            let detailsHtml = `
                <p><strong>Student:</strong> ${data.student_username}</p>
                <p><strong>Exam:</strong> ${data.exam_title}</p>
                <p><strong>Submitted:</strong> ${new Date(data.submitted_at).toLocaleString()}</p>
                <p><strong>Status:</strong> ${data.status}</p>
                <p><strong>Total Score:</strong> ${data.total_score !== null ? data.total_score : 'N/A'}</p>
                <hr/>
                <h5>Answers:</h5>
            `;
            if (data.answers && data.answers.length > 0) {
                data.answers.forEach((ans, index) => {
                    detailsHtml += `
                        <div class="mb-3 p-2 border rounded">
                            <p><strong>Q${index + 1} (${ans.max_points} pts):</strong> ${ans.question_text}</p>
                            <p><em>Student Answer:</em> ${ans.student_answer || '<i>No answer provided</i>'}</p>
                            <p><strong>Mark:</strong> ${ans.evaluated_mark !== null ? ans.evaluated_mark : 'Not evaluated'}</p>
                            ${ans.evaluation_feedback ? `<p><small><i>Feedback:</i> ${ans.evaluation_feedback}</small></p>` : ''}
                        </div>
                    `;
                });
            } else {
                detailsHtml += '<p>No answer details found.</p>';
            }
            submissionDetailModalBody.innerHTML = detailsHtml;

         } catch (error) {
             submissionDetailModalBody.innerHTML = `<p class="text-danger">Error loading details: ${error.message}</p>`;
         }
    };


    // --- Student Functions ---

     const showStudentSection = (sectionToShow) => {
        [availableExamsView, takeExamView, resultsView].forEach(s => s.style.display = 'none');
        sectionToShow.style.display = 'block';
    };

    const fetchAvailableExams = async () => {
        availableExamsTableBody.innerHTML = '<tr><td colspan="5" class="text-center">Loading available exams...</td></tr>';
        try {
            const data = await apiRequest('GET', '/student/exams/available');
            availableExamsTableBody.innerHTML = ''; // Clear loading
            if (data.exams && data.exams.length > 0) {
                data.exams.forEach(exam => {
                    const row = availableExamsTableBody.insertRow();
                    row.innerHTML = `
                        <td>${exam.title}</td>
                        <td>${exam.description || '-'}</td>
                        <td>${exam.duration_minutes}</td>
                        <td>${new Date(exam.end_time).toLocaleString()}</td>
                        <td>
                            <button class="btn btn-sm btn-success start-exam-btn" data-exam-id="${exam.id}">Start Exam</button>
                        </td>
                    `;
                });
            } else {
                 availableExamsTableBody.innerHTML = '<tr><td colspan="5" class="text-center">No exams currently available for you.</td></tr>';
            }
        } catch (error) {
            availableExamsTableBody.innerHTML = `<tr><td colspan="5" class="text-center text-danger">Error loading exams: ${error.message}</td></tr>`;
        }
    };

    const startExam = async (examId) => {
        try {
            const data = await apiRequest('GET', `/student/exams/${examId}/start`);
            currentTakingExamId = examId; // Store the ID of the exam being taken
            showStudentSection(takeExamView);
            takeExamTitle.textContent = `Taking Exam: ${data.title}`;
            takeExamQuestionCount.textContent = `${data.questions.length} Questions`;
            examQuestionsArea.innerHTML = ''; // Clear previous questions
            submitExamError.textContent = '';
            submitExamSuccess.textContent = '';

            data.questions.forEach((q, index) => {
                const questionBlock = document.createElement('div');
                questionBlock.classList.add('question-block');
                questionBlock.innerHTML = `
                    <label for="q-ans-${q.id}">Q${index + 1}. (${q.points} pts) ${q.question_text}</label>
                    <textarea class="form-control" id="q-ans-${q.id}" name="answer_${q.id}" rows="3" required data-question-id="${q.id}"></textarea>
                `;
                examQuestionsArea.appendChild(questionBlock);
            });

            startTimer(data.duration_minutes, examTimerDisplay);

        } catch (error) {
            // If starting fails, likely show error on the available exams view
            alert(`Error starting exam: ${error.message}`);
            showStudentSection(availableExamsView);
        }
    };

    const startTimer = (durationMinutes, display) => {
        clearInterval(currentExamTimer); // Clear any existing timer
        let timer = durationMinutes * 60;
        let minutes, seconds;

        currentExamTimer = setInterval(() => {
            minutes = parseInt(timer / 60, 10);
            seconds = parseInt(timer % 60, 10);

            minutes = minutes < 10 ? "0" + minutes : minutes;
            seconds = seconds < 10 ? "0" + seconds : seconds;

            display.textContent = minutes + ":" + seconds;

            if (--timer < 0) {
                clearInterval(currentExamTimer);
                currentExamTimer = null;
                display.textContent = "Time Up!";
                alert("Time is up! Submitting your exam automatically.");
                handleSubmitExam(new Event('submit')); // Trigger submission
            }
        }, 1000);
    };

    const handleSubmitExam = async (event) => {
         event.preventDefault();
         if (!currentTakingExamId) return; // Should not happen

         clearInterval(currentExamTimer); // Stop timer immediately
         currentExamTimer = null;
         submitExamError.textContent = '';
         submitExamSuccess.textContent = '';

         const answers = [];
         const answerTextareas = examQuestionsArea.querySelectorAll('textarea[data-question-id]');
         answerTextareas.forEach(textarea => {
             answers.push({
                 question_id: parseInt(textarea.getAttribute('data-question-id')),
                 answer_text: textarea.value
             });
         });

         const submissionData = { answers: answers };

         try {
             await apiRequest('POST', `/student/exams/${currentTakingExamId}/submit`, submissionData);
             submitExamSuccess.textContent = 'Exam submitted successfully!';
             takeExamForm.reset();
             currentTakingExamId = null; // Reset exam ID
             setTimeout(() => {
                 submitExamSuccess.textContent = '';
                 showStudentSection(availableExamsView); // Go back to available exams
                 fetchAvailableExams(); // Refresh list (exam should disappear)
                 fetchResults(); // Refresh results list
             }, 2000);
         } catch (error) {
             submitExamError.textContent = `Submission failed: ${error.message}`;
             // Optionally restart timer if submission fails? Or just let them retry?
             // For now, just show error. They might need to refresh if it's a network issue.
         }
    };

    const fetchResults = async () => {
         resultsTableBody.innerHTML = '<tr><td colspan="6" class="text-center">Loading results...</td></tr>';
        try {
            const data = await apiRequest('GET', '/student/results');
            resultsTableBody.innerHTML = ''; // Clear loading
            if (data.results && data.results.length > 0) {
                data.results.forEach(res => {
                    const row = resultsTableBody.insertRow();
                    row.innerHTML = `
                        <td>${res.exam_title}</td>
                        <td>${new Date(res.submitted_at).toLocaleString()}</td>
                        <td>${res.score !== null ? res.score : 'N/A'}</td>
                        <td>${res.max_score !== null ? res.max_score : 'N/A'}</td>
                        <td><span class="badge bg-success">${res.status}</span></td>
                         <td>
                            <button class="btn btn-sm btn-outline-primary view-result-details-btn" data-submission-id="${res.submission_id}">View Details</button>
                        </td>
                    `;
                });
            } else {
                 resultsTableBody.innerHTML = '<tr><td colspan="6" class="text-center">No evaluated results found.</td></tr>';
            }
        } catch (error) {
             resultsTableBody.innerHTML = `<tr><td colspan="6" class="text-center text-danger">Error loading results: ${error.message}</td></tr>`;
        }
    };

     const fetchResultDetails = async (submissionId) => {
        resultDetailModalBody.innerHTML = '<p>Loading details...</p>';
        resultDetailModal.show();
         try {
            const data = await apiRequest('GET', `/student/results/${submissionId}/details`);
            let detailsHtml = `
                <p><strong>Exam:</strong> ${data.exam_title}</p>
                <p><strong>Total Score:</strong> ${data.total_score !== null ? data.total_score : 'N/A'} / ${data.max_score !== null ? data.max_score : 'N/A'}</p>
                <hr/>
                <h5>Question Breakdown:</h5>
            `;
            if (data.details && data.details.length > 0) {
                data.details.forEach((det, index) => {
                    detailsHtml += `
                        <div class="mb-3 p-2 border rounded">
                            <p><strong>Q${index + 1} (${det.max_points} pts):</strong> ${det.question_text}</p>
                            <p><em>Your Answer:</em> ${det.student_answer || '<i>No answer provided</i>'}</p>
                            <p><strong>Mark Awarded:</strong> ${det.evaluated_mark !== null ? det.evaluated_mark : 'N/A'}</p>
                             ${det.feedback ? `<p><small><i>Feedback:</i> ${det.feedback}</small></p>` : ''}
                        </div>
                    `;
                });
            } else {
                detailsHtml += '<p>No detailed breakdown available.</p>';
            }
            resultDetailModalBody.innerHTML = detailsHtml;

         } catch (error) {
             resultDetailModalBody.innerHTML = `<p class="text-danger">Error loading details: ${error.message}</p>`;
         }
    };


    // --- Event Listeners ---
    loginForm.addEventListener('submit', handleLogin);
    registerForm.addEventListener('submit', handleRegister);
    logoutBtnTeacher.addEventListener('click', handleLogout);
    logoutBtnStudent.addEventListener('click', handleLogout);

    showRegisterBtn.addEventListener('click', () => showView(registerView));
    showLoginBtn.addEventListener('click', () => showView(loginView));

    // Teacher Event Listeners
    showCreateExamFormBtn.addEventListener('click', () => {
        showTeacherSection(createExamFormView);
        fetchQuestionsForExamForm(); // Load questions when form is shown
        createExamForm.reset(); // Clear form
        createExamError.textContent = '';
        createExamSuccess.textContent = '';
    });
    cancelCreateExamBtn.addEventListener('click', () => {
        showTeacherSection(teacherExamsListView); // Go back without saving
    });
    createExamForm.addEventListener('submit', handleCreateExam);
    backToExamsBtn.addEventListener('click', () => showTeacherSection(teacherExamsListView));

    // Use event delegation for dynamically added buttons (View Submissions / Details)
    teacherExamsTableBody.addEventListener('click', (event) => {
         if (event.target.classList.contains('view-submissions-btn')) {
             const examId = event.target.dataset.examId;
             const examTitle = event.target.dataset.examTitle;
             fetchSubmissions(examId, examTitle);
         }
    });
     submissionsTableBody.addEventListener('click', (event) => {
         if (event.target.classList.contains('view-submission-details-btn')) {
             const submissionId = event.target.dataset.submissionId;
             fetchSubmissionDetails(submissionId);
         }
    });


    // Student Event Listeners
    availableExamsTableBody.addEventListener('click', (event) => {
         if (event.target.classList.contains('start-exam-btn')) {
             const examId = event.target.dataset.examId;
             if (confirm('Are you sure you want to start this exam? The timer will begin immediately.')) {
                startExam(examId);
             }
         }
    });
    takeExamForm.addEventListener('submit', handleSubmitExam);
    showAvailableExamsBtn.addEventListener('click', () => {
        showStudentSection(availableExamsView);
        fetchAvailableExams(); // Refresh list when tab is clicked
    });
     showResultsBtn.addEventListener('click', () => {
        showStudentSection(resultsView);
        fetchResults(); // Refresh list when tab is clicked
    });
     resultsTableBody.addEventListener('click', (event) => {
         if (event.target.classList.contains('view-result-details-btn')) {
             const submissionId = event.target.dataset.submissionId;
             fetchResultDetails(submissionId);
         }
    });


    // --- Initial Load ---
    navigateToDashboard(); // Check token and navigate on page load

}); // End DOMContentLoaded