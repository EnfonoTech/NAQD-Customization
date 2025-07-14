frappe.ui.form.on('Customer', {
    refresh: function (frm) {
        // Clear old dashboard
        $(frm.wrapper).find('.custom-customer-dashboard-container').remove();
        if (frm.is_new()) return;

        frappe.after_ajax(() => {
            const $container = $(`
                <div class="custom-customer-dashboard-container">
                    <div class="dashboard-loading text-center" style="padding: 16px;">
                        <i class="fa fa-spinner fa-spin fa-2x"></i>
                        <p>Loading customer dashboard...</p>
                    </div>
                </div>
            `);

            $(frm.wrapper).find('.layout-main-section-wrapper').prepend($container);

            frappe.call({
                method: "naqd.api.customer_dashboard.get_customer_dashboard",
                args: { customer: frm.doc.name },
                callback: function (r) {
                    if (r.message) {
                        $container.html(r.message);
                    } else {
                        $container.html('<div class="text-muted">No dashboard data available.</div>');
                    }
                },
                error: function () {
                    $container.html('<div class="text-danger">Error loading dashboard.</div>');
                }
            });
        });
    }
});
