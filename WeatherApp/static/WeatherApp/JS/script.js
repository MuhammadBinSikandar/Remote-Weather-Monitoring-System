function showTabDuration(tabId) {
    // Hide all duration tabs
    const durationTabs = document.querySelectorAll('.duration_tab');
    durationTabs.forEach(tab => tab.classList.remove('Dactive'));

    // Show the selected duration tab
    document.getElementById(tabId).classList.add('Dactive');

    // Remove active class from all duration buttons
    const durationButtons = document.querySelectorAll('.Duration-tabs');
    durationButtons.forEach(button => button.classList.remove('Dactive'));

    // Add active class to the clicked duration button
    document.querySelector(`.Duration-tabs[onclick="showTabDuration('${tabId}')"]`).classList.add('Dactive');
}

function showTab(tabId) {
    // Hide all tab contents
    const tabContents = document.querySelectorAll('.tab-content');
    tabContents.forEach(content => content.style.display = 'none');

    // Show the selected tab content
    document.getElementById(tabId).style.display = 'block';

    // Remove active class from all tabs
    const tabs = document.querySelectorAll('.tab');
    tabs.forEach(tab => tab.classList.remove('active'));

    // Add active class to the clicked tab
    document.querySelector(`.tab[onclick="showTab('${tabId}')"]`).classList.add('active');
}