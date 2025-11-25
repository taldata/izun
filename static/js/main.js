// Main JavaScript for Committee Management System

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Auto-hide alerts after 10 seconds with hover pause
    var alertTimeouts = new Map();

    function setupAlertAutoHide(alert) {
        if (alert.hasAttribute('data-no-auto-hide')) return;

        var timeoutId;
        var autoHideDelay = 10000; // 10 seconds

        function startAutoHide() {
            timeoutId = setTimeout(function() {
                var bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }, autoHideDelay);
            alertTimeouts.set(alert, timeoutId);
        }

        function stopAutoHide() {
            if (timeoutId) {
                clearTimeout(timeoutId);
                alertTimeouts.delete(alert);
            }
        }

        // Start auto-hide
        startAutoHide();

        // Pause on hover
        alert.addEventListener('mouseenter', function() {
            stopAutoHide();
        });

        // Resume on mouse leave
        alert.addEventListener('mouseleave', function() {
            startAutoHide();
        });

        // Clear timeout if manually dismissed
        alert.addEventListener('close.bs.alert', function() {
            stopAutoHide();
        });
    }

    // Setup auto-hide for existing alerts
    document.querySelectorAll('.alert').forEach(setupAlertAutoHide);

    // Setup auto-hide for dynamically added alerts
    var observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            mutation.addedNodes.forEach(function(node) {
                if (node.nodeType === Node.ELEMENT_NODE) {
                    if (node.classList && node.classList.contains('alert')) {
                        setupAlertAutoHide(node);
                    }
                    // Check child elements too
                    node.querySelectorAll && node.querySelectorAll('.alert').forEach(setupAlertAutoHide);
                }
            });
        });
    });

    observer.observe(document.body, {
        childList: true,
        subtree: true
    });

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
            var href = this.getAttribute('href');
            if (!href || href === '#' || href.trim() === '') {
                return; // Nothing to scroll to
            }

            e.preventDefault();
            var target = document.querySelector(href);
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

