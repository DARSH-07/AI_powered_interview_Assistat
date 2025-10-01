// Global Application State
class InterviewApp {
    constructor() {
        this.currentCandidate = null;
        this.currentSession = null;
        this.websocket = null;
        this.timer = null;
        this.timerStart = null;
        this.questionStartTime = null;
        
        this.init();
    }

    init() {
        this.bindEvents();
        this.checkExistingSession();
        this.initWebSocket();
    }

    bindEvents() {
        // File upload events
        this.bindFileUploadEvents();
        
        // Form events
        this.bindFormEvents();
        
        // Tab events
        this.bindTabEvents();
        
        // Modal events
        this.bindModalEvents();
    }

    bindFileUploadEvents() {
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('resumeFile');
        const browseBtn = document.getElementById('browseFiles');

        // Drag and drop events
        uploadArea?.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('drag-over');
        });

        uploadArea?.addEventListener('dragleave', () => {
            uploadArea.classList.remove('drag-over');
        });

        uploadArea?.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('drag-over');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.handleFileUpload(files[0]);
            }
        });

        // Click to upload
        uploadArea?.addEventListener('click', () => fileInput?.click());
        browseBtn?.addEventListener('click', () => fileInput?.click());

        fileInput?.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                this.handleFileUpload(e.target.files[0]);
            }
        });
    }

    bindFormEvents() {
        // Candidate info form
        const candidateForm = document.getElementById('candidateInfoForm');
        candidateForm?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.updateCandidateInfo();
        });

        // Answer submission
        const submitBtn = document.getElementById('submitAnswer');
        const answerInput = document.getElementById('answerInput');
        
        submitBtn?.addEventListener('click', () => {
            this.submitAnswer();
        });

        answerInput?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && e.ctrlKey) {
                this.submitAnswer();
            }
        });
    }

    bindTabEvents() {
        // Dashboard refresh
        const refreshBtn = document.getElementById('refreshDashboard');
        refreshBtn?.addEventListener('click', () => {
            this.loadDashboardData();
        });

        // Tab switch events
        const interviewerTab = document.getElementById('interviewer-tab');
        interviewerTab?.addEventListener('shown.bs.tab', () => {
            this.loadDashboardData();
        });
    }

    bindModalEvents() {
        // Welcome back modal events
        const continueBtn = document.getElementById('continueSession');
        const newSessionBtn = document.getElementById('startNewSession');

        continueBtn?.addEventListener('click', () => {
            this.continueExistingSession();
        });

        newSessionBtn?.addEventListener('click', () => {
            this.startNewSession();
        });
    }

    async checkExistingSession() {
        try {
            const response = await fetch('/api/check-session/');
            const data = await response.json();
            
            if (data.has_session) {
                this.showWelcomeBackModal(data);
            }
        } catch (error) {
            console.error('Error checking session:', error);
        }
    }

    showWelcomeBackModal(sessionData) {
        const modal = new bootstrap.Modal(document.getElementById('welcomeBackModal'));
        const sessionInfo = document.getElementById('sessionInfo');
        
        sessionInfo.innerHTML = `
            <div class="alert alert-info">
                <strong>Candidate:</strong> ${sessionData.candidate.name || 'Unnamed'}<br>
                <strong>Status:</strong> ${sessionData.candidate.interview_status}<br>
                <strong>Progress:</strong> Question ${sessionData.current_question_number}/6
            </div>
        `;
        
        this.pendingSession = sessionData;
        modal.show();
    }

    continueExistingSession() {
        if (this.pendingSession) {
            this.currentCandidate = this.pendingSession.candidate;
            this.showCandidateInfo(this.currentCandidate);
            this.showProgress();
            
            // Resume from current question
            if (this.pendingSession.current_question) {
                this.displayQuestion(
                    this.pendingSession.current_question,
                    this.pendingSession.current_question_number,
                    this.pendingSession.time_allocated
                );
            }
        }
        
        const modal = bootstrap.Modal.getInstance(document.getElementById('welcomeBackModal'));
        modal.hide();
    }

    startNewSession() {
        // Clear existing session
        this.currentCandidate = null;
        this.currentSession = null;
        
        const modal = bootstrap.Modal.getInstance(document.getElementById('welcomeBackModal'));
        modal.hide();
    }

    async handleFileUpload(file) {
        try {
            // Validate file
            if (!this.validateFile(file)) {
                return;
            }

            this.showLoading('Uploading and parsing resume...');
            
            const formData = new FormData();
            formData.append('resume', file);

            const response = await fetch('/api/upload-resume/', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (data.success) {
                this.currentCandidate = {
                    id: data.candidate_id,
                    ...data.parsed_data
                };
                
                this.showCandidateInfoForm(data.parsed_data);
                this.addChatMessage('system', 'Resume uploaded successfully! Please verify your information below.');
            } else {
                this.showError(data.error || 'Upload failed');
            }
        } catch (error) {
            console.error('Upload error:', error);
            this.showError('Upload failed. Please try again.');
        } finally {
            this.hideLoading();
        }
    }

    validateFile(file) {
        // Check file type
        const allowedTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
        if (!allowedTypes.includes(file.type)) {
            this.showError('Please upload a PDF or DOCX file.');
            return false;
        }

        // Check file size (5MB limit)
        if (file.size > 5 * 1024 * 1024) {
            this.showError('File too large. Maximum size is 5MB.');
            return false;
        }

        return true;
    }

    showCandidateInfoForm(parsedData) {
        const uploadCard = document.getElementById('resumeUploadCard');
        const infoCard = document.getElementById('candidateInfoCard');
        
        uploadCard?.classList.add('d-none');
        infoCard?.classList.remove('d-none');

        // Populate form with parsed data
        document.getElementById('candidateName').value = parsedData.name || '';
        document.getElementById('candidateEmail').value = parsedData.email || '';
        document.getElementById('candidatePhone').value = parsedData.phone || '';

        // Focus on first empty field
        const fields = ['candidateName', 'candidateEmail', 'candidatePhone'];
        for (const fieldId of fields) {
            const field = document.getElementById(fieldId);
            if (!field.value) {
                field.focus();
                break;
            }
        }
    }

    async updateCandidateInfo() {
        try {
            const formData = {
                candidate_id: this.currentCandidate.id,
                name: document.getElementById('candidateName').value,
                email: document.getElementById('candidateEmail').value,
                phone: document.getElementById('candidatePhone').value
            };

            // Validate required fields
            if (!formData.name || !formData.email || !formData.phone) {
                this.showError('Please fill in all required fields.');
                return;
            }

            this.showLoading('Starting interview...');

            // Update candidate info
            await fetch('/api/update-candidate-info/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });

            // Start interview
            const response = await fetch('/api/start-interview/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ candidate_id: this.currentCandidate.id })
            });

            const data = await response.json();

            if (data.success) {
                this.currentSession = { id: data.session_id };
                this.currentCandidate = { ...this.currentCandidate, ...formData };
                
                this.startInterview(data);
            } else {
                this.showError(data.error || 'Failed to start interview');
            }
        } catch (error) {
            console.error('Start interview error:', error);
            this.showError('Failed to start interview. Please try again.');
        } finally {
            this.hideLoading();
        }
    }

    startInterview(interviewData) {
        // Hide candidate info form and show progress
        document.getElementById('candidateInfoCard')?.classList.add('d-none');
        this.showProgress();
        
        // Display first question
        this.displayQuestion(
            interviewData.question,
            interviewData.question_number,
            interviewData.time_allocated
        );
        
        // Update progress
        this.updateProgress(1, 0);
        this.addChatMessage('system', 'Interview started! You have 6 questions to answer. Good luck!');
    }

    displayQuestion(questionText, questionNumber, timeAllocated) {
        // Add question to chat
        this.addChatMessage('question', questionText, {
            question_number: questionNumber,
            time_allocated: timeAllocated
        });

        // Update UI
        document.getElementById('questionCounter').textContent = `Question ${questionNumber}/6`;
        document.getElementById('answerInput').disabled = false;
        document.getElementById('submitAnswer').disabled = false;
        
        // Start timer
        this.startTimer(timeAllocated);
        
        // Focus on answer input
        document.getElementById('answerInput').focus();
        
        this.questionStartTime = Date.now();
    }

    startTimer(seconds) {
        this.clearTimer();
        
        const timerDisplay = document.getElementById('timerDisplay');
        const timerText = document.getElementById('timerText');
        const timerCircle = document.querySelector('.timer-circle');
        
        timerDisplay?.classList.remove('d-none');
        
        let timeLeft = seconds;
        this.timerStart = Date.now();
        
        const updateTimer = () => {
            const elapsed = Math.floor((Date.now() - this.timerStart) / 1000);
            timeLeft = Math.max(0, seconds - elapsed);
            
            const minutes = Math.floor(timeLeft / 60);
            const secs = timeLeft % 60;
            
            if (timerText) {
                timerText.textContent = `${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
            }
            
            // Update timer appearance based on time left
            if (timerCircle) {
                timerCircle.classList.remove('warning', 'danger');
                if (timeLeft <= 10) {
                    timerCircle.classList.add('danger');
                } else if (timeLeft <= 30) {
                    timerCircle.classList.add('warning');
                }
            }
            
            if (timeLeft <= 0) {
                this.timeUp();
                return;
            }
            
            this.timer = setTimeout(updateTimer, 1000);
        };
        
        updateTimer();
    }

    clearTimer() {
        if (this.timer) {
            clearTimeout(this.timer);
            this.timer = null;
        }
    }

    timeUp() {
        this.clearTimer();
        this.addChatMessage('system', 'Time\'s up! Submitting your current answer...');
        this.submitAnswer(true);
    }

    async submitAnswer(isTimeUp = false) {
        try {
            const answerText = document.getElementById('answerInput').value.trim();
            const timeTaken = this.questionStartTime ? 
                Math.floor((Date.now() - this.questionStartTime) / 1000) : 0;

            // Disable inputs
            document.getElementById('answerInput').disabled = true;
            document.getElementById('submitAnswer').disabled = true;
            
            this.clearTimer();
            document.getElementById('timerDisplay')?.classList.add('d-none');

            // Add answer to chat
            if (answerText || isTimeUp) {
                this.addChatMessage('answer', answerText || '(No answer provided)', {
                    time_taken: timeTaken
                });
            }

            this.showLoading('Evaluating answer...');

            const response = await fetch('/api/submit-answer/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    candidate_id: this.currentCandidate.id,
                    answer: answerText,
                    time_taken: timeTaken
                })
            });

            const data = await response.json();

            if (data.success) {
                // Clear answer input
                document.getElementById('answerInput').value = '';
                
                if (data.interview_completed) {
                    this.completeInterview(data);
                } else {
                    this.nextQuestion(data);
                }
            } else {
                this.showError(data.error || 'Failed to submit answer');
            }
        } catch (error) {
            console.error('Submit answer error:', error);
            this.showError('Failed to submit answer. Please try again.');
        } finally {
            this.hideLoading();
        }
    }

    nextQuestion(data) {
        // Update progress
        this.updateProgress(data.question_number, data.current_score || 0);
        
        // Add score feedback
        if (data.current_score !== undefined) {
            this.addChatMessage('system', `Score for previous question: ${data.current_score}/10`);
        }
        
        // Display next question
        setTimeout(() => {
            this.displayQuestion(
                data.next_question,
                data.question_number,
                data.time_allocated
            );
        }, 1000);
    }

    completeInterview(data) {
        // Update progress to 100%
        this.updateProgress(6, data.total_score);
        
        // Add completion messages
        this.addChatMessage('system', `Interview completed! Your total score: ${data.total_score}/60`);
        
        if (data.summary) {
            this.addChatMessage('system', `Summary: ${data.summary}`);
        }
        
        // Hide progress card after delay
        setTimeout(() => {
            document.getElementById('progressCard')?.classList.add('d-none');
        }, 3000);
    }

    updateProgress(questionNumber, currentScore) {
        const progressBar = document.getElementById('interviewProgress');
        const currentScoreEl = document.getElementById('currentScore');
        
        const progressPercent = (questionNumber / 6) * 100;
        
        if (progressBar) {
            progressBar.style.width = `${progressPercent}%`;
            progressBar.setAttribute('aria-valuenow', progressPercent);
        }
        
        if (currentScoreEl) {
            currentScoreEl.textContent = currentScore.toFixed(1);
        }
        
        // Update difficulty display
        const difficultyEl = document.getElementById('currentDifficulty');
        if (difficultyEl) {
            let difficulty = 'Easy';
            if (questionNumber > 4) difficulty = 'Hard';
            else if (questionNumber > 2) difficulty = 'Medium';
            difficultyEl.textContent = difficulty;
        }
    }

    showProgress() {
        document.getElementById('progressCard')?.classList.remove('d-none');
    }

    addChatMessage(type, content, metadata = {}) {
        const chatMessages = document.getElementById('chatMessages');
        if (!chatMessages) return;

        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${type}`;
        
        let metaHtml = '';
        if (metadata.question_number) {
            metaHtml += `<div class="message-meta">Question ${metadata.question_number}`;
            if (metadata.time_allocated) {
                metaHtml += ` • ${metadata.time_allocated}s allowed`;
            }
            metaHtml += '</div>';
        }
        if (metadata.time_taken) {
            metaHtml += `<div class="message-meta">Answered in ${metadata.time_taken}s</div>`;
        }

        messageDiv.innerHTML = `
            <div class="message-content">${this.escapeHtml(content)}</div>
            ${metaHtml}
        `;

        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    async loadDashboardData() {
        try {
            // This would typically fetch from an API endpoint that returns all candidates
            // For now, we'll show a placeholder
            const candidatesList = document.getElementById('candidatesList');
            if (!candidatesList) return;

            this.showLoading('Loading candidates...');
            
            // Simulated API call - replace with actual endpoint
            // const response = await fetch('/api/candidates/');
            // const data = await response.json();
            
            // For demo purposes, showing placeholder
            candidatesList.innerHTML = `
                <div class="col-12 text-center py-5">
                    <i class="fas fa-users fa-3x text-muted mb-3"></i>
                    <h5>No candidates yet</h5>
                    <p class="text-muted">Candidates will appear here after completing interviews.</p>
                </div>
            `;
            
        } catch (error) {
            console.error('Dashboard load error:', error);
            this.showError('Failed to load dashboard data');
        } finally {
            this.hideLoading();
        }
    }

    initWebSocket() {
        try {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws/interview/`;
            
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = () => {
                console.log('WebSocket connected');
                this.sendWebSocketMessage({
                    type: 'ping'
                });
            };
            
            this.websocket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleWebSocketMessage(data);
                } catch (error) {
                    console.error('WebSocket message error:', error);
                }
            };
            
            this.websocket.onclose = () => {
                console.log('WebSocket disconnected');
                // Attempt to reconnect after 5 seconds
                setTimeout(() => this.initWebSocket(), 5000);
            };
            
            this.websocket.onerror = (error) => {
                console.error('WebSocket error:', error);
            };
        } catch (error) {
            console.error('WebSocket initialization error:', error);
        }
    }

    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'interview_update':
                // Handle real-time interview updates
                console.log('Interview update:', data);
                break;
            case 'pong':
                // Keep-alive response
                break;
            default:
                console.log('Unknown WebSocket message:', data);
        }
    }

    sendWebSocketMessage(message) {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this.websocket.send(JSON.stringify(message));
        }
    }

    showLoading(message = 'Loading...') {
        // Implementation would show loading spinner with message
        console.log('Loading:', message);
    }

    hideLoading() {
        // Implementation would hide loading spinner
        console.log('Loading complete');
    }

    showError(message) {
        // Implementation would show error toast/alert
        console.error('Error:', message);
        alert(message); // Temporary - replace with proper toast
    }
}

// Initialize application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.interviewApp = new InterviewApp();
});