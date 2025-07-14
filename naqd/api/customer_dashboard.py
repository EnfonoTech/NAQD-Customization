import frappe
from frappe.utils import flt, getdate
from erpnext.accounts.utils import get_balance_on 

@frappe.whitelist()
def get_customer_dashboard(customer):
    try:
        # Step 1: Count project statuses
        status_counts = {
            "Open": frappe.db.count("Project", {"customer": customer, "status": "Open"}),
            "Completed": frappe.db.count("Project", {"customer": customer, "status": "Completed"}),
            "Cancelled": frappe.db.count("Project", {"customer": customer, "status": "Cancelled"})
        }

        # Step 2: Get all project names for this customer
        customer_projects = frappe.get_all("Project", filters={
            "customer": customer,
            "status": ["!=", "Cancelled"]
        }, fields=["name"])
        project_names = [p.name for p in customer_projects]

        # Step 3: Find which projects are used in Sales Invoices
        billed_projects = frappe.get_all("Sales Invoice", filters={
            "docstatus": 1,
            "project": ["in", project_names]
        }, fields=["project"])
        billed_project_names = {b.project for b in billed_projects}

        # Step 4: Calculate unbilled projects
        unbilled_projects = len([p for p in project_names if p not in billed_project_names])

        # Step 5: Get ledger balance using utility function
        balance = get_balance_on(party_type="Customer", party=customer) or 0.0

        # Step 6: Return the dashboard HTML
        html = f"""
        <div class="custom-customer-dashboard" style="display: flex; gap: 20px; margin-bottom: 20px;">
            <div style="padding: 10px; border: 1px solid #ddd; border-radius: 8px; min-width: 180px;">
                <div><strong style="font-size: 18px;">{status_counts['Open']}</strong>   <medium>Ongoing Projects</medium></div>
            </div>
            <div style="padding: 10px; border: 1px solid #ddd; border-radius: 8px; min-width: 180px;">
                <div><strong style="font-size: 18px;">{status_counts['Cancelled']}</strong>  <medium>Cancelled Projects</medium></div>
            </div>
            <div style="padding: 10px; border: 1px solid #ddd; border-radius: 8px; min-width: 180px;">
                <div><strong style="font-size: 18px;">{status_counts['Completed']}</strong>  <medium>Completed Projects</medium></div>
            </div>
            <div style="padding: 10px; border: 1px solid #ddd; border-radius: 8px; min-width: 180px;">
                <div><strong style="font-size: 18px;">{unbilled_projects}</strong>   <medium>Unbilled Projects</medium></div>
            </div>
            <div style="padding: 10px; border: 1px solid #ddd; border-radius: 8px; min-width: 180px;">
                <div><strong style="font-size: 18px;">₹{flt(balance, 2):,.2f}</strong>   <medium>Ledger Balance</medium></div>
            </div>
        </div>
        """
        return html

    except Exception as e:
        frappe.log_error(f"Customer Dashboard Error: {str(e)}")
        return f"""
        <div style="padding: 12px; background: #fee2e2; color: #b91c1c;">
            <strong>Error loading dashboard:</strong> {str(e)}
        </div>
        """