// Committee hover popover (summary)
(function () {
    var hoverTimer = null;
    var cache = new Map(); // committeeId -> { data, timestamp }
    var CACHE_TTL_MS = 60 * 1000; // 60 seconds
    var activePopover = null;
    var activeEl = null;

    function getCommitteeIdFromRow(row) {
        // rows in committee view use [data-committee-id]
        var id = row && row.getAttribute('data-committee-id');
        return id ? parseInt(id, 10) : null;
    }

    function isCacheFresh(entry) {
        if (!entry) return false;
        return Date.now() - entry.timestamp < CACHE_TTL_MS;
    }

    function buildPopoverContent(summary) {
        if (!summary || !summary.success) {
            return '<div class="text-danger">שגיאה בטעינת פרטי הוועדה</div>';
        }
        var c = summary.committee || {};
        var events = summary.nearest_events || [];

        var header = `
            <div>
                <div class="fw-bold">${c.name || ''}</div>
                <div class="small text-muted">
                    ${c.hativa_name ? c.hativa_name + ' • ' : ''}${c.date ? formatDate(c.date) : ''}
                </div>
            </div>
        `;

        if (events.length === 0) {
            return header + '<div class="mt-2 text-muted small">אין אירועים להצגה</div>';
        }

        var list = '<div class="mt-2">';
        events.forEach(function (ev) {
            var when = ev.start ? formatDate(ev.start) : (ev.end ? formatDate(ev.end) : '');
            var typeBadge = '';
            if (ev.event_type) {
                var cls = ev.event_type === 'kokok' ? 'badge-kokok' : (ev.event_type === 'shotef' ? 'badge-shotef' : 'bg-secondary');
                var label = ev.event_type === 'kokok' ? 'קו\"ק' : (ev.event_type === 'shotef' ? 'שוטף' : ev.event_type);
                typeBadge = `<span class="badge ${cls} ms-1">${label}</span>`;
            }
            list += `
                <div class="d-flex align-items-start mb-1">
                    <div class="flex-grow-1">
                        <div class="fw-semibold">${ev.title || ''}</div>
                        <div class="small text-muted">
                            ${when || ''}${ev.maslul_name ? ' • ' + ev.maslul_name : ''}${ev.location ? ' • ' + ev.location : ''}
                        </div>
                    </div>
                    <div class="ms-2">
                        ${typeBadge}
                    </div>
                </div>
            `;
        });
        list += '</div>';
        return header + list;
    }

    function showPopover(targetEl, content) {
        hidePopover();
        activeEl = targetEl;
        activePopover = new bootstrap.Popover(targetEl, {
            container: 'body',
            trigger: 'manual',
            html: true,
            placement: 'auto',
            customClass: 'committee-summary-popover',
            content: content
        });
        activePopover.show();
    }

    function hidePopover() {
        if (activePopover && activeEl) {
            try {
                activePopover.hide();
            } catch (e) {}
            try {
                activePopover.dispose();
            } catch (e) {}
        }
        activePopover = null;
        activeEl = null;
    }

    // Delegate hover on committee rows (works with dynamic rows)
    document.addEventListener('mouseover', function (e) {
        var row = e.target && (e.target.closest && e.target.closest('.committee-row'));
        if (!row) return;

        // only fire once per row hover
        if (row._hoverBound) return;
        row._hoverBound = true;

        row.addEventListener('mouseenter', function () {
            var committeeId = getCommitteeIdFromRow(row);
            if (!committeeId) return;
            // hover intent delay
            hoverTimer = setTimeout(function () {
                // loading placeholder
                showPopover(row, '<div class="small text-muted">טוען...</div>');

                var entry = cache.get(committeeId);
                if (isCacheFresh(entry)) {
                    showPopover(row, buildPopoverContent(entry.data));
                    return;
                }

                fetch('/api/committees/' + committeeId + '/summary')
                    .then(function (r) { return r.json(); })
                    .then(function (data) {
                        cache.set(committeeId, { data: data, timestamp: Date.now() });
                        // still hovered?
                        if (activeEl === row) {
                            showPopover(row, buildPopoverContent(data));
                        }
                    })
                    .catch(function () {
                        if (activeEl === row) {
                            showPopover(row, '<div class="text-danger small">שגיאה בטעינה</div>');
                        }
                    });
            }, 250);
        });

        row.addEventListener('mouseleave', function () {
            if (hoverTimer) {
                clearTimeout(hoverTimer);
                hoverTimer = null;
            }
            hidePopover();
        });
    });
})();

