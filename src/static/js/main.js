document.addEventListener('DOMContentLoaded', () => {
    // --- Common Elements & Helpers ---
    const mainNavLinks = document.getElementById('main-nav-links');
    const registerNavItem = document.getElementById('register-nav-item');
    const loginNavItem = document.getElementById('login-nav-item');
    const logoutNavItem = document.getElementById('logout-nav-item');
    const logoutBtn = document.getElementById('logout-btn');

    // Forms
    const registerForm = document.getElementById('register-form');
    const loginForm = document.getElementById('login-form');
    const mentorSignupForm = document.getElementById('mentor-signup-form');
    const menteeSignupForm = document.getElementById('mentee-signup-form');
    const feedbackForm = document.getElementById('feedback-form'); 

    // Response Messages for Forms
    const registerResponseMessage = document.getElementById('register-response-message');
    const loginResponseMessage = document.getElementById('login-response-message');
    const mentorResponseMessage = document.getElementById('mentor-response-message');
    const menteeResponseMessage = document.getElementById('mentee-response-message');
    const feedbackResponseMessage = document.getElementById('feedback-response-message');
    // Client-side validation feedback elements
    const passwordMatchFeedback = document.getElementById('password-match-feedback');
    const ratingFeedback = document.getElementById('rating-feedback');

    // Mentee Signup Specifics
    const recommendationsSection = document.getElementById('recommendations-section');
    const recommendationsMessage = document.getElementById('recommendations-message');
    const mentorRecommendationsDiv = document.getElementById('mentor-recommendations');
    const pickMentorModal = document.getElementById('pick-mentor-modal');
    const modalMentorName = document.getElementById('modal-mentor-name'); // Will now display mentor's actual name
    const modalRequestMessage = document.getElementById('modal-request-message');
    const confirmPickMentorBtn = document.getElementById('confirm-pick-mentor');

    // Mentor Dashboard Specifics
    const mentorDashboardName = document.getElementById('mentor-dashboard-name'); // For dashboard title
    const mentorDashboardProfileSummary = document.getElementById('mentor-profile-summary');
    const mentorDashboardRequestsSection = document.getElementById('mentorship-requests-section');
    const mentorRequestsList = document.getElementById('mentorship-requests-list');
    const requestsMessage = document.getElementById('requests-message');
    const rejectModal = document.getElementById('reject-modal');
    const rejectionReasonInput = document.getElementById('rejection-reason');
    const confirmRejectBtn = document.getElementById('confirm-reject-btn');
    const mentorProfileMessage = document.getElementById('mentor-profile-message'); // For profile fetch errors

    // Mentee Dashboard Specifics
    const menteeDashboardName = document.getElementById('mentee-dashboard-name'); // For dashboard title
    const menteeDashboardProfileSummary = document.getElementById('mentee-profile-summary');
    const menteeDashboardRequestsList = document.getElementById('mentee-mentorship-requests-list');
    const menteeRequestsMessage = document.getElementById('mentee-requests-message');
    const menteeProfileMessage = document.getElementById('mentee-profile-message'); // For profile fetch errors
    
    // --- Global State Variables ---
    let currentMenteeId = null;
    let selectedMentorId = null;
    let currentMentorDashboardId = null;
    let currentMenteeDashboardId = null;
    let currentRequestIdForAction = null;
    let currentUser = null; // Will store the user object from /users/me if authenticated

    // --- Authentication & Navigation Helpers ---

    // isAuthenticated now relies on the `currentUser` object being set by `checkSessionAndFetchUser`
    function isAuthenticated() {
        return currentUser !== null;
    }

    // Function to update navigation links based on authentication status
    function updateNavLinks() {
        if (isAuthenticated()) {
            if (registerNavItem) registerNavItem.hidden = true;
            if (loginNavItem) loginNavItem.hidden = true;
            if (logoutNavItem) logoutNavItem.hidden = false;
        } else {
            if (registerNavItem) registerNavItem.hidden = false;
            if (loginNavItem) loginNavItem.hidden = false;
            if (logoutNavItem) logoutNavItem.hidden = true;
        }
    }

    // New: Check session on page load by calling /users/me
    async function checkSessionAndFetchUser() {
        try {
            // Frontend will implicitly send HttpOnly cookies.
            // Backend /users/me will check the cookie and return user info if valid, or 401.
            const response = await fetch('/users/me/', { 
                method: 'GET', 
                headers: {'Content-Type': 'application/json'},
                credentials: 'include' // Important for sending cookies
            });
            if (response.ok) {
                currentUser = await response.json();
                console.log('Session active. User:', currentUser.username);
                updateNavLinks();
            } else {
                currentUser = null;
                console.log('No active session or token expired.');
                updateNavLinks();
                // If on a protected dashboard page without a session, redirect
                const path = window.location.pathname;
                if (path.startsWith('/dashboard/') || path.startsWith('/feedback')) { // Also protect feedback form
                    console.log('Redirecting from protected page due to no active session.');
                    window.location.href = '/login';
                }
            }
        } catch (error) {
            currentUser = null;
            console.error('Error checking session:', error);
            updateNavLinks();
        }
    }

    // Logout function: sends request to backend to clear HttpOnly cookie
    async function logout() {
        try {
            // Assume a /logout endpoint on the backend that clears the HttpOnly cookie
            const response = await fetch('/logout', { 
                method: 'POST',
                credentials: 'include' // Important for sending cookies to clear
            }); 
            if (response.ok) {
                currentUser = null; // Clear client-side user state
                console.log('Logged out successfully from backend and client.');
                updateNavLinks();
                window.location.href = '/login'; // Redirect to login page
            } else {
                console.error('Logout failed on backend:', await response.text());
                // Even if backend fails, clear client-side state for UX
                currentUser = null;
                updateNavLinks();
                window.location.href = '/login';
            }
        } catch (error) {
            console.error('Network error during logout:', error);
            // Fallback: clear client-side state for UX even on network error
            currentUser = null;
            updateNavLinks();
            window.location.href = '/login';
        }
    }
    if (logoutBtn) {
        logoutBtn.addEventListener('click', logout);
    }

    // --- Generic Message Handlers ---
    function showFormMessage(messageElement, message, type) {
        if (messageElement) {
            messageElement.innerHTML = message;
            messageElement.setAttribute('data-variant', type);
            messageElement.hidden = false; // Show the message
        }
    }

    function hideFormMessage(messageElement) {
        if (messageElement) {
            messageElement.innerHTML = '';
            messageElement.removeAttribute('data-variant');
            messageElement.hidden = true; // Hide the message
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

    // --- Centralized API Call Helper (Modified for HttpOnly Cookies) ---
    async function authorizedFetch(url, options = {}) {
        const headers = { ...options.headers };

        // Determine Content-Type: Default to application/json if body exists and no Content-Type explicitly set
        if (options.body && !headers['Content-Type']) {
            headers['Content-Type'] = 'application/json';
        } else if (!options.body && ['GET', 'HEAD'].includes(options.method?.toUpperCase())) {
            // If no body and method is GET/HEAD, ensure Content-Type is not set
            delete headers['Content-Type'];
        }
        
        // No manual Authorization header for HttpOnly cookies; browser handles sending 'credentials: include'.
        // The server's 401 response is our signal for session expiry.

        const response = await fetch(url, { ...options, headers, credentials: 'include' }); // 'include' to send HttpOnly cookies

        if (response.status === 401) {
            console.warn('Unauthorized access: Session expired or invalid. Redirecting to login.');
            logout(); // Perform full logout sequence to clear client state and redirect
            throw new Error('Unauthorized: API responded with 401.'); // Prevent further processing
        }
        return response;
    }


    // --- Register Form Logic ---
    if (registerForm) {
        hideFormMessage(registerResponseMessage);
        if (passwordMatchFeedback) hideFormMessage(passwordMatchFeedback); // Clear password match feedback initially

        registerForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            hideFormMessage(registerResponseMessage);
            if (passwordMatchFeedback) hideFormMessage(passwordMatchFeedback);

            const formData = new FormData(registerForm);
            const username = formData.get('username');
            const password = formData.get('password');
            const confirmPassword = formData.get('confirm_password');

            if (password !== confirmPassword) {
                showFormMessage(passwordMatchFeedback, 'Passwords do not match.', 'error');
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

    // --- Login Form Logic (Modified for HttpOnly Cookies) ---
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
                // Backend /token endpoint should now set an HttpOnly cookie
                // Frontend doesn't receive the token directly
                const response = await fetch('/token', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                    },
                    body: formBody.toString(),
                    credentials: 'include' // Important to send/receive cookies
                });

                // We don't get the token back in JS, just a success/failure
                if (response.ok) {
                    // Optimistically set user state, but /users/me will be the source of truth
                    // A full page reload (window.location.href = '/') will trigger checkSessionAndFetchUser
                    // which will then get the actual user data via /users/me.
                    currentUser = { username: username }; 
                    updateNavLinks();
                    showFormMessage(loginResponseMessage, `Login successful! Welcome, ${username}. Redirecting...`, 'success');
                    window.location.href = '/'; 
                } else {
                    const result = await response.json();
                    showFormMessage(loginResponseMessage, `Error: ${result.detail || 'Could not log in.'}`, 'error');
                    console.error('API Error:', result);
                }
            } catch (error) {
                showFormMessage(loginResponseMessage, 'Network error or unable to connect to server.', 'error');
                console.error('Fetch error:', error);
            }
        });
    }


    // --- Mentor Signup Form Logic (Uses authorizedFetch) ---
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

            data.name = formData.get('name'); // ADDED: Collect name
            data.bio = formData.get('bio');
            data.expertise = formData.get('expertise') || null;
            data.capacity = parseInt(formData.get('capacity'), 10);

            const hoursPerMonth = parseInt(formData.get('hours_per_month'), 10);
            data.availability = (!isNaN(hoursPerMonth) && hoursPerMonth >= 0) ? { hours_per_month: hoursPerMonth } : null;

            const preferences = {};
            const industries = formData.get('preferences_industries');
            if (industries && industries.trim() !== '') {
                preferences.industries = industries.split(',').map(item => item.trim()).filter(item => item !== '');
            } else {
                preferences.industries = null; // Backend expects null for optional
            }
            const languages = formData.get('preferences_languages');
            if (languages && languages.trim() !== '') {
                preferences.languages = languages.split(',').map(item => item.trim()).filter(item => item !== '');
            } else {
                preferences.languages = null; // Backend expects null for optional
            }
            data.preferences = (preferences.industries || preferences.languages) ? preferences : null;


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
                    showFormMessage(mentorResponseMessage, `Mentor ${result.name} registered successfully! Your ID is: ${result.id}. You can view your dashboard <a href="/dashboard/mentor/${result.id}" role="button" class="secondary">here</a>.`, 'success');
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

    // --- Mentee Signup Form Logic (Uses authorizedFetch) ---
    if (menteeSignupForm) {
        hideFormMessage(menteeResponseMessage);

        menteeSignupForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            hideFormMessage(menteeResponseMessage);
            if (recommendationsSection) recommendationsSection.hidden = true;
            if (mentorRecommendationsDiv) mentorRecommendationsDiv.innerHTML = '';


            if (!isAuthenticated()) {
                showFormMessage(menteeResponseMessage, 'You must be logged in to find a mentor. Please <a href="/login">Login</a> or <a href="/register">Register</a>.', 'error');
                return;
            }

            const formData = new FormData(menteeSignupForm);
            const data = {};

            data.name = formData.get('name'); // ADDED: Collect name
            data.bio = formData.get('bio');
            data.goals = formData.get('goals');
            data.mentorship_style = formData.get('mentorship_style') || null;

            const hoursPerMonth = parseInt(formData.get('hours_per_month'), 10);
            data.availability = (!isNaN(hoursPerMonth) && hoursPerMonth >= 0) ? { hours_per_month: hoursPerMonth } : null;

            const preferences = {};
            const industries = formData.get('preferences_industries');
            if (industries && industries.trim() !== '') {
                preferences.industries = industries.split(',').map(item => item.trim()).filter(item => item !== '');
            } else {
                preferences.industries = null; // Backend expects null for optional
            }
            const languages = formData.get('preferences_languages');
            if (languages && languages.trim() !== '') {
                preferences.languages = languages.split(',').map(item => item.trim()).filter(item => item !== '');
            } else {
                preferences.languages = null; // Backend expects null for optional
            }
            data.preferences = (preferences.industries || preferences.languages) ? preferences : null;

            console.log('Sending mentee data for matching:', data);

            try {
                const response = await authorizedFetch('/match/', {
                    method: 'POST',
                    body: JSON.stringify(data),
                });

                const result = await response.json();

                if (response.ok) {
                    currentMenteeId = result.mentee_id;
                    showFormMessage(menteeResponseMessage, `Mentee ${result.name} registered. Your ID is: ${currentMenteeId}. ${result.message} You can view your dashboard <a href="/dashboard/mentee/${currentMenteeId}" role="button" class="secondary">here</a>.`, 'success');
                    
                    if (result.recommendations && result.recommendations.length > 0) {
                        displayRecommendations(result.recommendations);
                    } else {
                        if (recommendationsMessage) recommendationsMessage.textContent = result.message || "No suitable mentors found based on your criteria. Please try broadening your preferences.";
                        if (recommendationsSection) recommendationsSection.hidden = false;
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
        if (mentorRecommendationsDiv) mentorRecommendationsDiv.innerHTML = '';
        if (recommendationsMessage) recommendationsMessage.textContent = "Here are your top mentor recommendations:";
        
        recommendations.forEach(mentor => {
            const card = document.createElement('article');
            // Improved bio snippet handling to avoid '...' for short bios in JS
            const rawBio = mentor.mentor_bio_snippet || '';
            const bioSnippet = rawBio.length > 100 ? rawBio.substring(0, 100) + '...' : rawBio;

            card.innerHTML = `
                <h4>${mentor.mentor_name || 'Unknown Mentor'}</h4> {# Display mentor's name #}
                <p>${bioSnippet}</p> {# Bio snippet is now separate #}
                <p><strong>Expertise:</strong> ${mentor.mentor_details.expertise || 'Not specified'}</p>
                <p><strong>Capacity:</strong> ${mentor.mentor_details.capacity_info || 'N/A'}</p>
                <p><strong>Match Score:</strong> ${mentor.re_rank_score ? mentor.re_rank_score.toFixed(2) : 'N/A'}</p>
                <h5>Why this match?</h5>
                <ul>
                    ${mentor.explanations.map(exp => `<li>${exp}</li>`).join('')}
                </ul>
                <footer>
                    <button type="button" class="pick-mentor-btn" data-mentor-id="${mentor.mentor_id}" data-mentor-name="${mentor.mentor_name || 'Unknown Mentor'}">Pick This Mentor</button> {# Pass mentor name to dataset #}
                </footer>
            `;
            if (mentorRecommendationsDiv) mentorRecommendationsDiv.appendChild(card);
        });
        if (recommendationsSection) recommendationsSection.hidden = false;

        document.querySelectorAll('.pick-mentor-btn').forEach(button => {
            button.addEventListener('click', (event) => {
                selectedMentorId = parseInt(event.currentTarget.dataset.mentorId, 10);
                // Use data-mentor-name for modal display
                if (modalMentorName) modalMentorName.textContent = event.currentTarget.dataset.mentorName;
                if (modalRequestMessage) modalRequestMessage.value = '';
                togglePickMentorModal();
            });
        });
    }

    // --- Logic for Confirming Mentor Pick in Modal (Uses authorizedFetch) ---
    if (confirmPickMentorBtn) {
        confirmPickMentorBtn.addEventListener('click', async (event) => {
            if (!currentMenteeId || !selectedMentorId) {
                showFormMessage(menteeResponseMessage, 'Error: Mentee or mentor ID missing for request.', 'error');
                togglePickMentorModal();
                return;
            }

            const message = modalRequestMessage ? modalRequestMessage.value : '';
            const url = `/mentee/${currentMenteeId}/pick_mentor/${selectedMentorId}`;
            // For HttpOnly cookies, query params are fine for simple strings.
            const queryParams = message ? `?request_message=${encodeURIComponent(message)}` : '';

            try {
                const response = await authorizedFetch(url + queryParams, {
                    method: 'POST',
                    // No body needed for query params with POST and queryParams
                });

                const result = await response.json();

                if (response.ok) {
                    showFormMessage(menteeResponseMessage, `Mentorship request to Mentor ID ${selectedMentorId} sent successfully! Request ID: ${result.id}`, 'success');
                    // Consider refreshing mentee dashboard requests here
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

    // --- Mentor Dashboard Logic (Uses authorizedFetch) ---
    const mentorPathSegments = window.location.pathname.split('/');
    if (mentorPathSegments[1] === 'dashboard' && mentorPathSegments[2] === 'mentor' && mentorPathSegments[3]) {
        currentMentorDashboardId = parseInt(mentorPathSegments[3], 10);
        if (!isNaN(currentMentorDashboardId)) {
            fetchMentorDetails(currentMentorDashboardId);
            fetchMentorshipRequests(currentMentorDashboardId);
        } else {
            showFormMessage(mentorProfileMessage, 'Invalid mentor ID in URL.', 'error');
        }
    }

    async function fetchMentorDetails(mentorId) {
        if (!mentorDashboardProfileSummary || !mentorProfileMessage || !mentorDashboardName) return;
        hideFormMessage(mentorProfileMessage);

        try {
            const response = await fetch(`/mentors/${mentorId}`, { method: 'GET' });
            if (response.ok) {
                const mentor = await response.json();
                if (mentorDashboardName) mentorDashboardName.textContent = mentor.name; // Display name in dashboard title
                mentorDashboardProfileSummary.innerHTML = `
                    <h2>Your Profile</h2>
                    <p><strong>Mentor ID:</strong> ${mentor.id}</p>
                    <p><strong>Name:</strong> ${mentor.name}</p> {# Display mentor's name #}
                    <p><strong>Bio:</strong> ${mentor.bio}</p>
                    <p><strong>Expertise:</strong> ${mentor.expertise || 'Not specified'}</p>
                    <p><strong>Capacity:</strong> ${mentor.current_mentees} / ${mentor.capacity} active mentees</p>
                    <p><strong>Availability:</strong> ${mentor.availability?.hours_per_month || 'Not specified'} hours/month</p>
                    <p><strong>Preferences:</strong> Industries: ${(mentor.preferences?.industries || []).join(', ') || 'Any'}, Languages: ${(mentor.preferences?.languages || []).join(', ') || 'Any'}</p>
                    ${mentor.demographics ? `<p><strong>Demographics:</strong> ${JSON.stringify(mentor.demographics)}</p>` : ''}
                `;
                mentorDashboardProfileSummary.appendChild(mentorProfileMessage);
            } else {
                showFormMessage(mentorProfileMessage, `Failed to load mentor profile details: ${response.statusText}. Please ensure the ID is correct.`, 'error');
                console.error(`Failed to fetch mentor details for ID ${mentorId}:`, response.status, await response.text());
            }
        } catch (error) {
            showFormMessage(mentorProfileMessage, `Error loading mentor profile details. Network error: ${error.message}`, 'error');
            console.error(`Network error fetching mentor details for ID ${mentorId}:`, error);
        }
    }


    async function fetchMentorshipRequests(mentorId) {
        if (!mentorRequestsList || !requestsMessage) return;
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
            showFormMessage(requestsMessage, `Network error or unable to connect to server: ${error.message}`, 'error');
            mentorRequestsList.innerHTML = '<p>Failed to load requests due to network error.</p>';
            console.error('Fetch error fetching mentor requests:', error);
        }
    }

    function renderMentorMentorshipRequests(requests) {
        if (mentorRequestsList) mentorRequestsList.innerHTML = '';

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
        if (pendingSection && mentorRequestsList) mentorRequestsList.appendChild(pendingSection);

        const activeSection = createRequestCategorySection('Active Mentorships', activeRequests, 'active');
        if (activeSection && mentorRequestsList) mentorRequestsList.appendChild(activeSection);

        const historicalSection = createRequestCategorySection('Historical Requests', historicalRequests, 'historical');
        if (historicalSection && mentorRequestsList) mentorRequestsList.appendChild(historicalSection);

        if (pendingRequests.length === 0 && activeRequests.length === 0 && historicalRequests.length === 0) {
            if (mentorRequestsList) mentorRequestsList.innerHTML = '<p>No mentorship requests found.</p>';
        }

        attachMentorRequestButtonListeners();
    }

    function createMentorRequestCard(request, type) {
        const card = document.createElement('article');
        card.setAttribute('data-request-status', request.status);
        const statusClass = request.status.toLowerCase();

        let cardContent = `
            <h5>Request ID: ${request.id}</h5>
            <p><strong>Mentee:</strong> ${request.mentee_name || request.mentee_id}</p> {# Display mentee's name or ID fallback #}
            <p><strong>Status:</strong> <mark class="${statusClass}">${request.status}</mark></p>
            <p><strong>Requested:</strong> ${new Date(request.request_date).toLocaleDateString()}</p>
            ${request.request_message ? `<p><strong>Message:</strong> <em>${request.request_message}</em></p>` : ''}
        `;

        let footerButtons = '';
        if (request.status === 'PENDING') {
            footerButtons = `
                <button type="button" class="request-action-btn" data-action="accept" data-request-id="${request.id}" data-mentor-id="${currentMentorDashboardId}">Accept</button>
                <button type="button" class="request-action-btn secondary" data-action="reject" data-request-id="${request.id}" data-mentor-id="${currentMentorDashboardId}">Reject</button>
            `;
        } else if (request.status === 'ACCEPTED') {
            footerButtons = `
                <button type="button" class="request-action-btn" data-action="complete" data-request-id="${request.id}" data-mentor-id="${currentMentorDashboardId}">Complete Mentorship</button>
                <button type="button" class="request-action-btn secondary" data-action="reject" data-request-id="${request.id}" data-mentor-id="${currentMentorDashboardId}">End Mentorship (Reject)</button>
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
                fetchMentorshipRequests(mentorId); // Refresh requests list
                fetchMentorDetails(mentorId); // Refresh mentor details (capacity)
            } else {
                showFormMessage(requestsMessage, `Error performing ${action} for request ${requestId}: ${result.detail || 'Unknown error.'}`, 'error');
                console.error(`API Error for ${action} request ${requestId}:`, result);
            }
        } catch (error) {
            showFormMessage(requestsMessage, `Network error during ${action} action for request ${requestId}. Error: ${error.message}`, 'error');
            console.error(`Fetch error for ${action} request ${requestId}:`, error);
        }
    }

    if (confirmRejectBtn) {
        confirmRejectBtn.addEventListener('click', async (event) => {
            const rejectionReason = rejectionReasonInput ? rejectionReasonInput.value : '';
            await performMentorAction(currentMentorDashboardId, currentRequestIdForAction, 'reject', rejectionReason);
            toggleRejectModal();
            if (rejectionReasonInput) rejectionReasonInput.value = '';
        });
    }


    // --- Mentee Dashboard Logic (Uses authorizedFetch) ---
    const menteePathSegments = window.location.pathname.split('/');
    if (menteePathSegments[1] === 'dashboard' && menteePathSegments[2] === 'mentee' && menteePathSegments[3]) {
        currentMenteeDashboardId = parseInt(menteePathSegments[3], 10);
        if (!isNaN(currentMenteeDashboardId)) {
            fetchMenteeDetails(currentMenteeDashboardId);
            fetchMenteeMentorshipRequests(currentMenteeDashboardId);
        } else {
            showFormMessage(menteeProfileMessage, 'Invalid mentee ID in URL.', 'error');
        }
    }

    async function fetchMenteeDetails(menteeId) {
        if (!menteeDashboardProfileSummary || !menteeProfileMessage || !menteeDashboardName) return;
        hideFormMessage(menteeProfileMessage);

        try {
            const response = await fetch(`/mentees/${menteeId}`, { method: 'GET' });
            if (response.ok) {
                const mentee = await response.json();
                if (menteeDashboardName) menteeDashboardName.textContent = mentee.name; // Display name in dashboard title
                menteeDashboardProfileSummary.innerHTML = `
                    <h2>Your Profile</h2>
                    <p><strong>Mentee ID:</strong> ${mentee.id}</p>
                    <p><strong>Name:</strong> ${mentee.name}</p> {# Display mentee's name #}
                    <p><strong>Bio:</strong> ${mentee.bio}</p>
                    <p><strong>Goals:</strong> ${mentee.goals || 'Not specified'}</p>
                    <p><strong>Mentorship Style:</strong> ${mentee.mentorship_style || 'Not specified'}</p>
                    <p><strong>Availability:</strong> ${mentee.availability?.hours_per_month || 'Not specified'} hours/month</p>
                    <p><strong>Preferences:</strong> Industries: ${(mentee.preferences?.industries || []).join(', ') || 'Any'}, Languages: ${(mentee.preferences?.languages || []).join(', ') || 'Any'}</p>
                `;
                menteeDashboardProfileSummary.appendChild(menteeProfileMessage);
            } else {
                showFormMessage(menteeProfileMessage, `Failed to load mentee profile details: ${response.statusText}. Please ensure the ID is correct.`, 'error');
                console.error(`Failed to fetch mentee details for ID ${menteeId}:`, response.status, await response.text());
            }
        } catch (error) {
            showFormMessage(menteeProfileMessage, `Error loading mentee profile details. Network error: ${error.message}`, 'error');
            console.error(`Network error fetching mentee details for ID ${menteeId}:`, error);
        }
    }


    async function fetchMenteeMentorshipRequests(menteeId) {
        if (!menteeDashboardRequestsList || !menteeRequestsMessage) return;
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
            showFormMessage(menteeRequestsMessage, `Network error or unable to connect to server: ${error.message}`, 'error');
            menteeDashboardRequestsList.innerHTML = '<p>Failed to load requests due to network error.</p>';
            console.error('Fetch error fetching mentee requests:', error);
        }
    }

    function renderMenteeMentorshipRequests(requests) {
        if (menteeDashboardRequestsList) menteeDashboardRequestsList.innerHTML = '';

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
        if (pendingSection && menteeDashboardRequestsList) menteeDashboardRequestsList.appendChild(pendingSection);

        const activeSection = createRequestCategorySection('Active Mentorships', activeRequests, 'active');
        if (activeSection && menteeDashboardRequestsList) menteeDashboardRequestsList.appendChild(activeSection);

        const historicalSection = createRequestCategorySection('Historical Journeys', historicalRequests, 'historical');
        if (historicalSection && menteeDashboardRequestsList) menteeDashboardRequestsList.appendChild(historicalSection);

        if (pendingRequests.length === 0 && activeRequests.length === 0 && historicalRequests.length === 0) {
            if (menteeDashboardRequestsList) menteeDashboardRequestsList.innerHTML = '<p>No mentorship requests found.</p>';
        }

        attachMenteeRequestButtonListeners();
    }

    function createMenteeRequestCard(request, type) {
        const card = document.createElement('article');
        card.setAttribute('data-request-status', request.status);
        const statusClass = request.status.toLowerCase();

        let cardContent = `
            <h5>Request ID: ${request.id}</h5>
            <p><strong>Mentor:</strong> ${request.mentor_name || request.mentor_id}</p> {# Display mentor's name or ID fallback #}
            <p><strong>Status:</strong> <mark class="${statusClass}">${request.status}</mark></p>
            <p><strong>Requested:</strong> ${new Date(request.request_date).toLocaleDateString()}</p>
            ${request.request_message ? `<p><strong>Your Message:</strong> <em>${request.request_message}</em></p>` : ''}
        `;

        let footerButtons = '';
        if (request.status === 'PENDING') {
            footerButtons = `
                <button type="button" class="mentee-request-action-btn secondary" data-action="cancel" data-request-id="${request.id}" data-mentee-id="${currentMenteeDashboardId}">Cancel Request</button>
            `;
        } else if (request.status === 'ACCEPTED') {
            footerButtons = `
                <button type="button" class="mentee-request-action-btn" data-action="conclude" data-request-id="${request.id}" data-mentee-id="${currentMenteeDashboardId}">Conclude Mentorship</button>
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
                fetchMenteeDetails(menteeId); 
            } else {
                showFormMessage(menteeRequestsMessage, `Error performing ${action} for request ${requestId}: ${result.detail || 'Unknown error.'}`, 'error');
                console.error(`API Error for ${action} request ${requestId}:`, result);
            }
        } catch (error) {
            showFormMessage(menteeRequestsMessage, `Network error or unable to connect to server: ${error.message}`, 'error');
            console.error(`Fetch error for ${action} request ${requestId}:`, error);
        }
    }

    // --- Feedback Form Logic (Uses authorizedFetch) ---
    if (feedbackForm) {
        hideFormMessage(feedbackResponseMessage);
        if (ratingFeedback) hideFormMessage(ratingFeedback);

        feedbackForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            hideFormMessage(feedbackResponseMessage);
            if (ratingFeedback) hideFormMessage(ratingFeedback);

            if (!isAuthenticated()) {
                showFormMessage(feedbackResponseMessage, 'You must be logged in to submit feedback. Please <a href="/login">Login</a> or <a href="/register">Register</a>.', 'error');
                return;
            }

            const formData = new FormData(feedbackForm);
            const mentee_id = parseInt(formData.get('mentee_id'), 10);
            const mentor_id = parseInt(formData.get('mentor_id'), 10);
            const rating = parseInt(formData.get('rating'), 10);
            const comment = formData.get('comment') || null;

            // Basic client-side validation
            if (isNaN(mentee_id) || mentee_id <= 0) {
                showFormMessage(feedbackResponseMessage, 'Please enter a valid Mentee ID.', 'error');
                return;
            }
            if (isNaN(mentor_id) || mentor_id <= 0) {
                showFormMessage(feedbackResponseMessage, 'Please enter a valid Mentor ID.', 'error');
                return;
            }
            if (isNaN(rating) || rating < 1 || rating > 5) {
                if (ratingFeedback) showFormMessage(ratingFeedback, 'Please select a rating between 1 and 5 stars.', 'error');
                else showFormMessage(feedbackResponseMessage, 'Please select a rating between 1 and 5 stars.', 'error');
                return;
            }

            const feedbackData = {
                mentee_id,
                mentor_id,
                rating,
                comment,
            };

            console.log('Sending feedback data:', feedbackData);

            try {
                const response = await authorizedFetch('/feedback/', {
                    method: 'POST',
                    body: JSON.stringify(feedbackData),
                });

                const result = await response.json();

                if (response.ok) {
                    showFormMessage(feedbackResponseMessage, 'Thank you! Your feedback has been submitted successfully.', 'success');
                    feedbackForm.reset();
                } else {
                    showFormMessage(feedbackResponseMessage, `Error submitting feedback: ${result.detail || 'Unknown error.'}`, 'error');
                    console.error('API Error:', result);
                }
            } catch (error) {
                showFormMessage(feedbackResponseMessage, 'Network error or unable to connect to server.', 'error');
                console.error('Fetch error:', error);
            }
        });
    }

    // --- Initial setup on page load ---
    checkSessionAndFetchUser();
});