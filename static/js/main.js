$(document).ready(function() {
    // Show loading overlay on form submissions (excluding quick AJAX or GET requests)
    $('form[method="POST"]').on('submit', function() {
        // Only show if it's not a modal form being submitted via AJAX (future proofing)
        if (!$(this).hasClass('ajax-form')) {
            $('#loading-overlay').removeClass('d-none');
        }
    });

    // Auto-hide alerts/toasts after 5 seconds
    setTimeout(function() {
        $('.toast').removeClass('show');
    }, 5000);

    // Profile Modal cmp_id population is handled inline in companies.html
    // Student Form filtering could be enhanced here if needed

    // Responsive Sidebar Toggling
    const $sidebar = $('#sidebar');
    const $backdrop = $('#sidebar-backdrop');

    function toggleSidebar() {
        $sidebar.toggleClass('show');
        $backdrop.toggleClass('show');
        $('body').toggleClass('overflow-hidden');
    }

    $('#sidebar-toggle').on('click', toggleSidebar);
    $('#sidebar-close').on('click', toggleSidebar);
    $backdrop.on('click', toggleSidebar);

    // Close sidebar on link click in mobile view
    $sidebar.find('.nav-link').on('click', function() {
        if ($(window).width() < 992) {
            toggleSidebar();
        }
    });
});