// Calendar committee hover popover
(function () {
    var hoverTimer = null;
    var cache = new Map(); // committeeId -> { data, timestamp }
    var CACHE_TTL_MS = 60 * 1000; // 60 seconds
    var activePopover = null;
    var activeEl = null;

    function getCommitteeIdFromEl(el) {
        var id = el && el.getAttribute('data-vaada-id');
        return id ? parseInt(id, 10) : null;
    }

    function isCacheFresh(entry) {
        if (!entry) return false;
        return Date.now() - entry.timestamp < CACHE_TTL_MS;
    }

    function buildPopoverContent(summary) {
        if (!summary || !summary.success) {
            return '<div class="text-danger">שגיאה בטעינת פרטי הוועדה</div>';
        }
        var c = summary.committee || {};
        var events = summary.nearest_events || [];

        var header = `
            <div>
                <div class="fw-bold">${c.name || ''}</div>
                <div class="small text-muted">
                    ${c.hativa_name ? c.hativa_name + ' • ' : ''}${c.date ? formatDate(c.date) : ''}
                </div>
            </div>
        `;

        if (events.length === 0) {
            return header + '<div class="mt-2 text-muted small">אין אירועים להצגה</div>';
        }

        var list = '<div class="mt-2">';
        events.forEach(function (ev) {
            var when = ev.start ? formatDate(ev.start) : (ev.end ? formatDate(ev.end) : '');
            var typeBadge = '';
            if (ev.event_type) {
                var cls = ev.event_type === 'kokok' ? 'badge-kokok' : (ev.event_type === 'shotef' ? 'badge-shotef' : 'bg-secondary');
                var label = ev.event_type === 'kokok' ? 'קו\"ק' : (ev.event_type === 'shotef' ? 'שוטף' : ev.event_type);
                typeBadge = `<span class="badge ${cls} ms-1">${label}</span>`;
            }
            list += `
                <div class="d-flex align-items-start mb-1">
                    <div class="flex-grow-1">
                        <div class="fw-semibold">${ev.title || ''}</div>
                        <div class="small text-muted">
                            ${when || ''}${ev.maslul_name ? ' • ' + ev.maslul_name : ''}${ev.location ? ' • ' + ev.location : ''}
                        </div>
                    </div>
                    <div class="ms-2">
                        ${typeBadge}
                    </div>
                </div>
            `;
        });
        list += '</div>';
        return header + list;
    }

    function showPopover(targetEl, content) {
        hidePopover();
        activeEl = targetEl;
        activePopover = new bootstrap.Popover(targetEl, {
            container: 'body',
            trigger: 'manual',
            html: true,
            placement: 'auto',
            customClass: 'committee-summary-popover',
            content: content
        });
        activePopover.show();
    }

    function hidePopover() {
        if (activePopover && activeEl) {
            try { activePopover.hide(); } catch (e) {}
            try { activePopover.dispose(); } catch (e) {}
        }
        activePopover = null;
        activeEl = null;
    }

    // Delegate to dynamically created calendar badges
    document.addEventListener('mouseover', function (e) {
        var el = e.target && (e.target.closest && e.target.closest('.committee-badge'));
        if (!el) return;
        if (el._hoverBound) return;
        el._hoverBound = true;

        el.addEventListener('mouseenter', function () {
            var committeeId = getCommitteeIdFromEl(el);
            if (!committeeId) return;
            hoverTimer = setTimeout(function () {
                showPopover(el, '<div class="small text-muted">טוען...</div>');

                var entry = cache.get(committeeId);
                if (isCacheFresh(entry)) {
                    showPopover(el, buildPopoverContent(entry.data));
                    return;
                }

                fetch('/api/committees/' + committeeId + '/summary')
                    .then(function (r) { return r.json(); })
                    .then(function (data) {
                        cache.set(committeeId, { data: data, timestamp: Date.now() });
                        if (activeEl === el) {
                            showPopover(el, buildPopoverContent(data));
                        }
                    })
                    .catch(function () {
                        if (activeEl === el) {
                            showPopover(el, '<div class="text-danger small">שגיאה בטעינה</div>');
                        }
                    });
            }, 250);
        });

        el.addEventListener('mouseleave', function () {
            if (hoverTimer) {
                clearTimeout(hoverTimer);
                hoverTimer = null;
            }
            hidePopover();
        });
    });
})();

function showNotification(message, type = 'info', options = {}) {
    var alertClass = type === 'error' ? 'alert-danger' :
                    type === 'warning' ? 'alert-warning' :
                    type === 'info' ? 'alert-info' : 'alert-success';

    var iconClass = type === 'error' ? 'exclamation-triangle' :
                   type === 'warning' ? 'exclamation-circle' :
                   type === 'info' ? 'info-circle' : 'check-circle';

    var autoHide = options.autoHide !== false; // Default to true
    var duration = options.duration || 12000; // 12 seconds instead of 5

    var alertHtml = `
        <div class="alert ${alertClass} alert-dismissible fade show notification-enhanced" role="alert"
             ${!autoHide ? 'data-no-auto-hide' : ''}>
            <div class="notification-content">
                <i class="bi bi-${iconClass} me-2 notification-icon"></i>
                <span class="notification-message">${message}</span>
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="סגור"></button>
            </div>
            ${autoHide ? '<div class="notification-progress"></div>' : ''}
        </div>
    `;

    var container = document.querySelector('.container');
    if (container) {
        container.insertAdjacentHTML('afterbegin', alertHtml);

        var alert = container.querySelector('.alert');
        if (alert) {
            // Add enhanced styling
            alert.style.cssText = `
                position: relative;
                overflow: hidden;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                border: none;
                animation: slideInNotification 0.3s ease-out;
            `;

            if (autoHide) {
                // Add progress bar animation
                var progressBar = alert.querySelector('.notification-progress');
                if (progressBar) {
                    progressBar.style.cssText = `
                        position: absolute;
                        bottom: 0;
                        left: 0;
                        height: 3px;
                        background: currentColor;
                        opacity: 0.3;
                        animation: progressBar ${duration}ms linear;
                    `;
                }

                // Auto-hide after specified duration
                setTimeout(function() {
                    if (alert && alert.parentNode) {
                        alert.style.animation = 'slideOutNotification 0.3s ease-in forwards';
                        setTimeout(function() {
                            var bsAlert = new bootstrap.Alert(alert);
                            bsAlert.close();
                        }, 300);
                    }
                }, duration);
            }
        }
    }
}

