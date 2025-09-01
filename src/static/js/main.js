document.addEventListener('DOMContentLoaded', () => {
    // --- Common Elements & Helpers ---
    // This is for the 'MentorMatch' strong tag on the left side of the nav
    const mainNavLinks = document.getElementById('main-nav-links'); 
    // This is for the <ul> containing functional links on the right side of the nav
    const mainNavLinksRight = document.getElementById('main-nav-links-right'); 

    // Navigation Items - Dynamically managed visibility
    const navBecomeMentor = document.getElementById('nav-become-mentor'); 
    const navFindMentor = document.getElementById('nav-find-mentor');     
    const navMentorDashboard = document.getElementById('nav-mentor-dashboard'); 
    const navMenteeDashboard = document.getElementById('nav-mentee-dashboard'); 
    const navFeedback = document.getElementById('nav-feedback');         
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

    // Response Messages for Forms (these will display inline below forms/sections)
    const registerResponseMessage = document.getElementById('register-response-message');
    const loginResponseMessage = document.getElementById('login-response-message');
    const mentorResponseMessage = document.getElementById('mentor-response-message');
    const menteeResponseMessage = document.getElementById('mentee-response-message');
    const feedbackResponseMessage = document.getElementById('feedback-response-message');
    
    // Client-side validation feedback elements (e.g., password mismatch)
    const passwordMatchFeedback = document.getElementById('password-match-feedback');
    const ratingFeedback = document.getElementById('rating-feedback');

    // Mentee Signup/Dashboard Specifics (Recommendations section is now primarily on the mentee dashboard)
    const recommendationsSection = document.getElementById('recommendations-section'); 
    const recommendationsMessage = document.getElementById('recommendations-message');
    const mentorRecommendationsDiv = document.getElementById('mentor-recommendations');
    const pickMentorModal = document.getElementById('pick-mentor-modal'); // Moved to base.html for global access
    const modalMentorName = document.getElementById('modal-mentor-name'); 
    const modalRequestMessage = document.getElementById('modal-request-message');
    const confirmPickMentorBtn = document.getElementById('confirm-pick-mentor');
    const findNewMentorsBtn = document.getElementById('find-new-mentors-btn'); // New button on mentee dashboard

    // Mentor Dashboard Specifics
    const mentorDashboardName = document.getElementById('mentor-dashboard-name'); // For dynamic dashboard title (e.g., "Alice Johnson")
    const mentorDashboardProfileSummary = document.getElementById('mentor-profile-summary');
    const mentorDashboardRequestsSection = document.getElementById('mentorship-requests-section');
    const mentorRequestsList = document.getElementById('mentorship-requests-list');
    const requestsMessage = document.getElementById('requests-message'); // General message area for mentor dashboard
    const rejectModal = document.getElementById('reject-modal');
    const rejectionReasonInput = document.getElementById('rejection-reason');
    const confirmRejectBtn = document.getElementById('confirm-reject-btn');
    const mentorProfileMessage = document.getElementById('mentor-profile-message'); // Specific message area for mentor profile fetch errors

    // Mentee Dashboard Specifics
    const menteeDashboardName = document.getElementById('mentee-dashboard-name'); // For dynamic dashboard title (e.g., "Bob Williams")
    const menteeDashboardProfileSummary = document.getElementById('mentee-profile-summary');
    const menteeDashboardRequestsList = document.getElementById('mentee-mentorship-requests-list');
    const menteeRequestsMessage = document.getElementById('mentee-requests-message'); // General message area for mentee dashboard
    const menteeProfileMessage = document.getElementById('mentee-profile-message'); // Specific message area for mentee profile fetch errors
    
    // --- Global State Variables ---
    let currentMenteeId = null;
    let selectedMentorId = null;
    let currentMentorDashboardId = null;
    let currentMenteeDashboardId = null;
    let currentRequestIdForAction = null;
    let currentUser = null; // Stores user object (from /users/me/) if authenticated

    // --- Authentication & Navigation Helpers ---

    /**
     * Checks if a user is currently authenticated based on the currentUser state.
     * @returns {boolean} True if authenticated, false otherwise.
     */
    function isAuthenticated() {
        return currentUser !== null;
    }

    /**
     * Updates the visibility and content of navigation links based on authentication status
     * and whether the user has associated mentor/mentee profiles.
     */
    function updateNavLinks() {
        // Handle Register/Login/Logout visibility
        if (registerNavItem) registerNavItem.hidden = isAuthenticated();
        if (loginNavItem) loginNavItem.hidden = isAuthenticated();
        if (logoutNavItem) logoutNavItem.hidden = !isAuthenticated();

        // Handle dynamic dashboard/signup links visibility
        if (isAuthenticated() && currentUser) {
            // Mentor-specific links
            if (navMentorDashboard) {
                if (currentUser.mentor_profile_id) {
                    navMentorDashboard.querySelector('a').href = `/dashboard/mentor/${currentUser.mentor_profile_id}`;
                    navMentorDashboard.hidden = false;
                    if (navBecomeMentor) navBecomeMentor.hidden = true; // Hide "Become a Mentor" if already a mentor
                } else {
                    navMentorDashboard.hidden = true;
                    if (navBecomeMentor) navBecomeMentor.hidden = false; // Show "Become a Mentor" if not
                }
            }
            // Mentee-specific links
            if (navMenteeDashboard) {
                if (currentUser.mentee_profile_id) {
                    navMenteeDashboard.querySelector('a').href = `/dashboard/mentee/${currentUser.mentee_profile_id}`;
                    navMenteeDashboard.hidden = false;
                    if (navFindMentor) navFindMentor.hidden = true; // Hide "Find a Mentor" if already a mentee
                    if (navFeedback) navFeedback.hidden = false;     // Show feedback if already a mentee
                } else {
                    navMenteeDashboard.hidden = true;
                    if (navFindMentor) navFindMentor.hidden = false; // Show "Find a Mentor" if not
                    if (navFeedback) navFeedback.hidden = true;      // Hide feedback if not a mentee
                }
            }
        } else {
            // Not authenticated, hide all dynamic profile links and show generic signup/login
            if (navMentorDashboard) navMentorDashboard.hidden = true;
            if (navMenteeDashboard) navMenteeDashboard.hidden = true;
            if (navBecomeMentor) navBecomeMentor.hidden = false;
            if (navFindMentor) navFindMentor.hidden = false;
            if (navFeedback) navFeedback.hidden = true;
        }
    }

    /**
     * Checks for an active user session by calling /users/me/ and updates UI accordingly.
     * Handles redirects for protected pages if no session is active or user has existing profile.
     */
    async function checkSessionAndFetchUser() {
        try {
            const response = await fetch('/users/me/', { 
                method: 'GET', 
                headers: {'Content-Type': 'application/json'},
                credentials: 'include' // Ensures HttpOnly cookies are sent by the browser
            });
            if (response.ok) {
                currentUser = await response.json();
                console.log('Session active. User:', currentUser.username, 'Mentor ID:', currentUser.mentor_profile_id, 'Mentee ID:', currentUser.mentee_profile_id);
                
                updateNavLinks(); // Update generic login/logout and dynamic profile links

                // Redirect logic: If logged in, prevent access to signup pages they no longer need
                const path = window.location.pathname;
                if (path.startsWith('/signup/mentor') && currentUser.mentor_profile_id) {
                    window.location.href = `/dashboard/mentor/${currentUser.mentor_profile_id}`;
                }
                if (path.startsWith('/signup/mentee') && currentUser.mentee_profile_id) {
                    window.location.href = `/dashboard/mentee/${currentUser.mentee_profile_id}`;
                }

            } else {
                currentUser = null; // Clear user state if session is invalid
                console.log('No active session or token expired.');
                updateNavLinks(); // This will show Register/Login links again

                // Redirect from protected dashboard/feedback pages if no session is active
                const path = window.location.pathname;
                if (path.startsWith('/dashboard/') || path.startsWith('/feedback')) {
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

    /**
     * Logs out the current user by sending a request to the backend to clear the HttpOnly cookie.
     */
    async function logout() {
        try {
            const response = await fetch('/logout', { 
                method: 'POST',
                credentials: 'include' // Ensures HttpOnly cookie is sent to be cleared
            }); 
            if (response.ok) {
                currentUser = null; 
                console.log('Logged out successfully from backend and client.');
                updateNavLinks();
                window.location.href = '/login'; 
            } else {
                console.error('Logout failed on backend:', await response.text());
                currentUser = null; // Still clear client-side state for UX
                updateNavLinks();
                window.location.href = '/login';
            }
        } catch (error) {
            console.error('Network error during logout:', error);
            currentUser = null; // Still clear client-side state for UX
            updateNavLinks();
            window.location.href = '/login';
        }
    }
    if (logoutBtn) {
        logoutBtn.addEventListener('click', logout);
    }

    // --- Generic Message Handlers ---

    /**
     * Displays a message to the user, applying appropriate styling.
     * @param {HTMLElement} messageElement - The HTML element to display the message in.
     * @param {string} message - The message text or HTML to display.
     * @param {'success'|'error'} type - The type of message ('success' or 'error') for styling.
     */
    function showFormMessage(messageElement, message, type) {
        if (messageElement) {
            messageElement.innerHTML = message;
            messageElement.setAttribute('data-variant', type);
            messageElement.hidden = false; 
        }
    }

    /**
     * Hides a displayed message.
     * @param {HTMLElement} messageElement - The HTML element containing the message.
     */
    function hideFormMessage(messageElement) {
        if (messageElement) {
            messageElement.innerHTML = '';
            messageElement.removeAttribute('data-variant');
            messageElement.hidden = true; 
        }
    }

    // --- Modal Toggle Helpers (Generic for Pico.css dialogs) ---

    /**
     * Toggles the visibility of a Pico.css dialog modal.
     * @param {HTMLDialogElement} dialogElement - The <dialog> element to toggle.
     * @param {Event} [event] - Optional event object to prevent default behavior.
     */
    function toggleDialog(dialogElement, event) {
        if (!dialogElement) return;
        if (event) event.preventDefault();
        if (dialogElement.hasAttribute('open')) {
            dialogElement.removeAttribute('open');
            document.body.style.overflow = ''; // Restore scroll
        } else {
            dialogElement.setAttribute('open', '');
            document.body.style.overflow = 'hidden'; // Prevent scroll
        }
    }
    // Make modal toggles globally accessible (defined in base.html)
    window.togglePickMentorModal = (event) => toggleDialog(pickMentorModal, event);
    window.toggleRejectModal = (event) => toggleDialog(rejectModal, event);

    // --- Centralized API Call Helper (for protected endpoints) ---

    /**
     * Performs an authorized fetch request, automatically including HttpOnly cookies
     * and handling 401 Unauthorized responses by logging out the user.
     * @param {string} url - The URL to fetch.
     * @param {RequestInit} [options={}] - Standard fetch options.
     * @returns {Promise<Response>} The fetch response.
     * @throws {Error} If unauthorized or a network error occurs.
     */
    async function authorizedFetch(url, options = {}) {
        const headers = { ...options.headers };

        // Default Content-Type to application/json if body exists and not explicitly set
        if (options.body && !headers['Content-Type']) {
            headers['Content-Type'] = 'application/json';
        } else if (!options.body && ['GET', 'HEAD'].includes(options.method?.toUpperCase())) {
            // Remove Content-Type for GET/HEAD requests if no body
            delete headers['Content-Type'];
        }
        
        const response = await fetch(url, { ...options, headers, credentials: 'include' });

        if (response.status === 401) {
            console.warn('Unauthorized access: Session expired or invalid. Redirecting to login.');
            logout(); // Trigger full logout sequence
            throw new Error('Unauthorized: API responded with 401.'); 
        }
        return response;
    }


    // --- Register Form Logic ---
    if (registerForm) {
        hideFormMessage(registerResponseMessage);
        if (passwordMatchFeedback) hideFormMessage(passwordMatchFeedback);

        registerForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            hideFormMessage(registerResponseMessage);
            if (passwordMatchFeedback) hideFormMessage(passwordMatchFeedback); // Clear password mismatch on new submit

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
                    credentials: 'include' 
                });

                if (response.ok) {
                    await checkSessionAndFetchUser(); // Refresh session state and nav links
                    showFormMessage(loginResponseMessage, `Login successful! Welcome, ${username}. Redirecting...`, 'success');
                    window.location.href = '/'; // Redirect to homepage
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


    // --- Mentor Signup Form Logic ---
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

            data.name = formData.get('name'); 
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
                preferences.industries = null;
            }
            const languages = formData.get('preferences_languages');
            if (languages && languages.trim() !== '') {
                preferences.languages = languages.split(',').map(item => item.trim()).filter(item => item !== '');
            } else {
                preferences.languages = null;
            }
            data.preferences = (preferences.industries || preferences.languages) ? preferences : null;

            // --- NEW DEMOGRAPHICS HANDLING (individual fields) ---
            const demographics = {};
            const gender = formData.get('demographics_gender');
            if (gender && gender.trim() !== '') {
                demographics.gender = gender;
            }
            const ethnicity = formData.get('demographics_ethnicity');
            if (ethnicity && ethnicity.trim() !== '') {
                demographics.ethnicity = ethnicity;
            }
            const yearsExperience = parseInt(formData.get('demographics_years_experience'), 10);
            if (!isNaN(yearsExperience) && yearsExperience >= 0) {
                demographics.years_experience = yearsExperience;
            }

            data.demographics = (Object.keys(demographics).length > 0) ? demographics : null;
            // --- END NEW DEMOGRAPHICS HANDLING ---

            console.log('Sending mentor data:', data);

            try {
                const response = await authorizedFetch('/mentors/', {
                    method: 'POST',
                    body: JSON.stringify(data),
                });

                const result = await response.json();

                if (response.ok) {
                    showFormMessage(mentorResponseMessage, `Mentor ${result.name} registered successfully! Your ID is: ${result.id}. Redirecting to your dashboard...`, 'success');
                    mentorSignupForm.reset();
                    window.location.href = `/dashboard/mentor/${result.id}`; 
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

    // --- Mentee Signup Form Logic ---
    if (menteeSignupForm) {
        hideFormMessage(menteeResponseMessage);

        menteeSignupForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            hideFormMessage(menteeResponseMessage);
            // Recommendations section is no longer on this page, only on dashboard.
            // So these can be removed from here.
            // if (recommendationsSection) recommendationsSection.hidden = true;
            // if (mentorRecommendationsDiv) mentorRecommendationsDiv.innerHTML = '';


            if (!isAuthenticated()) {
                showFormMessage(menteeResponseMessage, 'You must be logged in to find a mentor. Please <a href="/login">Login</a> or <a href="/register">Register</a>.', 'error');
                return;
            }

            const formData = new FormData(menteeSignupForm);
            const data = {};

            data.name = formData.get('name'); 
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
                preferences.industries = null;
            }
            const languages = formData.get('preferences_languages');
            if (languages && languages.trim() !== '') {
                preferences.languages = languages.split(',').map(item => item.trim()).filter(item => item !== '');
            } else {
                preferences.languages = null;
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
                    showFormMessage(menteeResponseMessage, `Mentee ${result.mentee_name} registered. Your ID is: ${currentMenteeId}. Redirecting to your dashboard...`, 'success');
                    window.location.href = `/dashboard/mentee/${currentMenteeId}`;
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

    // --- NEW: Find New Mentors Button on Mentee Dashboard ---
    if (findNewMentorsBtn) {
        findNewMentorsBtn.addEventListener('click', async () => {
            if (!isAuthenticated()) {
                showFormMessage(menteeRequestsMessage, 'You must be logged in to find mentors.', 'error');
                return;
            }
            if (!currentMenteeDashboardId) {
                showFormMessage(menteeRequestsMessage, 'Mentee profile not loaded.', 'error');
                return;
            }

            hideFormMessage(menteeRequestsMessage); 
            if (recommendationsSection) recommendationsSection.hidden = true; // Hide old recommendations
            if (mentorRecommendationsDiv) mentorRecommendationsDiv.innerHTML = '<p aria-busy="true">Finding mentors...</p>'; // Show loading indicator


            try {
                // Fetch mentee's current profile from backend to use for matching
                const profileResponse = await fetch(`/mentees/${currentMenteeDashboardId}`, { method: 'GET' });
                if (!profileResponse.ok) {
                    const errorDetail = await profileResponse.json().then(data => data.detail || 'Unknown error').catch(() => 'Unknown error during profile fetch');
                    throw new Error(`Failed to fetch mentee profile for matching: ${errorDetail}`);
                }
                const menteeProfileData = await profileResponse.json();

                // Call the /match/ endpoint with this data
                const response = await authorizedFetch('/match/', {
                    method: 'POST',
                    body: JSON.stringify(menteeProfileData), // Send current profile data for matching
                });

                const result = await response.json();

                if (response.ok) {
                    if (result.recommendations && result.recommendations.length > 0) {
                        displayRecommendations(result.recommendations); // This function will display in recommendationsSection
                    } else {
                        if (recommendationsMessage) recommendationsMessage.textContent = result.message || "No suitable mentors found based on your criteria. Please try broadening your preferences.";
                        if (recommendationsSection) recommendationsSection.hidden = false;
                    }
                    showFormMessage(menteeRequestsMessage, result.message, 'success');
                } else {
                    showFormMessage(menteeRequestsMessage, `Error finding matches: ${result.detail || 'Could not find matches.'}`, 'error');
                    console.error('API Error:', result);
                }
            } catch (error) {
                showFormMessage(menteeRequestsMessage, `Network error or unable to connect to server for finding matches: ${error.message}`, 'error');
                console.error('Fetch error for finding matches:', error);
            }
        });
    }

    // --- Function to Display Recommendations (now called on dashboard) ---
    function displayRecommendations(recommendations) {
        if (mentorRecommendationsDiv) mentorRecommendationsDiv.innerHTML = ''; // Clear loading indicator
        if (recommendationsMessage) recommendationsMessage.textContent = "Here are your top mentor recommendations:";
        
        recommendations.forEach(mentor => {
            const card = document.createElement('article');
            const rawBio = mentor.mentor_bio_snippet || '';
            const bioSnippet = rawBio.length > 100 ? rawBio.substring(0, 100) + '...' : rawBio;

            card.innerHTML = `
                <h4>${mentor.mentor_name || 'Unknown Mentor'}</h4>
                <p>${bioSnippet}</p>
                <p><strong>Expertise:</strong> ${mentor.mentor_details.expertise || 'Not specified'}</p>
                <p><strong>Capacity:</strong> ${mentor.mentor_details.capacity_info || 'N/A'}</p>
                <p><strong>Match Score:</strong> ${mentor.re_rank_score ? mentor.re_rank_score.toFixed(2) : 'N/A'}</p>
                <h5>Why this match?</h5>
                <ul>
                    ${mentor.explanations.map(exp => `<li>${exp}</li>`).join('')}
                </ul>
                <footer>
                    <button type="button" class="pick-mentor-btn" data-mentor-id="${mentor.mentor_id}" data-mentor-name="${mentor.mentor_name || 'Unknown Mentor'}">Pick This Mentor</button>
                </footer>
            `;
            if (mentorRecommendationsDiv) mentorRecommendationsDiv.appendChild(card);
        });
        if (recommendationsSection) recommendationsSection.hidden = false;

        document.querySelectorAll('.pick-mentor-btn').forEach(button => {
            button.addEventListener('click', (event) => {
                selectedMentorId = parseInt(event.currentTarget.dataset.mentorId, 10);
                if (modalMentorName) modalMentorName.textContent = event.currentTarget.dataset.mentorName;
                if (modalRequestMessage) modalRequestMessage.value = '';
                togglePickMentorModal();
            });
        });
    }

    // --- Mentor Dashboard Logic ---
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

    /**
     * Fetches and displays details for a specific mentor on their dashboard.
     * @param {number} mentorId - The ID of the mentor.
     */
    async function fetchMentorDetails(mentorId) {
        if (!mentorDashboardProfileSummary || !mentorProfileMessage || !mentorDashboardName) return;
        hideFormMessage(mentorProfileMessage); // Hide previous messages

        try {
            const response = await fetch(`/mentors/${mentorId}`, { method: 'GET' });
            if (response.ok) {
                const mentor = await response.json();
                if (mentorDashboardName) mentorDashboardName.textContent = mentor.name; // Display name in dashboard title
                mentorDashboardProfileSummary.innerHTML = `
                    <h2>Your Profile</h2>
                    <p><strong>Mentor ID:</strong> ${mentor.id}</p>
                    <p><strong>Name:</strong> ${mentor.name}</p>
                    <p><strong>Bio:</strong> ${mentor.bio}</p>
                    <p><strong>Expertise:</strong> ${mentor.expertise || 'Not specified'}</p>
                    <p><strong>Capacity:</strong> ${mentor.current_mentees} / ${mentor.capacity} active mentees</p>
                    <p><strong>Availability:</strong> ${mentor.availability?.hours_per_month || 'Not specified'} hours/month</p>
                    <p><strong>Preferences:</strong> Industries: ${(mentor.preferences?.industries || []).join(', ') || 'Any'}, Languages: ${(mentor.preferences?.languages || []).join(', ') || 'Any'}</p>
                    ${mentor.demographics ? `<p><strong>Demographics:</strong> Gender: ${mentor.demographics.gender || 'N/A'}, Ethnicity: ${mentor.demographics.ethnicity || 'N/A'}, Years Exp: ${mentor.demographics.years_experience || 'N/A'}</p>` : ''}
                `;
                // Re-append the message element to ensure it's available for future showFormMessage calls
                // (innerHTML replaces content, so we ensure the message <p> is still there)
                if (!mentorDashboardProfileSummary.contains(mentorProfileMessage)) {
                    mentorDashboardProfileSummary.appendChild(mentorProfileMessage);
                }
            } else {
                showFormMessage(mentorProfileMessage, `Failed to load mentor profile details: ${response.statusText}. Please ensure the ID is correct.`, 'error');
                console.error(`Failed to fetch mentor details for ID ${mentorId}:`, response.status, await response.text());
            }
        } catch (error) {
            showFormMessage(mentorProfileMessage, `Error loading mentor profile details. Network error: ${error.message}`, 'error');
            console.error(`Network error fetching mentor details for ID ${mentorId}:`, error);
        }
    }

    /**
     * Fetches and displays mentorship requests for a specific mentor.
     * @param {number} mentorId - The ID of the mentor.
     */
    async function fetchMentorshipRequests(mentorId) {
        if (!mentorRequestsList || !requestsMessage) return;
        hideFormMessage(requestsMessage);
        mentorRequestsList.innerHTML = '<p aria-busy="true">Loading your requests...</p>'; // Show loading indicator

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

    /**
     * Renders mentorship request cards for a mentor, categorized by status.
     * @param {Array<Object>} requests - List of mentorship request objects.
     */
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
            cardsContainer.className = 'grid'; 
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

    /**
     * Creates an HTML article card for a single mentorship request (mentor's view).
     * @param {Object} request - The mentorship request object.
     * @param {string} type - Category type for styling.
     * @returns {HTMLElement} The created article element.
     */
    function createMentorRequestCard(request, type) {
        const card = document.createElement('article');
        card.setAttribute('data-request-status', request.status);
        const statusClass = request.status.toLowerCase();

        let cardContent = `
            <h5>Request ID: ${request.id}</h5>
            <p><strong>Mentee:</strong> <a href="/dashboard/mentee/${request.mentee_id}" class="secondary">${request.mentee_name || request.mentee_id}</a></p>
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

    /**
     * Attaches event listeners to action buttons on mentor request cards.
     */
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

    /**
     * Performs a mentor action (accept, reject, complete) on a mentorship request.
     * @param {number} mentorId - The ID of the mentor performing the action.
     * @param {number} requestId - The ID of the mentorship request.
     * @param {string} action - The action to perform ('accept', 'reject', 'complete').
     * @param {string} [rejectionReason=null] - Optional reason for rejection.
     */
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

    // Listener for confirming rejection in the modal
    if (confirmRejectBtn) {
        confirmRejectBtn.addEventListener('click', async (event) => {
            const rejectionReason = rejectionReasonInput ? rejectionReasonInput.value : '';
            await performMentorAction(currentMentorDashboardId, currentRequestIdForAction, 'reject', rejectionReason);
            toggleRejectModal();
            if (rejectionReasonInput) rejectionReasonInput.value = ''; // Clear input after use
        });
    }


    // --- Mentee Dashboard Logic ---
    const menteePathSegments = window.location.pathname.split('/');
    if (menteePathSegments[1] === 'dashboard' && menteePathSegments[2] === 'mentee' && menteePathSegments[3]) {
        currentMenteeDashboardId = parseInt(menteePathSegments[3], 10);
        if (!isNaN(currentMenteeDashboardId)) {
            fetchMenteeDetails(currentMenteeDashboardId);
            fetchMenteeMentorshipRequests(currentMenteeDashboardId);
            // The "Find New Mentors" button listener (`findNewMentorsBtn`) is attached globally if it exists.
        } else {
            showFormMessage(menteeProfileMessage, 'Invalid mentee ID in URL.', 'error');
        }
    }

    /**
     * Fetches and displays details for a specific mentee on their dashboard.
     * @param {number} menteeId - The ID of the mentee.
     */
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
                    <p><strong>Name:</strong> ${mentee.name}</p>
                    <p><strong>Bio:</strong> ${mentee.bio}</p>
                    <p><strong>Goals:</strong> ${mentee.goals || 'Not specified'}</p>
                    <p><strong>Mentorship Style:</strong> ${mentee.mentorship_style || 'Not specified'}</p>
                    <p><strong>Availability:</strong> ${mentee.availability?.hours_per_month || 'Not specified'} hours/month</p>
                    <p><strong>Preferences:</strong> Industries: ${(mentee.preferences?.industries || []).join(', ') || 'Any'}, Languages: ${(mentee.preferences?.languages || []).join(', ') || 'Any'}</p>
                `;
                // Re-append the message element to ensure it's available for future showFormMessage calls
                if (!menteeDashboardProfileSummary.contains(menteeProfileMessage)) {
                    menteeDashboardProfileSummary.appendChild(menteeProfileMessage);
                }
            } else {
                showFormMessage(menteeProfileMessage, `Failed to load mentee profile details: ${response.statusText}. Please ensure the ID is correct.`, 'error');
                console.error(`Failed to fetch mentee details for ID ${menteeId}:`, response.status, await response.text());
            }
        } catch (error) {
            showFormMessage(menteeProfileMessage, `Error loading mentee profile details. Network error: ${error.message}`, 'error');
            console.error(`Network error fetching mentee details for ID ${menteeId}:`, error);
        }
    }

    /**
     * Fetches and displays mentorship requests for a specific mentee.
     * @param {number} menteeId - The ID of the mentee.
     */
    async function fetchMenteeMentorshipRequests(menteeId) {
        if (!menteeDashboardRequestsList || !menteeRequestsMessage) return;
        hideFormMessage(menteeRequestsMessage);
        menteeDashboardRequestsList.innerHTML = '<p aria-busy="true">Loading your requests...</p>'; // Show loading indicator

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

    /**
     * Renders mentorship request cards for a mentee, categorized by status.
     * @param {Array<Object>} requests - List of mentorship request objects.
     */
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
            cardsContainer.className = 'grid'; 
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

    /**
     * Creates an HTML article card for a single mentorship request (mentee's view).
     * @param {Object} request - The mentorship request object.
     * @param {string} type - Category type for styling.
     * @returns {HTMLElement} The created article element.
     */
    function createMenteeRequestCard(request, type) {
        const card = document.createElement('article');
        card.setAttribute('data-request-status', request.status);
        const statusClass = request.status.toLowerCase();

        let cardContent = `
            <h5>Request ID: ${request.id}</h5>
            <p><strong>Mentor:</strong> <a href="/dashboard/mentor/${request.mentor_id}" class="secondary">${request.mentor_name || request.mentor_id}</a></p>
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

    /**
     * Attaches event listeners to action buttons on mentee request cards.
     */
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

    /**
     * Performs a mentee action (cancel, conclude) on a mentorship request.
     * @param {number} menteeId - The ID of the mentee performing the action.
     * @param {number} requestId - The ID of the mentorship request.
     * @param {string} action - The action to perform ('cancel', 'conclude').
     */
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
                fetchMenteeMentorshipRequests(menteeId); // Refresh requests
                fetchMenteeDetails(menteeId); // Refresh mentee details 
            } else {
                showFormMessage(menteeRequestsMessage, `Error performing ${action} for request ${requestId}: ${result.detail || 'Unknown error.'}`, 'error');
                console.error(`API Error for ${action} request ${requestId}:`, result);
            }
        } catch (error) {
            showFormMessage(menteeRequestsMessage, `Network error or unable to connect to server: ${error.message}`, 'error');
            console.error(`Fetch error for ${action} request ${requestId}:`, error);
        }
    }

    // --- Feedback Form Logic ---
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