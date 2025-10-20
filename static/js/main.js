// Main JavaScript for Committee Management System

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);

    // Form validation
    var forms = document.querySelectorAll('.needs-validation');
    Array.prototype.slice.call(forms).forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });

    // Loading states for buttons
    document.querySelectorAll('form').forEach(function(form) {
        form.addEventListener('submit', function() {
            var submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.classList.add('loading');
                submitBtn.disabled = true;
                var originalText = submitBtn.innerHTML;
                submitBtn.innerHTML = '<i class="bi bi-hourglass-split me-1"></i>מעבד...';
                
                // Re-enable after 10 seconds as fallback
                setTimeout(function() {
                    submitBtn.classList.remove('loading');
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalText;
                }, 10000);
            }
        });
    });

    // Dynamic route filtering in events form
    var hativaSelect = document.getElementById('hativa_select');
    var maslulSelect = document.getElementById('maslul_id');
    
    if (hativaSelect && maslulSelect) {
        hativaSelect.addEventListener('change', function() {
            var selectedHativa = this.value;
            var options = maslulSelect.querySelectorAll('option');
            
            options.forEach(function(option) {
                if (option.value === '') {
                    option.style.display = 'block';
                    return;
                }
                
                var hativa = option.getAttribute('data-hativa');
                if (selectedHativa === '' || hativa === selectedHativa) {
                    option.style.display = 'block';
                } else {
                    option.style.display = 'none';
                }
            });
            
            // Reset selection if current selection is not visible
            if (maslulSelect.value) {
                var currentOption = maslulSelect.querySelector('option[value="' + maslulSelect.value + '"]');
                if (currentOption && currentOption.style.display === 'none') {
                    maslulSelect.value = '';
                }
            }
        });
    }

    // Date validation for exception dates - REMOVED
    // Allowing both past and future dates for exception dates
    // Users can now add historical dates (holidays, etc.)

    // Committee date suggestions with AJAX
    function loadCommitteeSuggestions(committeeId) {
        if (!committeeId) return;
        
        var suggestionsContainer = document.getElementById('suggestions-container');
        if (!suggestionsContainer) return;
        
        suggestionsContainer.innerHTML = '<div class="text-center"><i class="bi bi-hourglass-split"></i> טוען הצעות...</div>';
        
        fetch('/api/committee_suggestions/' + committeeId)
            .then(response => response.json())
            .then(data => {
                displaySuggestions(data);
            })
            .catch(error => {
                console.error('Error:', error);
                suggestionsContainer.innerHTML = '<div class="alert alert-danger">שגיאה בטעינת ההצעות</div>';
            });
    }

    function displaySuggestions(suggestions) {
        var container = document.getElementById('suggestions-container');
        if (!container) return;
        
        if (suggestions.length === 0) {
            container.innerHTML = '<div class="alert alert-info">לא נמצאו תאריכים זמינים</div>';
            return;
        }
        
        var html = '<div class="row">';
        suggestions.forEach(function(suggestion) {
            var statusClass = suggestion.can_schedule ? 'success' : 'warning';
            var statusIcon = suggestion.can_schedule ? 'check-circle' : 'exclamation-triangle';
            var statusText = suggestion.can_schedule ? 'זמין' : 'לא זמין';
            
            html += `
                <div class="col-md-6 mb-3">
                    <div class="card border-${statusClass}">
                        <div class="card-body">
                            <h6 class="card-title">
                                <i class="bi bi-calendar me-1"></i>
                                ${suggestion.date}
                            </h6>
                            <p class="card-text">
                                <span class="badge bg-${statusClass}">
                                    <i class="bi bi-${statusIcon} me-1"></i>${statusText}
                                </span>
                            </p>
                            ${!suggestion.can_schedule ? `<small class="text-muted">${suggestion.reason}</small>` : ''}
                        </div>
                    </div>
                </div>
            `;
        });
        html += '</div>';
        
        container.innerHTML = html;
    }

    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(function(anchor) {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            var target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + N for new items
        if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
            e.preventDefault();
            var addButton = document.querySelector('[data-bs-toggle="modal"]');
            if (addButton) {
                addButton.click();
            }
        }
        
        // Escape to close modals
        if (e.key === 'Escape') {
            var openModal = document.querySelector('.modal.show');
            if (openModal) {
                var modal = bootstrap.Modal.getInstance(openModal);
                if (modal) {
                    modal.hide();
                }
            }
        }
    });

    // Auto-refresh for real-time updates (every 5 minutes)
    if (window.location.pathname.includes('schedule') || window.location.pathname.includes('suggest')) {
        setInterval(function() {
            // Only refresh if user is active (not idle)
            if (document.hasFocus()) {
                location.reload();
            }
        }, 300000); // 5 minutes
    }

    // Print functionality
    window.printPage = function() {
        window.print();
    };

    // Export functionality (basic CSV export for tables)
    window.exportTableToCSV = function(tableId, filename) {
        var table = document.getElementById(tableId);
        if (!table) return;
        
        var csv = [];
        var rows = table.querySelectorAll('tr');
        
        for (var i = 0; i < rows.length; i++) {
            var row = [], cols = rows[i].querySelectorAll('td, th');
            
            for (var j = 0; j < cols.length; j++) {
                var cellText = cols[j].innerText.replace(/"/g, '""');
                row.push('"' + cellText + '"');
            }
            
            csv.push(row.join(','));
        }
        
        // Download CSV file
        var csvFile = new Blob([csv.join('\n')], { type: 'text/csv' });
        var downloadLink = document.createElement('a');
        downloadLink.download = filename || 'export.csv';
        downloadLink.href = window.URL.createObjectURL(csvFile);
        downloadLink.style.display = 'none';
        document.body.appendChild(downloadLink);
        downloadLink.click();
        document.body.removeChild(downloadLink);
    };

    // Theme toggle (if implemented)
    var themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', function() {
            document.body.classList.toggle('dark-theme');
            var isDark = document.body.classList.contains('dark-theme');
            localStorage.setItem('theme', isDark ? 'dark' : 'light');
        });
        
        // Load saved theme
        var savedTheme = localStorage.getItem('theme');
        if (savedTheme === 'dark') {
            document.body.classList.add('dark-theme');
        }
    }

    // Initialize any additional components
    initializeComponents();
});

