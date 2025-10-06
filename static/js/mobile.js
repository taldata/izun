/**
 * Mobile Enhancements for Committee Management System
 * Includes touch gestures, pull-to-refresh, and PWA support
 */

(function() {
    'use strict';

    // Check if device is mobile
    const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    const isTouch = 'ontouchstart' in window || navigator.maxTouchPoints > 0;

    // Initialize mobile features
    document.addEventListener('DOMContentLoaded', function() {
        if (isMobile || isTouch) {
            initMobileFeatures();
        }
    });

    function initMobileFeatures() {
        console.log('Initializing mobile features...');
        
        // Add mobile class to body
        document.body.classList.add('mobile-device');
        
        // Initialize features
        initTouchGestures();
        initPullToRefresh();
        initMobileNavigation();
        initTableCards();
        initBottomSheet();
        registerServiceWorker();
        
        // Prevent zoom on double tap
        preventDoubleTapZoom();
        
        // Handle viewport changes
        handleViewportChanges();
    }

    /**
     * Touch Gestures Support
     */
    function initTouchGestures() {
        let touchStartX = 0;
        let touchStartY = 0;
        let touchEndX = 0;
        let touchEndY = 0;

        // Swipeable cards
        const cards = document.querySelectorAll('.mobile-card, .card');
        
        cards.forEach(card => {
            let startX = 0;
            let currentX = 0;
            
            card.addEventListener('touchstart', function(e) {
                startX = e.touches[0].clientX;
                card.style.transition = 'none';
            }, { passive: true });
            
            card.addEventListener('touchmove', function(e) {
                if (!startX) return;
                
                currentX = e.touches[0].clientX;
                const diff = currentX - startX;
                
                // Only allow right swipe (for RTL)
                if (diff > 0 && diff < 100) {
                    card.style.transform = `translateX(${diff}px)`;
                }
            }, { passive: true });
            
            card.addEventListener('touchend', function() {
                const diff = currentX - startX;
                
                if (diff > 50) {
                    // Swipe right action (show options)
                    card.classList.add('swiped');
                    card.style.transform = 'translateX(80px)';
                } else {
                    // Reset
                    card.style.transition = 'transform 0.3s ease';
                    card.style.transform = 'translateX(0)';
                }
                
                startX = 0;
                currentX = 0;
            }, { passive: true });
        });

        // Swipe navigation
        document.addEventListener('touchstart', function(e) {
            touchStartX = e.changedTouches[0].screenX;
            touchStartY = e.changedTouches[0].screenY;
        }, { passive: true });

        document.addEventListener('touchend', function(e) {
            touchEndX = e.changedTouches[0].screenX;
            touchEndY = e.changedTouches[0].screenY;
            handleSwipe();
        }, { passive: true });

        function handleSwipe() {
            const diffX = touchEndX - touchStartX;
            const diffY = touchEndY - touchStartY;
            
            // Minimum swipe distance
            const minSwipeDistance = 100;
            
            if (Math.abs(diffX) > Math.abs(diffY)) {
                // Horizontal swipe
                if (Math.abs(diffX) > minSwipeDistance) {
                    if (diffX > 0) {
                        // Swipe right
                        handleSwipeRight();
                    } else {
                        // Swipe left
                        handleSwipeLeft();
                    }
                }
            }
        }

        function handleSwipeRight() {
            // Go back in history
            if (window.history.length > 1) {
                showNotification('החזרה לעמוד הקודם...', 'info');
                setTimeout(() => window.history.back(), 300);
            }
        }

        function handleSwipeLeft() {
            // Open menu if available
            const menuToggle = document.querySelector('.navbar-toggler');
            if (menuToggle && !menuToggle.classList.contains('collapsed')) {
                menuToggle.click();
            }
        }
    }

    /**
     * Pull to Refresh
     */
    function initPullToRefresh() {
        let startY = 0;
        let currentY = 0;
        let pullDistance = 0;
        const pullThreshold = 80;
        
        const refreshIndicator = createRefreshIndicator();
        document.body.insertBefore(refreshIndicator, document.body.firstChild);

        document.addEventListener('touchstart', function(e) {
            if (window.scrollY === 0) {
                startY = e.touches[0].pageY;
            }
        }, { passive: true });

        document.addEventListener('touchmove', function(e) {
            if (startY === 0) return;
            
            currentY = e.touches[0].pageY;
            pullDistance = currentY - startY;
            
            if (pullDistance > 0 && pullDistance < pullThreshold * 2) {
                e.preventDefault();
                refreshIndicator.style.transform = `translateY(${pullDistance}px)`;
                refreshIndicator.style.opacity = Math.min(pullDistance / pullThreshold, 1);
                
                if (pullDistance > pullThreshold) {
                    refreshIndicator.classList.add('ready');
                } else {
                    refreshIndicator.classList.remove('ready');
                }
            }
        }, { passive: false });

        document.addEventListener('touchend', function() {
            if (pullDistance > pullThreshold) {
                refreshIndicator.classList.add('refreshing');
                refreshPage();
            } else {
                resetRefreshIndicator();
            }
            
            startY = 0;
            pullDistance = 0;
        }, { passive: true });

        function createRefreshIndicator() {
            const indicator = document.createElement('div');
            indicator.className = 'pull-to-refresh-indicator';
            indicator.innerHTML = `
                <div class="refresh-spinner">
                    <i class="bi bi-arrow-clockwise"></i>
                </div>
                <span class="refresh-text">משוך כדי לרענן</span>
            `;
            return indicator;
        }

        function refreshPage() {
            const indicator = document.querySelector('.pull-to-refresh-indicator');
            const text = indicator.querySelector('.refresh-text');
            text.textContent = 'מרענן...';
            
            setTimeout(() => {
                location.reload();
            }, 500);
        }

        function resetRefreshIndicator() {
            const indicator = document.querySelector('.pull-to-refresh-indicator');
            indicator.style.transform = 'translateY(0)';
            indicator.style.opacity = '0';
            indicator.classList.remove('ready', 'refreshing');
        }
    }

    /**
     * Mobile Navigation Enhancements
     */
    function initMobileNavigation() {
        const navbar = document.querySelector('.navbar-collapse');
        const navToggler = document.querySelector('.navbar-toggler');
        
        if (navbar && navToggler) {
            // Close menu when clicking outside
            document.addEventListener('click', function(e) {
                if (!navbar.contains(e.target) && !navToggler.contains(e.target)) {
                    if (navbar.classList.contains('show')) {
                        navToggler.click();
                    }
                }
            });
            
            // Close menu when clicking a link
            const navLinks = navbar.querySelectorAll('.nav-link');
            navLinks.forEach(link => {
                link.addEventListener('click', function() {
                    if (navbar.classList.contains('show')) {
                        setTimeout(() => navToggler.click(), 200);
                    }
                });
            });
        }

        // Add bottom navigation for mobile
        if (window.innerWidth <= 768) {
            createBottomNavigation();
        }
    }

    function createBottomNavigation() {
        const bottomNav = document.createElement('div');
        bottomNav.className = 'bottom-navigation';
        bottomNav.innerHTML = `
            <a href="${window.location.origin}/" class="bottom-nav-item ${location.pathname === '/' ? 'active' : ''}">
                <i class="bi bi-house"></i>
                <span>בית</span>
            </a>
            <a href="${window.location.origin}/events_table" class="bottom-nav-item ${location.pathname.includes('events') ? 'active' : ''}">
                <i class="bi bi-table"></i>
                <span>אירועים</span>
            </a>
            <a href="${window.location.origin}/auto_schedule" class="bottom-nav-item ${location.pathname.includes('schedule') ? 'active' : ''}">
                <i class="bi bi-robot"></i>
                <span>תזמון</span>
            </a>
            <button class="bottom-nav-item" onclick="document.querySelector('.navbar-toggler').click()">
                <i class="bi bi-list"></i>
                <span>תפריט</span>
            </button>
        `;
        
        document.body.appendChild(bottomNav);
        document.body.style.paddingBottom = '70px';
    }

    /**
     * Convert Tables to Cards on Mobile
     */
    function initTableCards() {
        const tables = document.querySelectorAll('.table-responsive table');
        
        tables.forEach(table => {
            if (window.innerWidth <= 768) {
                convertTableToCards(table);
            }
        });

        // Re-check on resize
        window.addEventListener('resize', debounce(() => {
            tables.forEach(table => {
                if (window.innerWidth <= 768) {
                    convertTableToCards(table);
                } else {
                    restoreTable(table);
                }
            });
        }, 250));
    }

    function convertTableToCards(table) {
        if (table.dataset.mobileConverted === 'true') return;
        
        const headers = Array.from(table.querySelectorAll('thead th')).map(th => th.textContent.trim());
        const rows = table.querySelectorAll('tbody tr');
        
        const cardsContainer = document.createElement('div');
        cardsContainer.className = 'table-mobile-cards';
        
        rows.forEach(row => {
            const cells = row.querySelectorAll('td');
            const card = document.createElement('div');
            card.className = 'mobile-card';
            
            let cardHTML = '<div class="mobile-card-header">';
            // Use first cell as header
            if (cells[0]) {
                cardHTML += cells[0].textContent.trim();
            }
            cardHTML += '</div>';
            
            cells.forEach((cell, index) => {
                if (index === 0) return; // Skip first cell (used as header)
                
                cardHTML += `
                    <div class="mobile-card-row">
                        <div class="mobile-card-label">${headers[index] || ''}</div>
                        <div class="mobile-card-value">${cell.innerHTML}</div>
                    </div>
                `;
            });
            
            // Add action buttons if present
            const actionButtons = row.querySelectorAll('.btn, button, a.btn');
            if (actionButtons.length > 0) {
                cardHTML += '<div class="mobile-card-actions">';
                actionButtons.forEach(btn => {
                    cardHTML += btn.outerHTML;
                });
                cardHTML += '</div>';
            }
            
            card.innerHTML = cardHTML;
            cardsContainer.appendChild(card);
        });
        
        table.classList.add('table-desktop');
        table.style.display = 'none';
        table.parentNode.appendChild(cardsContainer);
        table.dataset.mobileConverted = 'true';
    }

    function restoreTable(table) {
        const cardsContainer = table.parentNode.querySelector('.table-mobile-cards');
        if (cardsContainer) {
            cardsContainer.remove();
            table.style.display = '';
            table.classList.remove('table-desktop');
            table.dataset.mobileConverted = 'false';
        }
    }

    /**
     * Bottom Sheet for Actions
     */
    function initBottomSheet() {
        // Convert modals to bottom sheets on mobile
        const modals = document.querySelectorAll('.modal');
        
        modals.forEach(modal => {
            if (window.innerWidth <= 768) {
                modal.classList.add('mobile-bottom-sheet');
                
                const modalDialog = modal.querySelector('.modal-dialog');
                if (modalDialog) {
                    modalDialog.style.margin = '0';
                    modalDialog.style.maxWidth = '100%';
                    modalDialog.style.position = 'fixed';
                    modalDialog.style.bottom = '0';
                    modalDialog.style.left = '0';
                    modalDialog.style.right = '0';
                    modalDialog.style.transform = 'translateY(100%)';
                    modalDialog.style.transition = 'transform 0.3s ease';
                }
            }
        });
    }

    /**
     * Service Worker Registration for PWA
     */
    function registerServiceWorker() {
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/static/js/sw.js')
                .then(registration => {
                    console.log('Service Worker registered:', registration);
                })
                .catch(error => {
                    console.log('Service Worker registration failed:', error);
                });
        }
    }

    /**
     * Prevent Double Tap Zoom
     */
    function preventDoubleTapZoom() {
        let lastTap = 0;
        
        document.addEventListener('touchend', function(e) {
            const currentTime = new Date().getTime();
            const tapLength = currentTime - lastTap;
            
            if (tapLength < 300 && tapLength > 0) {
                e.preventDefault();
            }
            
            lastTap = currentTime;
        }, { passive: false });
    }

    /**
     * Handle Viewport Changes
     */
    function handleViewportChanges() {
        // Handle orientation change
        window.addEventListener('orientationchange', function() {
            setTimeout(() => {
                location.reload();
            }, 200);
        });

        // Handle resize
        let resizeTimer;
        window.addEventListener('resize', function() {
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(() => {
                adjustLayoutForViewport();
            }, 250);
        });
    }

    function adjustLayoutForViewport() {
        const vh = window.innerHeight * 0.01;
        document.documentElement.style.setProperty('--vh', `${vh}px`);
    }

    /**
     * Utility Functions
     */
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    function showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `mobile-notification ${type}`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.classList.add('show');
        }, 100);
        
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, 2000);
    }

    // Initialize on load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initMobileFeatures);
    } else {
        initMobileFeatures();
    }

})();
