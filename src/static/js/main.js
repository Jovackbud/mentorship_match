document.addEventListener('DOMContentLoaded', () => {
    // --- Common Elements & Helpers ---
    const mentorSignupForm = document.getElementById('mentor-signup-form');
    const menteeSignupForm = document.getElementById('mentee-signup-form');
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
    const mentorDashboardRequestsSection = document.getElementById('mentorship-requests-section'); // Renamed for clarity, was 'mentorDashboardPage'
    const mentorRequestsList = document.getElementById('mentorship-requests-list');
    const requestsMessage = document.getElementById('requests-message');
    const rejectModal = document.getElementById('reject-modal');
    const rejectionReasonInput = document.getElementById('rejection-reason');
    const confirmRejectBtn = document.getElementById('confirm-reject-btn');

    // NEW: Mentee Dashboard Specifics
    const menteeDashboardRequestsSection = document.getElementById('mentee-mentorship-requests-list');
    const menteeRequestsMessage = document.getElementById('mentee-requests-message');
    
    let currentMenteeId = null; // Stored from signup form
    let selectedMentorId = null; // Stored from mentee recommendations pick
    let currentMentorDashboardId = null; // Stored from mentor dashboard URL
    let currentMenteeDashboardId = null; // NEW: Stored from mentee dashboard URL
    let currentRequestIdForAction = null; // Stored when modal/action is initiated

    // Helper function to show messages for a specific message element
    function showFormMessage(messageElement, message, type) {
        if (messageElement) {
            messageElement.innerHTML = message; // Use innerHTML for links
            messageElement.setAttribute('data-variant', type);
            messageElement.style.display = 'block';
        }
    }

    // Helper function to hide messages for a specific message element
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
        if (event) event.preventDefault(); // Prevent default link behavior if an event object is passed
        if (dialogElement.hasAttribute('open')) {
            dialogElement.removeAttribute('open');
            document.body.style.overflow = '';
        } else {
            dialogElement.setAttribute('open', '');
            document.body.style.overflow = 'hidden';
        }
    }

    // Specific modal toggles for clarity and global access
    window.togglePickMentorModal = (event) => toggleDialog(pickMentorModal, event);
    window.toggleRejectModal = (event) => toggleDialog(rejectModal, event);


    // --- Mentor Signup Form Logic (Existing, but added dashboard link) ---
    if (mentorSignupForm) {
        hideFormMessage(mentorResponseMessage);

        mentorSignupForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            hideFormMessage(mentorResponseMessage);

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
                const response = await fetch('/mentors/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
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

    // --- Mentee Signup Form Logic (Existing, but added dashboard link) ---
    if (menteeSignupForm) {
        hideFormMessage(menteeResponseMessage);

        menteeSignupForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            hideFormMessage(menteeResponseMessage);
            recommendationsSection.style.display = 'none';
            mentorRecommendationsDiv.innerHTML = '';

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
                const response = await fetch('/match/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
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

    // --- Logic for Confirming Mentor Pick in Modal ---
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
                const response = await fetch(url + queryParams, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
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

    // --- Mentor Dashboard Logic (Existing) ---
    const mentorPathSegments = window.location.pathname.split('/');
    if (mentorPathSegments[1] === 'dashboard' && mentorPathSegments[2] === 'mentor' && mentorPathSegments[3]) {
        currentMentorDashboardId = parseInt(mentorPathSegments[3], 10);
        if (!isNaN(currentMentorDashboardId)) {
            // fetchMentorDetails(currentMentorDashboardId); // This API endpoint doesn't exist yet, uncomment when it does.
            fetchMentorshipRequests(currentMentorDashboardId);
        } else {
            showFormMessage(requestsMessage, 'Invalid mentor ID in URL.', 'error');
        }
    }

    // Placeholder for fetching mentor details - needs API endpoint: GET /mentors/{id}
    async function fetchMentorDetails(mentorId) {
        // This function would fetch detailed mentor profile from an API endpoint like /mentors/{mentor_id}
        // For now, it's a placeholder.
        const profileSummaryDiv = document.getElementById('mentor-profile-summary');
        if (profileSummaryDiv) {
             // You'd make an API call here and populate the fields
            // For now, it just shows the ID from the template.
        }
    }


    async function fetchMentorshipRequests(mentorId) {
        hideFormMessage(requestsMessage);
        mentorRequestsList.innerHTML = '<p>Loading your requests...</p>';

        try {
            const response = await fetch(`/api/mentors/${mentorId}/requests`);
            const requests = await response.json();

            if (response.ok) {
                if (requests.length === 0) {
                    mentorRequestsList.innerHTML = '<p>No mentorship requests found.</p>';
                } else {
                    renderMentorMentorshipRequests(requests); // Changed function name
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

    function renderMentorMentorshipRequests(requests) { // Changed function name
        mentorRequestsList.innerHTML = '';

        let pendingRequests = requests.filter(r => r.status === 'PENDING');
        let activeRequests = requests.filter(r => r.status === 'ACCEPTED');
        let historicalRequests = requests.filter(r => ['REJECTED', 'CANCELLED', 'COMPLETED'].includes(r.status));

        const sortByRequestDateDesc = (a, b) => new Date(b.request_date).getTime() - new Date(a.request_date).getTime();
        pendingRequests.sort(sortByRequestDateDesc);
        activeRequests.sort(sortByRequestDateDesc);
        historicalRequests.sort(sortByRequestDateDesc);

        function createRequestCategorySection(title, requestsArray, type, isMentorView = true) {
            if (requestsArray.length === 0) return null;

            const categorySection = document.createElement('section');
            categorySection.className = `request-category ${type}-requests`;
            
            const header = document.createElement('h3');
            header.textContent = title;
            categorySection.appendChild(header);

            const cardsContainer = document.createElement('div');
            cardsContainer.className = 'cards-container';
            requestsArray.forEach(request => {
                cardsContainer.appendChild(createMentorRequestCard(request, type)); // Use mentor-specific card
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

        attachMentorRequestButtonListeners(); // Changed function name
    }

    // Renamed function to be mentor-specific
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
        } // No actions for CANCELLED or COMPLETED on mentor side

        card.innerHTML = `
            ${cardContent}
            <footer>${footerButtons}</footer>
        `;
        return card;
    }

    // Renamed function to be mentor-specific
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
            const response = await fetch(endpoint + queryParams, {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                },
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


    // --- NEW: Mentee Dashboard Logic ---
    const menteePathSegments = window.location.pathname.split('/');
    if (menteePathSegments[1] === 'dashboard' && menteePathSegments[2] === 'mentee' && menteePathSegments[3]) {
        currentMenteeDashboardId = parseInt(menteePathSegments[3], 10);
        if (!isNaN(currentMenteeDashboardId)) {
            // fetchMenteeDetails(currentMenteeDashboardId); // This API endpoint doesn't exist yet
            fetchMenteeMentorshipRequests(currentMenteeDashboardId);
        } else {
            showFormMessage(menteeRequestsMessage, 'Invalid mentee ID in URL.', 'error');
        }
    }

    // Placeholder for fetching mentee details - needs API endpoint: GET /mentees/{id}
    async function fetchMenteeDetails(menteeId) {
        // This function would fetch detailed mentee profile from an API endpoint like /mentees/{mentee_id}
        // For now, it's a placeholder.
        const profileSummaryDiv = document.getElementById('mentee-profile-summary');
        if (profileSummaryDiv) {
             // You'd make an API call here and populate the fields
            // For now, it just shows the ID from the template.
        }
    }

    async function fetchMenteeMentorshipRequests(menteeId) {
        hideFormMessage(menteeRequestsMessage);
        menteeDashboardRequestsSection.innerHTML = '<p>Loading your requests...</p>';

        try {
            const response = await fetch(`/api/mentees/${menteeId}/requests`);
            const requests = await response.json();

            if (response.ok) {
                if (requests.length === 0) {
                    menteeDashboardRequestsSection.innerHTML = '<p>No mentorship requests found.</p>';
                } else {
                    renderMenteeMentorshipRequests(requests);
                }
            } else {
                showFormMessage(menteeRequestsMessage, `Error fetching requests: ${requests.detail || 'Unknown error.'}`, 'error');
                menteeDashboardRequestsSection.innerHTML = '<p>Failed to load requests.</p>';
                console.error('API Error fetching mentee requests:', requests);
            }
        } catch (error) {
            showFormMessage(menteeRequestsMessage, 'Network error or unable to connect to server.', 'error');
            menteeDashboardRequestsSection.innerHTML = '<p>Failed to load requests due to network error.</p>';
            console.error('Fetch error fetching mentee requests:', error);
        }
    }

    function renderMenteeMentorshipRequests(requests) {
        menteeDashboardRequestsSection.innerHTML = '';

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
                cardsContainer.appendChild(createMenteeRequestCard(request, type)); // Use mentee-specific card
            });
            categorySection.appendChild(cardsContainer);
            return categorySection;
        }

        const pendingSection = createRequestCategorySection('Pending Requests', pendingRequests, 'pending');
        if (pendingSection) menteeDashboardRequestsSection.appendChild(pendingSection);

        const activeSection = createRequestCategorySection('Active Mentorships', activeRequests, 'active');
        if (activeSection) menteeDashboardRequestsSection.appendChild(activeSection);

        const historicalSection = createRequestCategorySection('Historical Journeys', historicalRequests, 'historical');
        if (historicalSection) menteeDashboardRequestsSection.appendChild(historicalSection);

        if (pendingRequests.length === 0 && activeRequests.length === 0 && historicalRequests.length === 0) {
            menteeDashboardRequestsSection.innerHTML = '<p>No mentorship requests found.</p>';
        }

        attachMenteeRequestButtonListeners();
    }

    // NEW: Function to create a mentee-specific request card
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
        } // No actions for REJECTED, CANCELLED, COMPLETED on mentee side (just view)

        card.innerHTML = `
            ${cardContent}
            <footer>${footerButtons}</footer>
        `;
        return card;
    }

    // NEW: Function to attach listeners for mentee action buttons
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

    // NEW: Function to perform mentee actions (cancel, conclude)
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
            const response = await fetch(endpoint, {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                },
            });
            const result = await response.json();

            if (response.ok) {
                showFormMessage(menteeRequestsMessage, `Request ${requestId} ${action.toUpperCase()}ED successfully!`, 'success');
                fetchMenteeMentorshipRequests(menteeId); // Refresh the list
            } else {
                showFormMessage(menteeRequestsMessage, `Error performing ${action} for request ${requestId}: ${result.detail || 'Unknown error.'}`, 'error');
                console.error(`API Error for ${action} request ${requestId}:`, result);
            }
        } catch (error) {
            showFormMessage(menteeRequestsMessage, `Network error during ${action} action for request ${requestId}.`, 'error');
            console.error(`Fetch error for ${action} request ${requestId}:`, error);
        }
    }

});