function initializeComponents() {
    // Initialize any custom components here
    
    // Example: Initialize date pickers with Hebrew locale
    var dateInputs = document.querySelectorAll('input[type="date"]');
    dateInputs.forEach(function(input) {
        // Add Hebrew day names as data attributes for custom formatting
        input.setAttribute('data-locale', 'he-IL');
    });
    
    // Initialize progress indicators
    var progressRings = document.querySelectorAll('.progress-ring-circle');
    progressRings.forEach(function(ring) {
        var percent = ring.getAttribute('data-percent') || 0;
        var radius = ring.r.baseVal.value;
        var circumference = radius * 2 * Math.PI;
        var offset = circumference - (percent / 100) * circumference;
        
        ring.style.strokeDasharray = circumference;
        ring.style.strokeDashoffset = offset;
    });
}

// Utility functions
function formatDate(dateString, locale = 'he-IL') {
    var date = new Date(dateString);
    return date.toLocaleDateString(locale, {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
}

function showNotification(message, type = 'info') {
    var alertClass = type === 'error' ? 'alert-danger' : 'alert-success';
    var iconClass = type === 'error' ? 'exclamation-triangle' : 'check-circle';
    
    var alertHtml = `
        <div class="alert ${alertClass} alert-dismissible fade show" role="alert">
            <i class="bi bi-${iconClass} me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    var container = document.querySelector('.container');
    if (container) {
        container.insertAdjacentHTML('afterbegin', alertHtml);
        
        // Auto-hide after 5 seconds
        setTimeout(function() {
            var alert = container.querySelector('.alert');
            if (alert) {
                var bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }
        }, 5000);
    }
}

// Global error handler
window.addEventListener('error', function(e) {
    console.error('JavaScript Error:', e.error);
    // Optionally show user-friendly error message
    // showNotification('אירעה שגיאה במערכת. אנא נסה שוב.', 'error');
});