// Function to create sticky notifications that don't auto-hide
function showStickyNotification(message, type = 'info', title = '') {
    var alertClass = type === 'error' ? 'alert-danger' :
                    type === 'warning' ? 'alert-warning' :
                    type === 'info' ? 'alert-info' : 'alert-success';

    var iconClass = type === 'error' ? 'exclamation-triangle' :
                   type === 'warning' ? 'exclamation-circle' :
                   type === 'info' ? 'info-circle' : 'check-circle';

    var alertHtml = `
        <div class="alert ${alertClass} alert-dismissible fade show notification-enhanced sticky-notification" role="alert" data-no-auto-hide>
            <div class="notification-content">
                <div class="notification-header">
                    ${title ? `<h6 class="notification-title">${title}</h6>` : ''}
                    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="סגור"></button>
                </div>
                <div class="notification-body">
                    <i class="bi bi-${iconClass} me-2 notification-icon"></i>
                    <span class="notification-message">${message}</span>
                </div>
            </div>
        </div>
    `;

    var container = document.querySelector('.container');
    if (container) {
        container.insertAdjacentHTML('afterbegin', alertHtml);

        var alert = container.querySelector('.alert');
        if (alert) {
            // Add enhanced styling for sticky notifications
            alert.style.cssText = `
                position: relative;
                overflow: hidden;
                box-shadow: 0 6px 20px rgba(0,0,0,0.15);
                border: 2px solid currentColor;
                border-radius: 12px;
                animation: slideInNotification 0.3s ease-out;
                background: linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(255,255,255,0.9) 100%);
                backdrop-filter: blur(10px);
            `;

            // Add click to dismiss for sticky notifications
            alert.addEventListener('click', function(e) {
                if (e.target === alert) {
                    var bsAlert = new bootstrap.Alert(alert);
                    bsAlert.close();
                }
            });
        }
    }
}

// Function to show success notifications with different durations
function showSuccessNotification(message, options = {}) {
    return showNotification(message, 'success', { duration: 8000, ...options });
}

function showErrorNotification(message, options = {}) {
    return showNotification(message, 'error', { duration: 15000, ...options }); // Longer for errors
}

function showWarningNotification(message, options = {}) {
    return showNotification(message, 'warning', { duration: 10000, ...options });
}

function showInfoNotification(message, options = {}) {
    return showNotification(message, 'info', { duration: 6000, ...options });
}

// Make notification functions globally available
window.showNotification = showNotification;
window.showStickyNotification = showStickyNotification;
window.showSuccessNotification = showSuccessNotification;
window.showErrorNotification = showErrorNotification;
window.showWarningNotification = showWarningNotification;
window.showInfoNotification = showInfoNotification;

// Global error handler
window.addEventListener('error', function(e) {
    console.error('JavaScript Error:', e.error);
    // Optionally show user-friendly error message
    // showErrorNotification('אירעה שגיאה במערכת. אנא נסה שוב.');
});

