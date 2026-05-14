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
});
