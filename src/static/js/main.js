/* src/static/js/main.js */
document.addEventListener('DOMContentLoaded', async() => {
    // --- Common Elements & Helpers ---
    const mainNavLinks = document.getElementById('main-nav-links');
    const mainNavLinksRight = 
    document.getElementById('main-nav-links-right');

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

    // Response Messages for Forms
    const registerResponseMessage = document.getElementById('register-response-message');
    const loginResponseMessage = document.getElementById('login-response-message');
    const mentorResponseMessage = document.getElementById('mentor-response-message');
    const menteeResponseMessage = document.getElementById('mentee-response-message');
    const feedbackResponseMessage = document.getElementById('feedback-response-message');

    // Client-side validation feedback elements
    const passwordMatchFeedback = document.getElementById('password-match-feedback');
    const ratingFeedback = document.getElementById('rating-feedback');

    // Mentee Dashboard Specifics (Recommendations section is now primarily on the recommendations page)
    const findNewMentorsBtn = document.getElementById('find-new-mentors-btn'); 
    const pickMentorModal = document.getElementById('pick-mentor-modal'); 
    const modalMentorName = document.getElementById('modal-mentor-name');
    const modalRequestMessage = document.getElementById('modal-request-message');
    const confirmPickMentorBtn = document.getElementById('confirm-pick-mentor');
    
    // NEW: Elements for the Recommendations Page
    const recommendationsPageSection = document.getElementById('recommendations-section'); // Section on the new recommendations.html
    const recommendationsPageMessage = document.getElementById('recommendations-message'); // Message on the new recommendations.html
    const mentorRecommendationsDiv = document.getElementById('mentor-recommendations'); // Container on the new recommendations.html
    const proceedToDashboardBtn = document.getElementById('proceed-to-dashboard-btn'); // Button on the new recommendations.html

    // Mentor Dashboard Specifics
    const mentorDashboardName = document.getElementById('mentor-dashboard-name');
    const mentorDashboardProfileSummary = document.getElementById('mentor-profile-summary');
    const mentorDashboardRequestsSection = document.getElementById('mentorship-requests-section');
    const mentorRequestsList = document.getElementById('mentorship-requests-list');
    const requestsMessage = document.getElementById('requests-message');
    const rejectModal = document.getElementById('reject-modal');
    const rejectionReasonInput = document.getElementById('rejection-reason');
    const confirmRejectBtn = document.getElementById('confirm-reject-btn');
    const mentorProfileMessage = document.getElementById('mentor-profile-message');

    // Mentee Dashboard Specifics
    const menteeDashboardName = document.getElementById('mentee-dashboard-name');
    const menteeDashboardProfileSummary = document.getElementById('mentee-profile-summary');
    const menteeDashboardRequestsList = document.getElementById('mentee-mentorship-requests-list');
    const menteeRequestsMessage = document.getElementById('mentee-requests-message');
    const menteeProfileMessage = document.getElementById('mentee-profile-message');


    // --- Global State Variables ---
    let currentMenteeId = null; // Used for mentee signup redirects
    let selectedMentorId = null;
    let currentMentorDashboardId = null;
    let currentMenteeDashboardId = null; // Used for mentee dashboard redirects & actions
    let currentRequestIdForAction = null;
    let currentUser = null;

    // --- Authentication & Navigation Helpers ---

    function isAuthenticated() {
        return currentUser !== null;
    }

    function updateNavLinks() {
        if (registerNavItem) registerNavItem.hidden = isAuthenticated();
        if (loginNavItem) loginNavItem.hidden = isAuthenticated();
        if (logoutNavItem) logoutNavItem.hidden = !isAuthenticated();

        if (isAuthenticated() && currentUser) {
            if (navMentorDashboard) {
                if (currentUser.mentor_profile_id) {
                    navMentorDashboard.querySelector('a').href = `/dashboard/mentor/${currentUser.mentor_profile_id}`;
                    navMentorDashboard.hidden = false;
                    if (navBecomeMentor) navBecomeMentor.hidden = true;
                } else {
                    navMentorDashboard.hidden = true;
                    if (navBecomeMentor) navBecomeMentor.hidden = false;
                }
            }
            if (navMenteeDashboard) {
                if (currentUser.mentee_profile_id) {
                    navMenteeDashboard.querySelector('a').href = `/dashboard/mentee/${currentUser.mentee_profile_id}`;
                    navMenteeDashboard.hidden = false;
                    if (navFindMentor) navFindMentor.hidden = true;
                    if (navFeedback) navFeedback.hidden = false;
                } else {
                    navMenteeDashboard.hidden = true;
                    if (navFindMentor) navFindMentor.hidden = false;
                    if (navFeedback) navFeedback.hidden = true;
                }
            }
        } else {
            if (navMentorDashboard) navMentorDashboard.hidden = true;
            if (navMenteeDashboard) navMenteeDashboard.hidden = true;
            if (navBecomeMentor) navBecomeMentor.hidden = false;
            if (navFindMentor) navFindMentor.hidden = false;
            if (navFeedback) navFeedback.hidden = true;
        }
    }

    // Intercept "Find Your Mentor" for existing mentees to go straight to recommendations
    const navFindMentorLink = navFindMentor ? navFindMentor.querySelector('a') : null;
    if (navFindMentorLink) {
        navFindMentorLink.addEventListener('click', async (event) => {
            // If user is logged in and already has a mentee profile, run match and redirect to recommendations
            if (isAuthenticated() && currentUser?.mentee_profile_id) {
                event.preventDefault();
                try {
                    const menteeId = currentUser.mentee_profile_id;

                    // Ensure we have the latest mentee profile
                    const profileResponse = await authorizedFetch(`/api/mentees/${menteeId}`, { method: 'GET' });
                    if (!profileResponse.ok) {
                        throw new Error('Failed to fetch mentee profile for matching');
                    }
                    const menteeProfileData = await profileResponse.json();

                    // Trigger match using existing profile
                    const matchResponse = await authorizedFetch(`/api/mentees/${menteeId}/match`, {
                        method: 'POST',
                        body: JSON.stringify(menteeProfileData),
                    });
                    const result = await matchResponse.json();

                    if (matchResponse.ok) {
                        sessionStorage.setItem('menteeIdForRecommendations', menteeId.toString());
                        if (result.recommendations && result.recommendations.length > 0) {
                            sessionStorage.setItem('initialRecommendations', JSON.stringify(result.recommendations));
                            sessionStorage.removeItem('recommendationsMessage');
                        } else {
                            sessionStorage.setItem('initialRecommendations', JSON.stringify([]));
                            sessionStorage.setItem('recommendationsMessage', result.message || 'No suitable mentors found based on your criteria. Please try broadening your preferences.');
                        }
                        window.location.href = `/mentees/${menteeId}/recommendations`;
                    } else {
                        // Fall back to mentee dashboard on failure
                        console.error('Error running match from nav:', result);
                        window.location.href = `/dashboard/mentee/${menteeId}`;
                    }
                } catch (e) {
                    console.error('Network error running match from nav:', e);
                    // As a fallback, let them go to signup if something unexpected happened
                    window.location.href = '/signup/mentee';
                }
            }
            // else: not authenticated or no mentee profile → default link to /signup/mentee
        });
    }

    async function checkSessionAndFetchUser() {
        try {
            const response = await fetch('/users/me/', {
                method: 'GET',
                headers: {'Content-Type': 'application/json'},
                credentials: 'include'
            });
            if (response.ok) {
                currentUser = await response.json();
                console.log('Session active. User:', currentUser.username, 'Mentor ID:', currentUser.mentor_profile_id, 'Mentee ID:', currentUser.mentee_profile_id);

                updateNavLinks();

                const path = window.location.pathname;
                if (path.startsWith('/signup/mentor') && currentUser.mentor_profile_id) {
                    window.location.href = `/dashboard/mentor/${currentUser.mentor_profile_id}`;
                }
                if (path.startsWith('/signup/mentee') && currentUser.mentee_profile_id) {
                    window.location.href = `/dashboard/mentee/${currentUser.mentee_profile_id}`;
                }

            } else {
                currentUser = null;
                console.log('No active session or token expired.');
                updateNavLinks();

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

    async function logout() {
        try {
            const response = await fetch('/logout', {
                method: 'POST',
                credentials: 'include'
            });
            if (response.ok) {
                currentUser = null;
                console.log('Logged out successfully from backend and client.');
                updateNavLinks();
                // Clear any stored recommendations on logout
                sessionStorage.removeItem('initialRecommendations');
                sessionStorage.removeItem('menteeIdForRecommendations');
                sessionStorage.removeItem('recommendationsMessage');
                window.location.href = '/login';
            } else {
                console.error('Logout failed on backend:', await response.text());
                currentUser = null;
                updateNavLinks();
                sessionStorage.removeItem('initialRecommendations');
                sessionStorage.removeItem('menteeIdForRecommendations');
                sessionStorage.removeItem('recommendationsMessage');
                window.location.href = '/login';
            }
        } catch (error) {
            console.error('Network error during logout:', error);
            currentUser = null;
            updateNavLinks();
            sessionStorage.removeItem('initialRecommendations');
            sessionStorage.removeItem('menteeIdForRecommendations');
            sessionStorage.removeItem('recommendationsMessage');
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
            messageElement.hidden = false;
        }
    }

    function hideFormMessage(messageElement) {
        if (messageElement) {
            messageElement.innerHTML = '';
            messageElement.removeAttribute('data-variant');
            messageElement.hidden = true;
        }
    }

    // --- Modal Toggle Helpers ---

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
        const headers = { ...options.headers };

        if (options.body && !headers['Content-Type']) {
            headers['Content-Type'] = 'application/json';
        } else if (!options.body && ['GET', 'HEAD'].includes(options.method?.toUpperCase())) {
            delete headers['Content-Type'];
        }

        const response = await fetch(url, { ...options, headers, credentials: 'include' });

        if (response.status === 401) {
            console.warn('Unauthorized access: Session expired or invalid. Redirecting to login.');
            logout();
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
                    // Point 1: Redirect immediately to login after successful registration
                    window.location.href = '/login';
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
                    await checkSessionAndFetchUser();
                    // Redirect based on user role/profile presence
                    if (currentUser?.mentee_profile_id) {
                        window.location.href = `/dashboard/mentee/${currentUser.mentee_profile_id}`;
                    } else if (currentUser?.mentor_profile_id) {
                        window.location.href = `/dashboard/mentor/${currentUser.mentor_profile_id}`;
                    } else {
                        window.location.href = '/get-started';
                    }
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

    // --- Mentee Signup Form Logic (UPDATED for Recommendations Page) ---
    if (menteeSignupForm) {
        hideFormMessage(menteeResponseMessage);

        menteeSignupForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            hideFormMessage(menteeResponseMessage);

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
                const response = await authorizedFetch('/api/mentees/match-or-create', {
                    method: 'POST',
                    body: JSON.stringify(data),
                });

                const result = await response.json();

                if (response.ok) {
                    currentMenteeId = result.mentee_id;
                    
                    sessionStorage.setItem('menteeIdForRecommendations', currentMenteeId.toString());
                    if (result.recommendations && result.recommendations.length > 0) {
                        sessionStorage.setItem('initialRecommendations', JSON.stringify(result.recommendations));
                    } else {
                        sessionStorage.setItem('initialRecommendations', JSON.stringify([]));
                        sessionStorage.setItem('recommendationsMessage', result.message || "No suitable mentors found based on your criteria. Please try broadening your preferences.");
                    }

                    showFormMessage(menteeResponseMessage, `Mentee ${result.mentee_name} registered. Redirecting to matches...`, 'success');
                    window.location.href = `/mentees/${currentMenteeId}/recommendations`;

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

    // Find New Mentors Button (on Mentee Dashboard) ---
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
            if (findNewMentorsBtn) findNewMentorsBtn.setAttribute('aria-busy', 'true');


            try {
                const profileResponse = await authorizedFetch(`/api/mentees/${currentMenteeDashboardId}`, { method: 'GET' });
                if (!profileResponse.ok) {
                    const errorDetail = await profileResponse.json().then(data => data.detail || 'Unknown error').catch(() => 'Unknown error during profile fetch');
                    throw new Error(`Failed to fetch mentee profile for matching: ${errorDetail}`);
                }
                const menteeProfileData = await profileResponse.json();

                const response = await authorizedFetch(`/api/mentees/${currentMenteeDashboardId}/match`, {
                    method: 'POST',
                    body: JSON.stringify(menteeProfileData),
                });

                const result = await response.json();

                if (response.ok) {
                    sessionStorage.setItem('menteeIdForRecommendations', currentMenteeDashboardId.toString());
                    if (result.recommendations && result.recommendations.length > 0) {
                        sessionStorage.setItem('initialRecommendations', JSON.stringify(result.recommendations));
                    } else {
                        sessionStorage.setItem('initialRecommendations', JSON.stringify([]));
                        sessionStorage.setItem('recommendationsMessage', result.message || "No suitable mentors found based on your criteria. Please try broadening your preferences.");
                    }
                    showFormMessage(menteeRequestsMessage, result.message, 'success');
                    window.location.href = `/mentees/${currentMenteeDashboardId}/recommendations`;

                } else {
                    showFormMessage(menteeRequestsMessage, `Error finding matches: ${result.detail || 'Could not find matches.'}`, 'error');
                    console.error('API Error:', result);
                }
            } catch (error) {
                showFormMessage(menteeRequestsMessage, `Network error or unable to connect to server for finding matches: ${error.message}`, 'error');
                console.error('Fetch error for finding matches:', error);
            } finally {
                if (findNewMentorsBtn) findNewMentorsBtn.removeAttribute('aria-busy');
            }
        });
    }

    // --- Function to Display Recommendations (UPDATED to use new elements) ---
    function displayRecommendations(recommendations, message = "Here are your top mentor recommendations:") {
        if (mentorRecommendationsDiv) mentorRecommendationsDiv.innerHTML = '';
        if (recommendationsPageMessage) recommendationsPageMessage.textContent = message;

        if (recommendations.length === 0) {
             if (mentorRecommendationsDiv) mentorRecommendationsDiv.innerHTML = `<p>${message}</p>`;
             return;
        }

        recommendations.forEach(mentor => {
            const card = document.createElement('article');
            const rawBio = mentor.mentor_bio_snippet || '';
            const bioSnippet = rawBio.length > 100 ? rawBio.substring(0, 100) + '...' : rawBio;

            card.innerHTML = `
                <h4>${mentor.mentor_name || 'Unknown Mentor'}</h4>
                <p>${bioSnippet}</p>
                <p><strong>Expertise:</strong> ${mentor.mentor_details.expertise || 'Not specified'}</p>
                {# Point 6: Removed mentor capacity from recommendations page #}
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
        if (recommendationsPageSection) recommendationsPageSection.hidden = false;

        document.querySelectorAll('.pick-mentor-btn').forEach(button => {
            button.addEventListener('click', (event) => {
                selectedMentorId = parseInt(event.currentTarget.dataset.mentorId, 10);
                if (modalMentorName) modalMentorName.textContent = event.currentTarget.dataset.mentorName;
                if (modalRequestMessage) modalRequestMessage.value = '';
                togglePickMentorModal();
            });
        });
    }

    // --- NEW: Logic for Recommendations Page Load ---
    const recommendationsPathSegments = window.location.pathname.split('/');
    if (recommendationsPathSegments[1] === 'mentees' && recommendationsPathSegments[3] === 'recommendations' && recommendationsPathSegments[2]) {
        const menteeIdFromPath = parseInt(recommendationsPathSegments[2], 10);
        const storedMenteeId = sessionStorage.getItem('menteeIdForRecommendations');
        const storedRecommendations = sessionStorage.getItem('initialRecommendations');
        const storedMessage = sessionStorage.getItem('recommendationsMessage');

        if (menteeIdFromPath === parseInt(storedMenteeId || 'NaN', 10) && storedRecommendations) {
            const recommendations = JSON.parse(storedRecommendations);
            displayRecommendations(recommendations, storedMessage || "Here are your top mentor recommendations:");
            
            // Set up "Proceed to Dashboard" button
            if (proceedToDashboardBtn) {
                proceedToDashboardBtn.addEventListener('click', () => {
                    // Clear recommendation data when proceeding
                    sessionStorage.removeItem('initialRecommendations');
                    sessionStorage.removeItem('menteeIdForRecommendations');
                    sessionStorage.removeItem('recommendationsMessage');
                    window.location.href = `/dashboard/mentee/${menteeIdFromPath}`;
                });
            }
        } else {
            if (recommendationsPageMessage) {
                recommendationsPageMessage.textContent = "No recent recommendations found. Please try finding new matches from your dashboard.";
                if (mentorRecommendationsDiv) mentorRecommendationsDiv.innerHTML = '';
            }
            if (proceedToDashboardBtn) {
                 proceedToDashboardBtn.addEventListener('click', () => {
                    sessionStorage.removeItem('initialRecommendations');
                    sessionStorage.removeItem('menteeIdForRecommendations');
                    sessionStorage.removeItem('recommendationsMessage');
                    window.location.href = `/dashboard/mentee/${menteeIdFromPath}`;
                });
            }
             console.warn('No valid recommendations found in session storage for this mentee ID. Consider redirecting.');
        }
        // Also clear on page unload to avoid stale data lingering across sessions
        window.addEventListener('beforeunload', () => {
            sessionStorage.removeItem('initialRecommendations');
            sessionStorage.removeItem('menteeIdForRecommendations');
            sessionStorage.removeItem('recommendationsMessage');
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
        hideFormMessage(mentorProfileMessage);

        try {
            const response = await fetch(`/api/mentors/${mentorId}`, { method: 'GET' });
            if (response.ok) {
                const mentor = await response.json();
                if (mentorDashboardName) mentorDashboardName.textContent = mentor.name;
                mentorDashboardProfileSummary.innerHTML = `
                    <h2>Your Profile</h2>
                    <p><strong>Name:</strong> ${mentor.name}</p>
                    <p><strong>Bio:</strong> ${mentor.bio}</p>
                    <p><strong>Expertise:</strong> ${mentor.expertise || 'Not specified'}</p>
                    <p><strong>Capacity:</strong> ${mentor.current_mentees} / ${mentor.capacity} active mentees</p>
                    <p><strong>Availability:</strong> ${mentor.availability?.hours_per_month || 'Not specified'} hours/month</p>
                    <p><strong>Preferences:</strong> Industries: ${(mentor.preferences?.industries || []).join(', ') || 'Any'}, Languages: ${(mentor.preferences?.languages || []).join(', ') || 'Any'}</p>
                    ${mentor.demographics ? `<p><strong>Demographics:</strong> Gender: ${mentor.demographics.gender || 'N/A'}, Ethnicity: ${mentor.demographics.ethnicity || 'N/A'}, Years Exp: ${mentor.demographics.years_experience || 'N/A'}</p>` : ''}
                `;
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
        mentorRequestsList.innerHTML = '<p aria-busy="true">Loading your requests...</p>';

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
            endpoint = `/api/mentor/${mentorId}/request/${requestId}/accept`; // Corrected API path
        } else if (action === 'reject') {
            endpoint = `/api/mentor/${mentorId}/request/${requestId}/reject`; // Corrected API path
            if (rejectionReason) {
                queryParams = `?rejection_reason=${encodeURIComponent(rejectionReason)}`;
            }
        } else if (action === 'complete') {
            endpoint = `/api/mentor/${mentorId}/request/${requestId}/complete`; // Corrected API path
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
                fetchMentorDetails(mentorId);
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
            if (rejectionReasonInput) rejectionReasonInput.value = '';
        });
    }


    // --- Mentee Dashboard Logic ---
    const menteePathSegments = window.location.pathname.split('/');
    if (menteePathSegments[1] === 'dashboard' && menteePathSegments[2] === 'mentee' && menteePathSegments[3]) {
        currentMenteeDashboardId = parseInt(menteePathSegments[3], 10);
        if (!isNaN(currentMenteeDashboardId)) {
            fetchMenteeDetails(currentMenteeDashboardId);
            fetchMenteeMentorshipRequests(currentMenteeDashboardId); // <--- CORRECTED CALL
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
            // CORRECTED: Use the /api/ endpoint for fetching JSON data
            const response = await fetch(`/api/mentees/${menteeId}`, { method: 'GET' }); // <--- FIX HERE
            if (response.ok) {
                const mentee = await response.json();
                if (menteeDashboardName) menteeDashboardName.textContent = mentee.name;
                menteeDashboardProfileSummary.innerHTML = `
                    <h2>Your Profile</h2>
                    <p><strong>Name:</strong> ${mentee.name}</p>
                    <p><strong>Bio:</strong> ${mentee.bio}</p>
                    <p><strong>Goals:</strong> ${mentee.goals || 'Not specified'}</p>
                    <p><strong>Mentorship Style:</strong> ${mentee.mentorship_style || 'Not specified'}</p>
                    <p><strong>Availability:</strong> ${mentee.availability?.hours_per_month || 'Not specified'} hours/month</p>
                    <p><strong>Preferences:</strong> Industries: ${(mentee.preferences?.industries || []).join(', ') || 'Any'}, Languages: ${(mentee.preferences?.languages || []).join(', ') || 'Any'}</p>
                `;
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
        menteeDashboardRequestsList.innerHTML = '<p aria-busy="true">Loading your requests...</p>';

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
            endpoint = `/api/mentee/${menteeId}/request/${requestId}/cancel`; // Corrected API path
        } else if (action === 'conclude') {
            endpoint = `/api/mentee/${menteeId}/request/${requestId}/conclude`; // Corrected API path
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
                const response = await authorizedFetch(`/api/mentees/${mentee_id}/feedback`, { // Corrected endpoint for feedback submission
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

    // --- Mentor Edit Page Logic ---
    const mentorEditForm = document.getElementById('mentor-edit-form');
    const mentorEditMessage = document.getElementById('mentor-edit-message');
    const mentorDeleteBtn = document.getElementById('mentor-delete-btn');

    if (mentorEditForm) {
        hideFormMessage(mentorEditMessage);
        // Ensure session known
        await checkSessionAndFetchUser();
        if (!isAuthenticated() || !currentUser?.mentor_profile_id) {
            window.location.href = '/login';
        } else {
            const mentorId = currentUser.mentor_profile_id;
            // Prefill
            try {
                const res = await authorizedFetch(`/api/mentors/${mentorId}`, { method: 'GET' });
                const mentor = await res.json();
                if (res.ok) {
                    document.getElementById('mentor_name').value = mentor.name || '';
                    document.getElementById('mentor_bio').value = mentor.bio || '';
                    document.getElementById('mentor_expertise').value = mentor.expertise || '';
                    document.getElementById('mentor_capacity').value = mentor.capacity || 1;
                    document.getElementById('mentor_hours_per_month').value = mentor.availability?.hours_per_month ?? '';
                    document.getElementById('mentor_preferences_industries').value = (mentor.preferences?.industries || []).join(', ');
                    document.getElementById('mentor_preferences_languages').value = (mentor.preferences?.languages || []).join(', ');
                } else {
                    showFormMessage(mentorEditMessage, `Failed to load mentor profile: ${mentor.detail || 'Unknown error.'}`, 'error');
                }
            } catch (e) {
                showFormMessage(mentorEditMessage, `Network error loading mentor profile: ${e.message}`, 'error');
            }
            // Submit
            mentorEditForm.addEventListener('submit', async (event) => {
                event.preventDefault();
                hideFormMessage(mentorEditMessage);

                const data = {
                    name: document.getElementById('mentor_name').value,
                    bio: document.getElementById('mentor_bio').value,
                    expertise: document.getElementById('mentor_expertise').value || null,
                    capacity: parseInt(document.getElementById('mentor_capacity').value, 10),
                    availability: (document.getElementById('mentor_hours_per_month').value !== '')
                        ? { hours_per_month: parseInt(document.getElementById('mentor_hours_per_month').value, 10) } : null,
                    preferences: (() => {
                        const industries = document.getElementById('mentor_preferences_industries').value.trim();
                        const languages = document.getElementById('mentor_preferences_languages').value.trim();
                        const pref = {};
                        if (industries) pref.industries = industries.split(',').map(s => s.trim()).filter(Boolean);
                        if (languages) pref.languages = languages.split(',').map(s => s.trim()).filter(Boolean);
                        return (pref.industries || pref.languages) ? pref : null;
                    })()
                };

                try {
                    const res = await authorizedFetch(`/mentors/${mentorId}`, {
                        method: 'PUT',
                        body: JSON.stringify(data)
                    });
                    const result = await res.json();
                    if (res.ok) {
                        showFormMessage(mentorEditMessage, 'Profile updated. Redirecting to dashboard...', 'success');
                        window.location.href = `/dashboard/mentor/${mentorId}`;
                    } else {
                        showFormMessage(mentorEditMessage, `Update failed: ${result.detail || 'Unknown error.'}`, 'error');
                    }
                } catch (e) {
                    showFormMessage(mentorEditMessage, `Network error updating profile: ${e.message}`, 'error');
                }
            });

            if (mentorDeleteBtn) {
                mentorDeleteBtn.addEventListener('click', async () => {
                    if (!confirm('Are you sure you want to delete your mentor profile? This cannot be undone.')) return;
                    try {
                        const res = await authorizedFetch(`/mentors/${mentorId}`, { method: 'DELETE' });
                        if (res.status === 204) {
                            showFormMessage(mentorEditMessage, 'Profile deleted.', 'success');
                            window.location.href = '/get-started';
                        } else {
                            const result = await res.json();
                            showFormMessage(mentorEditMessage, `Delete failed: ${result.detail || 'Unknown error.'}`, 'error');
                        }
                    } catch (e) {
                        showFormMessage(mentorEditMessage, `Network error deleting profile: ${e.message}`, 'error');
                    }
                });
            }
        }
    }

    // --- Mentee Edit Page Logic ---
    const menteeEditForm = document.getElementById('mentee-edit-form');
    const menteeEditMessage = document.getElementById('mentee-edit-message');
    const menteeDeleteBtn = document.getElementById('mentee-delete-btn');

    if (menteeEditForm) {
        hideFormMessage(menteeEditMessage);
        await checkSessionAndFetchUser();
        if (!isAuthenticated() || !currentUser?.mentee_profile_id) {
            window.location.href = '/login';
        } else {
            const menteeId = currentUser.mentee_profile_id;
            // Prefill
            try {
                const res = await authorizedFetch(`/api/mentees/${menteeId}`, { method: 'GET' });
                const mentee = await res.json();
                if (res.ok) {
                    document.getElementById('mentee_name').value = mentee.name || '';
                    document.getElementById('mentee_bio').value = mentee.bio || '';
                    document.getElementById('mentee_goals').value = mentee.goals || '';
                    document.getElementById('mentee_style').value = mentee.mentorship_style || '';
                    document.getElementById('mentee_hours_per_month').value = mentee.availability?.hours_per_month ?? '';
                    document.getElementById('mentee_preferences_industries').value = (mentee.preferences?.industries || []).join(', ');
                    document.getElementById('mentee_preferences_languages').value = (mentee.preferences?.languages || []).join(', ');
                } else {
                    showFormMessage(menteeEditMessage, `Failed to load mentee profile: ${mentee.detail || 'Unknown error.'}`, 'error');
                }
            } catch (e) {
                showFormMessage(menteeEditMessage, `Network error loading mentee profile: ${e.message}`, 'error');
            }
            // Submit
            menteeEditForm.addEventListener('submit', async (event) => {
                event.preventDefault();
                hideFormMessage(menteeEditMessage);

                const data = {
                    name: document.getElementById('mentee_name').value,
                    bio: document.getElementById('mentee_bio').value,
                    goals: document.getElementById('mentee_goals').value || null,
                    mentorship_style: document.getElementById('mentee_style').value || null,
                    availability: (document.getElementById('mentee_hours_per_month').value !== '')
                        ? { hours_per_month: parseInt(document.getElementById('mentee_hours_per_month').value, 10) } : null,
                    preferences: (() => {
                        const industries = document.getElementById('mentee_preferences_industries').value.trim();
                        const languages = document.getElementById('mentee_preferences_languages').value.trim();
                        const pref = {};
                        if (industries) pref.industries = industries.split(',').map(s => s.trim()).filter(Boolean);
                        if (languages) pref.languages = languages.split(',').map(s => s.trim()).filter(Boolean);
                        return (pref.industries || pref.languages) ? pref : null;
                    })()
                };

                try {
                    const res = await authorizedFetch(`/mentees/${menteeId}`, {
                        method: 'PUT',
                        body: JSON.stringify(data)
                    });
                    const result = await res.json();
                    if (res.ok) {
                        showFormMessage(menteeEditMessage, 'Profile updated. Redirecting to dashboard...', 'success');
                        window.location.href = `/dashboard/mentee/${menteeId}`;
                    } else {
                        showFormMessage(menteeEditMessage, `Update failed: ${result.detail || 'Unknown error.'}`, 'error');
                    }
                } catch (e) {
                    showFormMessage(menteeEditMessage, `Network error updating profile: ${e.message}`, 'error');
                }
            });

            if (menteeDeleteBtn) {
                menteeDeleteBtn.addEventListener('click', async () => {
                    if (!confirm('Are you sure you want to delete your mentee profile? This cannot be undone.')) return;
                    try {
                        const res = await authorizedFetch(`/mentees/${menteeId}`, { method: 'DELETE' });
                        if (res.status === 204) {
                            showFormMessage(menteeEditMessage, 'Profile deleted.', 'success');
                            window.location.href = '/get-started';
                        } else {
                            const result = await res.json();
                            showFormMessage(menteeEditMessage, `Delete failed: ${result.detail || 'Unknown error.'}`, 'error');
                        }
                    } catch (e) {
                        showFormMessage(menteeEditMessage, `Network error deleting profile: ${e.message}`, 'error');
                    }
                });
            }
        }
    }



    // --- Initial setup on page load ---
    checkSessionAndFetchUser();
});