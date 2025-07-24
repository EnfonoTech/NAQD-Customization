import frappe
from frappe.utils import today

def create_sales_invoice_on_completion(doc, method):
    if doc.status != "Completed":
        return

    if frappe.db.exists("Sales Invoice", {"project": doc.name, "docstatus": 0}):
        return

    if not doc.customer:
        frappe.throw("Project must be linked to a Customer to generate a Sales Invoice.")

    invoice = frappe.new_doc("Sales Invoice")
    invoice.customer = doc.customer
    invoice.project = doc.name
    invoice.due_date = today()
    invoice.set_posting_time = 1

    # Add placeholder item
    invoice.append("items", {
        "item_code": "sample item",  # Make sure this item exists
        "qty": 1,
        "rate": 0
    })

    invoice.insert(ignore_permissions=True)


    frappe.msgprint(f"Draft Sales Invoice <b>{invoice.name}</b> created.")


