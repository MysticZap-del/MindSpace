document.addEventListener('DOMContentLoaded', () => {
    // --- Get DOM Elements ---
    const loadingState = document.getElementById('loading-state');
    const errorState = document.getElementById('error-state');
    const profileContent = document.getElementById('profile-content');

    // Profile elements
    const profilePicturePreview = document.getElementById('profile-picture-preview');
    const profilePictureUpload = document.getElementById('profile-picture-upload');
    const profilePictureEditDiv = document.querySelector('.edit-mode-element.text-center');
    const nameView = document.getElementById('profile-name-view');
    const ageView = document.getElementById('profile-age-view');
    const weightView = document.getElementById('profile-weight-view');
    const nameEdit = document.getElementById('profile-name-edit');
    const ageEdit = document.getElementById('profile-age-edit');
    const weightEdit = document.getElementById('profile-weight-edit');
    const editButton = document.getElementById('edit-profile-button');
    const saveButton = document.getElementById('save-changes-button');
    const cancelButton = document.getElementById('cancel-button');
    const viewModeElements = document.querySelectorAll('.view-mode-element');
    const editModeElements = document.querySelectorAll('.edit-mode-element');

    // Chart Elements
    const chartLoadingState = document.getElementById('chart-loading-state');
    const chartErrorState = document.getElementById('chart-error-state');
    const moodChartCanvas = document.getElementById('moodChart');
    let moodChartInstance = null;

    // Quote Elements
    const quoteLoadingState = document.getElementById('quote-loading-state');
    const quoteErrorState = document.getElementById('quote-error-state');
    const quoteContent = document.getElementById('quote-content');
    const quoteTextElement = document.getElementById('daily-quote-text');
    const quoteAuthorElement = document.getElementById('daily-quote-author');


    let currentProfileData = {};
    let selectedFile = null;

    // --- Functions ---

    function showError(message, element = errorState) {
        element.textContent = `Error: ${message}`;
        element.classList.remove('hidden');
        // Hide corresponding loading/content
        if (element === errorState) {
            loadingState.classList.add('hidden');
            profileContent.classList.add('hidden');
        } else if (element === chartErrorState) {
            chartLoadingState.classList.add('hidden');
            moodChartCanvas.style.display = 'none';
        } else if (element === quoteErrorState) {
            quoteLoadingState.classList.add('hidden');
            quoteContent.classList.add('hidden');
        }
    }

    function showProfileContent() {
        loadingState.classList.add('hidden');
        errorState.classList.add('hidden');
        profileContent.classList.remove('hidden');
    }

    function updateProfileView(data) {
        currentProfileData = data;
        nameView.textContent = data.name || 'N/A';
        ageView.textContent = data.age || 'N/A';
        weightView.textContent = data.weight ? `${data.weight} kg` : 'N/A';

        if (data.picture_filename) {
            profilePicturePreview.src = `/static/uploads/${data.picture_filename}?t=${new Date().getTime()}`;
        } else {
            // Use a placeholder suitable for dark mode if needed, or keep the current one
            profilePicturePreview.src = '/static/images/placeholder.png';
        }

        nameEdit.value = data.name || '';
        ageEdit.value = data.age || '';
        weightEdit.value = data.weight || '';
        selectedFile = null;
        profilePictureUpload.value = null;
    }

    function toggleEditMode(isEditing) {
        console.log('Toggling edit mode:', isEditing);
        viewModeElements.forEach(el => {
            isEditing ? el.classList.add('hidden') : el.classList.remove('hidden');
        });
        editModeElements.forEach(el => {
            isEditing ? el.classList.remove('hidden') : el.classList.add('hidden');
        });

        if (!isEditing) {
             profilePicturePreview.src = currentProfileData.picture_filename
                ? `/static/uploads/${currentProfileData.picture_filename}?t=${new Date().getTime()}`
                : '/static/images/placeholder.png';
             selectedFile = null;
             profilePictureUpload.value = null;
        }
    }

    async function fetchProfileData() {
        try {
            loadingState.classList.remove('hidden');
            errorState.classList.add('hidden');
            profileContent.classList.add('hidden');

            const response = await fetch('/api/profile');
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: response.statusText }));
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            updateProfileView(data);
            showProfileContent();
            toggleEditMode(false);
        } catch (error) {
            console.error('Failed to fetch profile data:', error);
            showError(`Could not load profile. ${error.message}`);
        }
    }

     async function saveProfileData() {
        saveButton.disabled = true; saveButton.textContent = 'Saving...'; cancelButton.disabled = true;
        const updatedData = {
            name: nameEdit.value.trim(),
            age: ageEdit.value ? parseInt(ageEdit.value, 10) : null,
            weight: weightEdit.value ? parseFloat(weightEdit.value) : null,
        };
         if ((updatedData.age !== null && isNaN(updatedData.age)) || (updatedData.weight !== null && isNaN(updatedData.weight)) ) {
             alert('Invalid age or weight entered.');
             saveButton.disabled = false; saveButton.textContent = 'Save'; cancelButton.disabled = false; return;
        }
        try {
            const textResponse = await fetch('/api/profile', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(updatedData) });
            if (!textResponse.ok) {
                const errorData = await textResponse.json().catch(() => ({ detail: textResponse.statusText }));
                throw new Error(`Failed to save profile data: ${errorData.detail || textResponse.statusText}`);
            }
            const textResult = await textResponse.json();
            console.log('Profile text data saved successfully:', textResult);
            currentProfileData = { ...currentProfileData, ...textResult.profile };
            if (selectedFile) { await saveProfilePicture(); }
            await fetchProfileData(); // Refetch to update view and ensure view mode
        } catch (error) {
            console.error('Error saving profile:', error);
            alert(`Error saving profile: ${error.message}`);
            saveButton.disabled = false; saveButton.textContent = 'Save'; cancelButton.disabled = false;
        }
    }

    async function saveProfilePicture() {
         if (!selectedFile) return;
         const formData = new FormData(); formData.append('profile_picture', selectedFile);
         saveButton.textContent = 'Uploading...';
         try {
             const response = await fetch('/api/profile/picture', { method: 'POST', body: formData });
             if (!response.ok) {
                 const errorData = await response.json().catch(() => ({ detail: response.statusText }));
                 throw new Error(`Failed to upload picture: ${errorData.detail || response.statusText}`);
             }
             const result = await response.json();
             console.log('Picture uploaded successfully:', result);
             currentProfileData.picture_filename = result.filename;
             selectedFile = null; profilePictureUpload.value = null;
         } catch (error) {
              console.error('Error uploading picture:', error); throw error;
         }
    }

    // --- Chart Function ---
    async function fetchAndDisplayMoodChart() {
        chartLoadingState.classList.remove('hidden');
        chartErrorState.classList.add('hidden');
        moodChartCanvas.style.display = 'none';

        try {
            const response = await fetch('/api/mood_history?days=7');
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: response.statusText }));
                throw new Error(errorData.error || `HTTP error! Status: ${response.status}`);
            }
            const data = await response.json();

            if (!data || !data.labels || !data.scores) {
                throw new Error("Invalid data format received from server.");
            }

            // Check if data exists (real or dummy)
            const hasAnyData = data.scores.length > 0; // Check if scores array is not empty
            if (!hasAnyData) {
                 chartLoadingState.textContent = "Could not load chart data.";
                 chartErrorState.classList.add('hidden');
                 moodChartCanvas.style.display = 'none';
                 return;
            }

            chartLoadingState.classList.add('hidden');
            moodChartCanvas.style.display = 'block';

            const ctx = moodChartCanvas.getContext('2d');
            if (moodChartInstance) { moodChartInstance.destroy(); }

            // Define colors for dark mode
            const purpleColor = 'rgb(168, 85, 247)'; // purple-500
            const purpleBgColor = 'rgba(168, 85, 247, 0.2)';
            const gridColor = 'rgba(107, 114, 128, 0.3)'; // gray-500 with alpha
            const textColor = 'rgb(209, 213, 219)'; // gray-300

            moodChartInstance = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.labels,
                    datasets: [{
                        label: 'Average Daily Mood Score',
                        data: data.scores,
                        borderColor: purpleColor, // Purple line
                        backgroundColor: purpleBgColor, // Purple area fill
                        tension: 0.1,
                        fill: true,
                        spanGaps: true, // Connect lines across null/missing data points
                        pointBackgroundColor: purpleColor, // Make points visible
                        pointRadius: 3, // Adjust point size
                        pointHoverRadius: 5,
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: false,
                            min: -1, max: 1,
                            title: { display: true, text: 'Mood Score (-1 to +1)', color: textColor },
                            ticks: { color: textColor }, // Y-axis label colors
                            grid: { color: gridColor } // Y-axis grid lines
                        },
                        x: {
                             type: 'time',
                             time: { unit: 'day', tooltipFormat: 'MMM d, yyyy', displayFormats: { day: 'MMM d' } },
                             title: { display: true, text: 'Date', color: textColor },
                             ticks: { color: textColor }, // X-axis label colors
                             grid: { color: gridColor } // X-axis grid lines
                        }
                    },
                     plugins: {
                        legend: { labels: { color: textColor } }, // Legend text color
                        tooltip: {
                            titleColor: textColor, // Tooltip title color
                            bodyColor: textColor, // Tooltip body color
                            backgroundColor: 'rgba(31, 41, 55, 0.9)', // gray-800 bg with alpha
                            borderColor: 'rgba(107, 114, 128, 0.5)',
                            borderWidth: 1,
                            callbacks: {
                                label: function(context) {
                                    let label = context.dataset.label || '';
                                    if (label) { label += ': '; }
                                    if (context.parsed.y !== null) {
                                        let score = context.parsed.y;
                                        let moodInterpretation = "Neutral";
                                        if (score > 0.35) moodInterpretation = "Positive";
                                        else if (score < -0.35) moodInterpretation = "Negative";
                                        label += `${score.toFixed(2)} (${moodInterpretation})`;
                                    } else { label += 'No Data'; }
                                    return label;
                                }
                            }
                        }
                    }
                }
            });

        } catch (error) {
            console.error('Failed to fetch or display mood chart:', error);
            showError(`Could not load mood chart: ${error.message}`, chartErrorState);
        }
    }

    // --- NEW Quote Function ---
    async function fetchAndDisplayDailyQuote() {
        quoteLoadingState.classList.remove('hidden');
        quoteErrorState.classList.add('hidden');
        quoteContent.classList.add('hidden');
        quoteAuthorElement.classList.add('hidden'); // Hide author initially

        try {
            const response = await fetch('/api/daily_quote');
            if (!response.ok) {
                 const errorData = await response.json().catch(() => ({ detail: response.statusText }));
                 throw new Error(errorData.error || `HTTP error! Status: ${response.status}`);
            }
            const data = await response.json();

            if (!data || !data.quote) {
                 throw new Error("Invalid quote data received.");
            }

            // Parse quote and author (assuming format "Quote text" - Author Name)
            const quoteParts = data.quote.split(' - ');
            const text = quoteParts[0];
            const author = quoteParts.length > 1 ? quoteParts[1] : null;

            quoteTextElement.textContent = text;
            if (author) {
                quoteAuthorElement.textContent = `- ${author}`;
                quoteAuthorElement.classList.remove('hidden'); // Show author if present
            }

            quoteLoadingState.classList.add('hidden');
            quoteContent.classList.remove('hidden'); // Show the blockquote

        } catch (error) {
             console.error('Failed to fetch or display daily quote:', error);
             showError(`Could not load daily quote: ${error.message}`, quoteErrorState);
        }

    }

    // --- Event Listeners ---
    editButton.addEventListener('click', () => {
        console.log('Edit button clicked - current data:', currentProfileData);
        nameEdit.value = currentProfileData.name || '';
        ageEdit.value = currentProfileData.age || '';
        weightEdit.value = currentProfileData.weight || '';
        selectedFile = null; profilePictureUpload.value = null;
        toggleEditMode(true);
    });

    cancelButton.addEventListener('click', () => {
        console.log('Cancel button clicked');
        toggleEditMode(false);
    });

    saveButton.addEventListener('click', saveProfileData);

    profilePictureUpload.addEventListener('change', (event) => {
        const file = event.target.files[0];
        if (file) {
            if (file.size > 2 * 1024 * 1024) { alert('File is too large (Max 2MB).'); profilePictureUpload.value = null; selectedFile = null; return; }
            if (!['image/jpeg', 'image/png', 'image/gif'].includes(file.type)) { alert('Invalid file type (JPG, PNG, GIF only).'); profilePictureUpload.value = null; selectedFile = null; return; }
            selectedFile = file;
            const reader = new FileReader();
            reader.onload = (e) => { profilePicturePreview.src = e.target.result; };
            reader.onerror = (e) => { console.error("FileReader error:", e); alert("Error reading file preview."); selectedFile = null; profilePictureUpload.value = null; };
            reader.readAsDataURL(file);
        } else { selectedFile = null; }
    });

    // --- Initial Load ---
    fetchProfileData();
    fetchAndDisplayMoodChart();
    fetchAndDisplayDailyQuote(); // Fetch quote on load

});
