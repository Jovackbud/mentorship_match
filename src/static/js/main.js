document.addEventListener('DOMContentLoaded', () => {
    // --- Common Elements & Helpers ---
    const mainNavLinks = document.getElementById('main-nav-links');
    const registerNavItem = document.getElementById('register-nav-item'); // NEW
    const loginNavItem = document.getElementById('login-nav-item');       // NEW
    const logoutNavItem = document.getElementById('logout-nav-item');     // NEW
    const logoutBtn = document.getElementById('logout-btn');

    // Forms
    const registerForm = document.getElementById('register-form');
    const loginForm = document.getElementById('login-form');
    const mentorSignupForm = document.getElementById('mentor-signup-form');
    const menteeSignupForm = document.getElementById('mentee-signup-form');

    // Response Messages for Forms
    const registerResponseMessage = document.getElementById('register-response-message');
    const loginResponseMessage = document.getElementById('login-response-message');
    const mentorResponseMessage = document.getElementById('mentor-response-message');
    const menteeResponseMessage = document.getElementById('mentee-response-message');

    // Mentee Signup Specifics (already existing)
    const recommendationsSection = document.getElementById('recommendations-section');
    const recommendationsMessage = document.getElementById('recommendations-message');
    const mentorRecommendationsDiv = document.getElementById('mentor-recommendations');
    const pickMentorModal = document.getElementById('pick-mentor-modal');
    const modalMentorName = document.getElementById('modal-mentor-name');
    const modalRequestMessage = document.getElementById('modal-request-message');
    const confirmPickMentorBtn = document.getElementById('confirm-pick-mentor');

    // Mentor Dashboard Specifics (already existing)
    const mentorDashboardProfileSummary = document.getElementById('mentor-profile-summary');
    const mentorDashboardRequestsSection = document.getElementById('mentorship-requests-section');
    const mentorRequestsList = document.getElementById('mentorship-requests-list');
    const requestsMessage = document.getElementById('requests-message');
    const rejectModal = document.getElementById('reject-modal');
    const rejectionReasonInput = document.getElementById('rejection-reason');
    const confirmRejectBtn = document.getElementById('confirm-reject-btn');

    // Mentee Dashboard Specifics (already existing)
    const menteeDashboardProfileSummary = document.getElementById('mentee-profile-summary');
    const menteeDashboardRequestsList = document.getElementById('mentee-mentorship-requests-list');
    const menteeRequestsMessage = document.getElementById('mentee-requests-message');
    
    let currentMenteeId = null;
    let selectedMentorId = null;
    let currentMentorDashboardId = null;
    let currentMenteeDashboardId = null;
    let currentRequestIdForAction = null;
    let currentUsername = null;
    let currentUserProfileId = null;

    // --- Authentication & Navigation Helpers ---

    function isAuthenticated() {
        const token = localStorage.getItem('access_token');
        console.log('isAuthenticated() check: token in localStorage is', token ? 'present' : 'absent');
        return token !== null;
    }

    function updateNavLinks() {
        console.log('updateNavLinks() called. Is authenticated:', isAuthenticated());
        if (isAuthenticated()) {
            if (registerNavItem) registerNavItem.style.display = 'none';
            if (loginNavItem) loginNavItem.style.display = 'none';
            if (logoutNavItem) logoutNavItem.style.display = 'list-item';
            
            // Placeholder for personalized dashboard links (e.g., if we link users to mentors/mentees)
        } else {
            if (registerNavItem) registerNavItem.style.display = 'list-item';
            if (loginNavItem) loginNavItem.style.display = 'list-item';
            if (logoutNavItem) logoutNavItem.style.display = 'none';
        }
    }

    async function logout() {
        localStorage.removeItem('access_token');
        currentUsername = null;
        currentUserProfileId = null;
        updateNavLinks();
        console.log('Logged out. Redirecting to login.');
        window.location.href = '/login';
    }
    if (logoutBtn) {
        logoutBtn.addEventListener('click', logout);
    }

    // --- Generic Message Handlers ---
    function showFormMessage(messageElement, message, type) {
        if (messageElement) {
            messageElement.innerHTML = message;
            messageElement.setAttribute('data-variant', type);
            messageElement.style.display = 'block';
        }
    }

    function hideFormMessage(messageElement) {
        if (messageElement) {
            messageElement.innerHTML = '';
            messageElement.removeAttribute('data-variant');
            messageElement.style.display = 'none';
        }
    }

    // --- Modal Toggle Helpers (Generic for Pico.css dialogs) ---
    function toggleDialog(dialogElement, event) {
        if (!dialogElement) return;
        if (event) event.preventDefault();
        if (dialogElement.hasAttribute('open')) {
            dialogElement.removeAttribute('open');
            document.body.style.overflow = '';
        } else {
            dialogElement.setAttribute('open', '');
            document.body.style.overflow = 'hidden';
        }
    }

    window.togglePickMentorModal = (event) => toggleDialog(pickMentorModal, event);
    window.toggleRejectModal = (event) => toggleDialog(rejectModal, event);

    // --- Centralized API Call Helper ---
    async function authorizedFetch(url, options = {}) {
        const token = localStorage.getItem('access_token');
        const headers = {
            ...options.headers,
            'Content-Type': 'application/json',
        };

        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        } else {
            // If a token is required but not present, redirect to login
            // Note: This only applies to APIs that are explicitly protected.
            // Public endpoints (like GET /mentors/{id}) do not use authorizedFetch
            // directly but might be called indirectly for populating associated info.
            if (!url.startsWith('/mentors/') && !url.startsWith('/mentees/')) { // Allow public profile fetches
                console.warn('authorizedFetch: No token found. Attempting to access protected resource.');
                logout(); // Redirect to login
                throw new Error('Unauthorized: No access token found.');
            }
        }

        const response = await fetch(url, { ...options, headers });

        if (response.status === 401) {
            console.warn('Unauthorized access: Token might be expired or invalid. Redirecting to login.');
            logout();
            throw new Error('Unauthorized: API responded with 401.'); // Prevent further processing
        }
        return response;
    }


    // --- Register Form Logic ---
    if (registerForm) {
        hideFormMessage(registerResponseMessage);
        registerForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            hideFormMessage(registerResponseMessage);

            const formData = new FormData(registerForm);
            const username = formData.get('username');
            const password = formData.get('password');
            const confirmPassword = formData.get('confirm_password');

            if (password !== confirmPassword) {
                showFormMessage(registerResponseMessage, 'Passwords do not match.', 'error');
                return;
            }

            try {
                const response = await fetch('/register', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ username, password }),
                });

                const result = await response.json();

                if (response.ok) {
                    showFormMessage(registerResponseMessage, `Registration successful for ${result.username}! Please <a href="/login">login</a>.`, 'success');
                    registerForm.reset();
                } else {
                    showFormMessage(registerResponseMessage, `Error: ${result.detail || 'Could not register.'}`, 'error');
                    console.error('API Error:', result);
                }
            } catch (error) {
                showFormMessage(registerResponseMessage, 'Network error or unable to connect to server.', 'error');
                console.error('Fetch error:', error);
            }
        });
    }

    // --- Login Form Logic ---
    if (loginForm) {
        hideFormMessage(loginResponseMessage);
        loginForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            hideFormMessage(loginResponseMessage);

            const formData = new FormData(loginForm);
            const username = formData.get('username');
            const password = formData.get('password');

            const formBody = new URLSearchParams();
            formBody.append('username', username);
            formBody.append('password', password);

            try {
                const response = await fetch('/token', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                    },
                    body: formBody.toString(),
                });

                const result = await response.json();

                if (response.ok) {
                    localStorage.setItem('access_token', result.access_token);
                    currentUsername = username;
                    updateNavLinks();
                    showFormMessage(loginResponseMessage, `Login successful! Welcome, ${username}. Redirecting...`, 'success');
                    window.location.href = '/';
                } else {
                    showFormMessage(loginResponseMessage, `Error: ${result.detail || 'Could not log in.'}`, 'error');
                    console.error('API Error:', result);
                }
            } catch (error) {
                showFormMessage(loginResponseMessage, 'Network error or unable to connect to server.', 'error');
                console.error('Fetch error:', error);
            }
        });
    }


    // --- Mentor Signup Form Logic (UPDATED to use authorizedFetch) ---
    if (mentorSignupForm) {
        hideFormMessage(mentorResponseMessage);

        mentorSignupForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            hideFormMessage(mentorResponseMessage);

            if (!isAuthenticated()) {
                showFormMessage(mentorResponseMessage, 'You must be logged in to register as a mentor. Please <a href="/login">Login</a> or <a href="/register">Register</a>.', 'error');
                return;
            }

            const formData = new FormData(mentorSignupForm);
            const data = {};

            data.bio = formData.get('bio');
            data.expertise = formData.get('expertise') || null;
            data.capacity = parseInt(formData.get('capacity'), 10);

            const hoursPerMonth = parseInt(formData.get('hours_per_month'), 10);
            data.availability = (!isNaN(hoursPerMonth) && hoursPerMonth >= 0) ? { hours_per_month: hoursPerMonth } : null;

            const preferences = {};
            const industries = formData.get('preferences_industries');
            if (industries) {
                preferences.industries = industries.split(',').map(item => item.trim()).filter(item => item !== '');
            } else {
                preferences.industries = null;
            }
            const languages = formData.get('preferences_languages');
            if (languages) {
                preferences.languages = languages.split(',').map(item => item.trim()).filter(item => item !== '');
            } else {
                preferences.languages = null;
            }
            data.preferences = (Object.keys(preferences).length > 0 && (preferences.industries || preferences.languages)) ? preferences : null;

            const demographicsJson = formData.get('demographics');
            if (demographicsJson && demographicsJson.trim() !== '') {
                try {
                    data.demographics = JSON.parse(demographicsJson);
                } catch (e) {
                    showFormMessage(mentorResponseMessage, 'Error: Demographics must be valid JSON.', 'error');
                    console.error('Demographics JSON parse error:', e);
                    return;
                }
            } else {
                data.demographics = null;
            }

            console.log('Sending mentor data:', data);

            try {
                const response = await authorizedFetch('/mentors/', {
                    method: 'POST',
                    body: JSON.stringify(data),
                });

                const result = await response.json();

                if (response.ok) {
                    showFormMessage(mentorResponseMessage, `Mentor registered successfully! Your ID is: ${result.id}. You can view your dashboard <a href="/dashboard/mentor/${result.id}" role="button" class="secondary">here</a>.`, 'success');
                    mentorSignupForm.reset();
                } else {
                    showFormMessage(mentorResponseMessage, `Error: ${result.detail || 'Could not register mentor.'}`, 'error');
                    console.error('API Error:', result);
                }
            } catch (error) {
                showFormMessage(mentorResponseMessage, 'Network error or unable to connect to server.', 'error');
                console.error('Fetch error:', error);
            }
        });
    }

    // --- Mentee Signup Form Logic (UPDATED to use authorizedFetch) ---
    if (menteeSignupForm) {
        hideFormMessage(menteeResponseMessage);

        menteeSignupForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            hideFormMessage(menteeResponseMessage);
            recommendationsSection.style.display = 'none';
            mentorRecommendationsDiv.innerHTML = '';

            if (!isAuthenticated()) {
                showFormMessage(menteeResponseMessage, 'You must be logged in to find a mentor. Please <a href="/login">Login</a> or <a href="/register">Register</a>.', 'error');
                return;
            }

            const formData = new FormData(menteeSignupForm);
            const data = {};

            data.bio = formData.get('bio');
            data.goals = formData.get('goals');
            data.mentorship_style = formData.get('mentorship_style') || null;

            const hoursPerMonth = parseInt(formData.get('hours_per_month'), 10);
            data.availability = (!isNaN(hoursPerMonth) && hoursPerMonth >= 0) ? { hours_per_month: hoursPerMonth } : null;

            const preferences = {};
            const industries = formData.get('preferences_industries');
            if (industries) {
                preferences.industries = industries.split(',').map(item => item.trim()).filter(item => item !== '');
            } else {
                preferences.industries = null;
            }
            const languages = formData.get('preferences_languages');
            if (languages) {
                preferences.languages = languages.split(',').map(item => item.trim()).filter(item => item !== '');
            } else {
                preferences.languages = null;
            }
            data.preferences = (Object.keys(preferences).length > 0 && (preferences.industries || preferences.languages)) ? preferences : null;

            console.log('Sending mentee data for matching:', data);

            try {
                const response = await authorizedFetch('/match/', {
                    method: 'POST',
                    body: JSON.stringify(data),
                });

                const result = await response.json();

                if (response.ok) {
                    currentMenteeId = result.mentee_id;
                    showFormMessage(menteeResponseMessage, `Mentee registered. Your ID is: ${currentMenteeId}. ${result.message} You can view your dashboard <a href="/dashboard/mentee/${currentMenteeId}" role="button" class="secondary">here</a>.`, 'success');
                    
                    if (result.recommendations && result.recommendations.length > 0) {
                        displayRecommendations(result.recommendations);
                    } else {
                        recommendationsMessage.textContent = result.message || "No suitable mentors found based on your criteria. Please try broadening your preferences.";
                        recommendationsSection.style.display = 'block';
                    }
                } else {
                    showFormMessage(menteeResponseMessage, `Error: ${result.detail || 'Could not find matches.'}`, 'error');
                    console.error('API Error:', result);
                }
            } catch (error) {
                showFormMessage(menteeResponseMessage, 'Network error or unable to connect to server.', 'error');
                console.error('Fetch error:', error);
            }
        });
    }

    // --- Function to Display Recommendations (for Mentee Signup) ---
    function displayRecommendations(recommendations) {
        mentorRecommendationsDiv.innerHTML = '';
        recommendationsMessage.textContent = "Here are your top mentor recommendations:";
        
        recommendations.forEach(mentor => {
            const card = document.createElement('article');
            card.innerHTML = `
                <h4>${mentor.mentor_bio_snippet}</h4>
                <p><strong>Expertise:</strong> ${mentor.mentor_details.expertise || 'N/A'}</p>
                <p><strong>Capacity:</strong> ${mentor.mentor_details.capacity_info || 'N/A'}</p>
                <p><strong>Match Score:</strong> ${mentor.re_rank_score ? mentor.re_rank_score.toFixed(2) : 'N/A'}</p>
                <h5>Why this match?</h5>
                <ul>
                    ${mentor.explanations.map(exp => `<li>${exp}</li>`).join('')}
                </ul>
                <footer>
                    <button class="pick-mentor-btn" data-mentor-id="${mentor.mentor_id}" data-mentor-bio="${mentor.mentor_bio_snippet}">Pick This Mentor</button>
                </footer>
            `;
            mentorRecommendationsDiv.appendChild(card);
        });
        recommendationsSection.style.display = 'block';

        document.querySelectorAll('.pick-mentor-btn').forEach(button => {
            button.addEventListener('click', (event) => {
                selectedMentorId = parseInt(event.currentTarget.dataset.mentorId, 10);
                modalMentorName.textContent = event.currentTarget.dataset.mentorBio;
                modalRequestMessage.value = '';
                togglePickMentorModal();
            });
        });
    }

    // --- Logic for Confirming Mentor Pick in Modal (UPDATED to use authorizedFetch) ---
    if (confirmPickMentorBtn) {
        confirmPickMentorBtn.addEventListener('click', async (event) => {
            if (!currentMenteeId || !selectedMentorId) {
                showFormMessage(menteeResponseMessage, 'Error: Mentee or mentor ID missing for request.', 'error');
                togglePickMentorModal();
                return;
            }

            const message = modalRequestMessage.value;
            const url = `/mentee/${currentMenteeId}/pick_mentor/${selectedMentorId}`;
            const queryParams = message ? `?request_message=${encodeURIComponent(message)}` : '';

            try {
                const response = await authorizedFetch(url + queryParams, {
                    method: 'POST',
                });

                const result = await response.json();

                if (response.ok) {
                    showFormMessage(menteeResponseMessage, `Mentorship request to Mentor ID ${selectedMentorId} sent successfully! Request ID: ${result.id}`, 'success');
                } else {
                    showFormMessage(menteeResponseMessage, `Error sending request: ${result.detail || 'Could not send mentorship request.'}`, 'error');
                    console.error('API Error:', result);
                }
            } catch (error) {
                showFormMessage(menteeResponseMessage, 'Network error or unable to connect to server for picking mentor.', 'error');
                console.error('Fetch error for picking mentor:', error);
            } finally {
                togglePickMentorModal();
            }
        });
    }

    // --- Mentor Dashboard Logic (UPDATED to use authorizedFetch) ---
    const mentorPathSegments = window.location.pathname.split('/');
    if (mentorPathSegments[1] === 'dashboard' && mentorPathSegments[2] === 'mentor' && mentorPathSegments[3]) {
        currentMentorDashboardId = parseInt(mentorPathSegments[3], 10);
        if (!isNaN(currentMentorDashboardId)) {
            fetchMentorDetails(currentMentorDashboardId);
            fetchMentorshipRequests(currentMentorDashboardId);
        } else {
            showFormMessage(requestsMessage, 'Invalid mentor ID in URL.', 'error');
        }
    }

    async function fetchMentorDetails(mentorId) {
        const profileSummaryDiv = document.getElementById('mentor-profile-summary');
        if (!profileSummaryDiv) return;

        try {
            // NOTE: This endpoint is public, so it does not use authorizedFetch
            const response = await fetch(`/mentors/${mentorId}`, { method: 'GET' });
            if (response.ok) {
                const mentor = await response.json();
                profileSummaryDiv.innerHTML = `
                    <h2>Your Profile</h2>
                    <p><strong>Mentor ID:</strong> ${mentor.id}</p>
                    <p><strong>Bio:</strong> ${mentor.bio}</p>
                    <p><strong>Expertise:</strong> ${mentor.expertise || 'Not specified'}</p>
                    <p><strong>Capacity:</strong> ${mentor.current_mentees} / ${mentor.capacity} active mentees</p>
                    <p><strong>Availability:</strong> ${mentor.availability?.hours_per_month || 'Not specified'} hours/month</p>
                    <p><strong>Preferences:</strong> Industries: ${(mentor.preferences?.industries || []).join(', ') || 'Any'}, Languages: ${(mentor.preferences?.languages || []).join(', ') || 'Any'}</p>
                    ${mentor.demographics ? `<p><strong>Demographics:</strong> ${JSON.stringify(mentor.demographics)}</p>` : ''}
                `;
            } else {
                profileSummaryDiv.innerHTML = `<p>Failed to load mentor profile details: ${response.statusText}. Please ensure you are logged in and authorized to view this profile.</p>`;
                console.error(`Failed to fetch mentor details for ID ${mentorId}:`, response.status, await response.text());
            }
        } catch (error) {
            profileSummaryDiv.innerHTML = `<p>Error loading mentor profile details.</p>`;
            console.error(`Network error fetching mentor details for ID ${mentorId}:`, error);
        }
    }


    async function fetchMentorshipRequests(mentorId) {
        hideFormMessage(requestsMessage);
        mentorRequestsList.innerHTML = '<p>Loading your requests...</p>';

        try {
            const response = await authorizedFetch(`/api/mentors/${mentorId}/requests`, { method: 'GET' });
            const requests = await response.json();

            if (response.ok) {
                if (requests.length === 0) {
                    mentorRequestsList.innerHTML = '<p>No mentorship requests found.</p>';
                } else {
                    renderMentorMentorshipRequests(requests);
                }
            } else {
                showFormMessage(requestsMessage, `Error fetching requests: ${requests.detail || 'Unknown error.'}`, 'error');
                mentorRequestsList.innerHTML = '<p>Failed to load requests.</p>';
                console.error('API Error fetching mentor requests:', requests);
            }
        } catch (error) {
            showFormMessage(requestsMessage, 'Network error or unable to connect to server.', 'error');
            mentorRequestsList.innerHTML = '<p>Failed to load requests due to network error.</p>';
            console.error('Fetch error fetching mentor requests:', error);
        }
    }

    function renderMentorMentorshipRequests(requests) {
        mentorRequestsList.innerHTML = '';

        let pendingRequests = requests.filter(r => r.status === 'PENDING');
        let activeRequests = requests.filter(r => r.status === 'ACCEPTED');
        let historicalRequests = requests.filter(r => ['REJECTED', 'CANCELLED', 'COMPLETED'].includes(r.status));

        const sortByRequestDateDesc = (a, b) => new Date(b.request_date).getTime() - new Date(a.request_date).getTime();
        pendingRequests.sort(sortByRequestDateDesc);
        activeRequests.sort(sortByRequestDateDesc);
        historicalRequests.sort(sortByRequestDateDesc);

        function createRequestCategorySection(title, requestsArray, type) {
            if (requestsArray.length === 0) return null;

            const categorySection = document.createElement('section');
            categorySection.className = `request-category ${type}-requests`;
            
            const header = document.createElement('h3');
            header.textContent = title;
            categorySection.appendChild(header);

            const cardsContainer = document.createElement('div');
            cardsContainer.className = 'cards-container';
            requestsArray.forEach(request => {
                cardsContainer.appendChild(createMentorRequestCard(request, type));
            });
            categorySection.appendChild(cardsContainer);
            return categorySection;
        }

        const pendingSection = createRequestCategorySection('Pending Requests', pendingRequests, 'pending');
        if (pendingSection) mentorRequestsList.appendChild(pendingSection);

        const activeSection = createRequestCategorySection('Active Mentorships', activeRequests, 'active');
        if (activeSection) mentorRequestsList.appendChild(activeSection);

        const historicalSection = createRequestCategorySection('Historical Requests', historicalRequests, 'historical');
        if (historicalSection) mentorRequestsList.appendChild(historicalSection);

        if (pendingRequests.length === 0 && activeRequests.length === 0 && historicalRequests.length === 0) {
            mentorRequestsList.innerHTML = '<p>No mentorship requests found.</p>';
        }

        attachMentorRequestButtonListeners();
    }

    function createMentorRequestCard(request, type) {
        const card = document.createElement('article');
        card.setAttribute('data-request-status', request.status);
        const statusClass = request.status.toLowerCase();

        let cardContent = `
            <h5>Request ID: ${request.id}</h5>
            <p><strong>Mentee ID:</strong> ${request.mentee_id}</p>
            <p><strong>Status:</strong> <mark class="${statusClass}">${request.status}</mark></p>
            <p><strong>Requested:</strong> ${new Date(request.request_date).toLocaleDateString()}</p>
            ${request.request_message ? `<p><strong>Message:</strong> <em>${request.request_message}</em></p>` : ''}
        `;

        let footerButtons = '';
        if (request.status === 'PENDING') {
            footerButtons = `
                <button class="request-action-btn" data-action="accept" data-request-id="${request.id}" data-mentor-id="${currentMentorDashboardId}">Accept</button>
                <button class="request-action-btn secondary" data-action="reject" data-request-id="${request.id}" data-mentor-id="${currentMentorDashboardId}">Reject</button>
            `;
        } else if (request.status === 'ACCEPTED') {
            footerButtons = `
                <button class="request-action-btn" data-action="complete" data-request-id="${request.id}" data-mentor-id="${currentMentorDashboardId}">Complete Mentorship</button>
                <button class="request-action-btn secondary" data-action="reject" data-request-id="${request.id}" data-mentor-id="${currentMentorDashboardId}">End Mentorship (Reject)</button>
            `;
        }

        card.innerHTML = `
            ${cardContent}
            <footer>${footerButtons}</footer>
        `;
        return card;
    }

    function attachMentorRequestButtonListeners() {
        document.querySelectorAll('.request-action-btn').forEach(button => {
            button.addEventListener('click', async (event) => {
                const action = event.currentTarget.dataset.action;
                const requestId = parseInt(event.currentTarget.dataset.requestId, 10);
                const mentorId = parseInt(event.currentTarget.dataset.mentorId, 10);

                if (action === 'reject') {
                    currentRequestIdForAction = requestId;
                    toggleRejectModal();
                } else {
                    await performMentorAction(mentorId, requestId, action);
                }
            });
        });
    }

    async function performMentorAction(mentorId, requestId, action, rejectionReason = null) {
        let endpoint = '';
        let method = 'PUT';
        let queryParams = '';

        if (action === 'accept') {
            endpoint = `/mentor/${mentorId}/request/${requestId}/accept`;
        } else if (action === 'reject') {
            endpoint = `/mentor/${mentorId}/request/${requestId}/reject`;
            if (rejectionReason) {
                queryParams = `?rejection_reason=${encodeURIComponent(rejectionReason)}`;
            }
        } else if (action === 'complete') {
            endpoint = `/mentor/${mentorId}/request/${requestId}/complete`;
        } else {
            showFormMessage(requestsMessage, `Unknown action: ${action}`, 'error');
            return;
        }

        try {
            const response = await authorizedFetch(endpoint + queryParams, {
                method: method,
            });
            const result = await response.json();

            if (response.ok) {
                showFormMessage(requestsMessage, `Request ${requestId} ${action.toUpperCase()}ED successfully!`, 'success');
                fetchMentorshipRequests(mentorId);
            } else {
                showFormMessage(requestsMessage, `Error performing ${action} for request ${requestId}: ${result.detail || 'Unknown error.'}`, 'error');
                console.error(`API Error for ${action} request ${requestId}:`, result);
            }
        } catch (error) {
            showFormMessage(requestsMessage, `Network error during ${action} action for request ${requestId}.`, 'error');
            console.error(`Fetch error for ${action} request ${requestId}:`, error);
        }
    }

    if (confirmRejectBtn) {
        confirmRejectBtn.addEventListener('click', async (event) => {
            const rejectionReason = rejectionReasonInput.value;
            await performMentorAction(currentMentorDashboardId, currentRequestIdForAction, 'reject', rejectionReason);
            toggleRejectModal();
            rejectionReasonInput.value = '';
        });
    }


    // --- Mentee Dashboard Logic (UPDATED to use authorizedFetch) ---
    const menteePathSegments = window.location.pathname.split('/');
    if (menteePathSegments[1] === 'dashboard' && menteePathSegments[2] === 'mentee' && menteePathSegments[3]) {
        currentMenteeDashboardId = parseInt(menteePathSegments[3], 10);
        if (!isNaN(currentMenteeDashboardId)) {
            fetchMenteeDetails(currentMenteeDashboardId);
            fetchMenteeMentorshipRequests(currentMenteeDashboardId);
        } else {
            showFormMessage(menteeRequestsMessage, 'Invalid mentee ID in URL.', 'error');
        }
    }

    async function fetchMenteeDetails(menteeId) {
        const profileSummaryDiv = document.getElementById('mentee-profile-summary');
        if (!profileSummaryDiv) return;

        try {
            // NOTE: This endpoint is public, so it does not use authorizedFetch
            const response = await fetch(`/mentees/${menteeId}`, { method: 'GET' });
            if (response.ok) {
                const mentee = await response.json();
                profileSummaryDiv.innerHTML = `
                    <h2>Your Profile</h2>
                    <p><strong>Mentee ID:</strong> ${mentee.id}</p>
                    <p><strong>Bio:</strong> ${mentee.bio}</p>
                    <p><strong>Goals:</strong> ${mentee.goals || 'Not specified'}</p>
                    <p><strong>Mentorship Style:</strong> ${mentee.mentorship_style || 'Not specified'}</p>
                    <p><strong>Availability:</strong> ${mentee.availability?.hours_per_month || 'Not specified'} hours/month</p>
                    <p><strong>Preferences:</strong> Industries: ${(mentee.preferences?.industries || []).join(', ') || 'Any'}, Languages: ${(mentee.preferences?.languages || []).join(', ') || 'Any'}</p>
                `;
            } else {
                profileSummaryDiv.innerHTML = `<p>Failed to load mentee profile details: ${response.statusText}. Please ensure you are logged in and authorized to view this profile.</p>`;
                console.error(`Failed to fetch mentee details for ID ${menteeId}:`, response.status, await response.text());
            }
        } catch (error) {
            profileSummaryDiv.innerHTML = `<p>Error loading mentee profile details.</p>`;
            console.error(`Network error fetching mentee details for ID ${menteeId}:`, error);
        }
    }


    async function fetchMenteeMentorshipRequests(menteeId) {
        hideFormMessage(menteeRequestsMessage);
        menteeDashboardRequestsList.innerHTML = '<p>Loading your requests...</p>';

        try {
            const response = await authorizedFetch(`/api/mentees/${menteeId}/requests`, { method: 'GET' });
            const requests = await response.json();

            if (response.ok) {
                if (requests.length === 0) {
                    menteeDashboardRequestsList.innerHTML = '<p>No mentorship requests found.</p>';
                } else {
                    renderMenteeMentorshipRequests(requests);
                }
            } else {
                showFormMessage(menteeRequestsMessage, `Error fetching requests: ${requests.detail || 'Unknown error.'}`, 'error');
                menteeDashboardRequestsList.innerHTML = '<p>Failed to load requests.</p>';
                console.error('API Error fetching mentee requests:', requests);
            }
        } catch (error) {
            showFormMessage(menteeRequestsMessage, 'Network error or unable to connect to server.', 'error');
            menteeDashboardRequestsList.innerHTML = '<p>Failed to load requests due to network error.</p>';
            console.error('Fetch error fetching mentee requests:', error);
        }
    }

    function renderMenteeMentorshipRequests(requests) {
        menteeDashboardRequestsList.innerHTML = '';

        let pendingRequests = requests.filter(r => r.status === 'PENDING');
        let activeRequests = requests.filter(r => r.status === 'ACCEPTED');
        let historicalRequests = requests.filter(r => ['REJECTED', 'CANCELLED', 'COMPLETED'].includes(r.status));

        const sortByRequestDateDesc = (a, b) => new Date(b.request_date).getTime() - new Date(a.request_date).getTime();
        pendingRequests.sort(sortByRequestDateDesc);
        activeRequests.sort(sortByRequestDateDesc);
        historicalRequests.sort(sortByRequestDateDesc);

        function createRequestCategorySection(title, requestsArray, type) {
            if (requestsArray.length === 0) return null;

            const categorySection = document.createElement('section');
            categorySection.className = `request-category ${type}-requests`;
            
            const header = document.createElement('h3');
            header.textContent = title;
            categorySection.appendChild(header);

            const cardsContainer = document.createElement('div');
            cardsContainer.className = 'cards-container';
            requestsArray.forEach(request => {
                cardsContainer.appendChild(createMenteeRequestCard(request, type));
            });
            categorySection.appendChild(cardsContainer);
            return categorySection;
        }

        const pendingSection = createRequestCategorySection('Pending Requests', pendingRequests, 'pending');
        if (pendingSection) menteeDashboardRequestsList.appendChild(pendingSection);

        const activeSection = createRequestCategorySection('Active Mentorships', activeRequests, 'active');
        if (activeSection) menteeDashboardRequestsList.appendChild(activeSection);

        const historicalSection = createRequestCategorySection('Historical Journeys', historicalRequests, 'historical');
        if (historicalSection) menteeDashboardRequestsList.appendChild(historicalSection);

        if (pendingRequests.length === 0 && activeRequests.length === 0 && historicalRequests.length === 0) {
            menteeDashboardRequestsList.innerHTML = '<p>No mentorship requests found.</p>';
        }

        attachMenteeRequestButtonListeners();
    }

    function createMenteeRequestCard(request, type) {
        const card = document.createElement('article');
        card.setAttribute('data-request-status', request.status);
        const statusClass = request.status.toLowerCase();

        let cardContent = `
            <h5>Request ID: ${request.id}</h5>
            <p><strong>Mentor ID:</strong> ${request.mentor_id}</p>
            <p><strong>Status:</strong> <mark class="${statusClass}">${request.status}</mark></p>
            <p><strong>Requested:</strong> ${new Date(request.request_date).toLocaleDateString()}</p>
            ${request.request_message ? `<p><strong>Your Message:</strong> <em>${request.request_message}</em></p>` : ''}
        `;

        let footerButtons = '';
        if (request.status === 'PENDING') {
            footerButtons = `
                <button class="mentee-request-action-btn secondary" data-action="cancel" data-request-id="${request.id}" data-mentee-id="${currentMenteeDashboardId}">Cancel Request</button>
            `;
        } else if (request.status === 'ACCEPTED') {
            footerButtons = `
                <button class="mentee-request-action-btn" data-action="conclude" data-request-id="${request.id}" data-mentee-id="${currentMenteeDashboardId}">Conclude Mentorship</button>
            `;
        }

        card.innerHTML = `
            ${cardContent}
            <footer>${footerButtons}</footer>
        `;
        return card;
    }

    function attachMenteeRequestButtonListeners() {
        document.querySelectorAll('.mentee-request-action-btn').forEach(button => {
            button.addEventListener('click', async (event) => {
                const action = event.currentTarget.dataset.action;
                const requestId = parseInt(event.currentTarget.dataset.requestId, 10);
                const menteeId = parseInt(event.currentTarget.dataset.menteeId, 10);

                await performMenteeAction(menteeId, requestId, action);
            });
        });
    }

    async function performMenteeAction(menteeId, requestId, action) {
        let endpoint = '';
        let method = 'PUT';

        if (action === 'cancel') {
            endpoint = `/mentee/${menteeId}/request/${requestId}/cancel`;
        } else if (action === 'conclude') {
            endpoint = `/mentee/${menteeId}/request/${requestId}/conclude`;
        } else {
            showFormMessage(menteeRequestsMessage, `Unknown mentee action: ${action}`, 'error');
            return;
        }

        try {
            const response = await authorizedFetch(endpoint, {
                method: method,
            });
            const result = await response.json();

            if (response.ok) {
                showFormMessage(menteeRequestsMessage, `Request ${requestId} ${action.toUpperCase()}ED successfully!`, 'success');
                fetchMenteeMentorshipRequests(menteeId);
            } else {
                showFormMessage(menteeRequestsMessage, `Error performing ${action} for request ${requestId}: ${result.detail || 'Unknown error.'}`, 'error');
                console.error(`API Error for ${action} request ${requestId}:`, result);
            }
        } catch (error) {
            showFormMessage(menteeRequestsMessage, 'Network error or unable to connect to server.', 'error');
            console.error(`Fetch error for ${action} request ${requestId}:`, error);
        }
    }

    // --- Initial setup on page load ---
    updateNavLinks(); // Update navigation based on current login status
});