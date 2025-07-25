import frappe
from frappe.utils import today, getdate, formatdate
import calendar


def set_custom_previous_links(doc, method):
    """Run after Project creation: re-link tasks created from template and copy checklist."""

    if not doc.project_template:
        return

    # Step 1: Get task subjects from the template via its child table
    template_task_links = frappe.get_all("Project Template Task", filters={
        "parent": doc.project_template
    }, fields=["task", "subject"])

    template_tasks = []
    for row in template_task_links:
        task = frappe.get_doc("Task", row.task)
        template_tasks.append({
            "name": task.name,
            "subject": task.subject,
            "custom_previous_task": task.custom_previous_task,
            "checklist": task.get("custom_check_list", [])  # Get checklist from template task
        })

    # Step 2: Get newly created tasks for this project
    real_tasks = frappe.get_all("Task", filters={
        "project": doc.name,
        "is_template": 0
    }, fields=["name", "subject"])

    # Step 3: Map subject → real task name
    subject_to_real_task = {t.subject: t.name for t in real_tasks}

    # Step 4: Set custom_previous_task links and copy checklist
    for template in template_tasks:
        current_subject = template["subject"]
        real_current = subject_to_real_task.get(current_subject)
        
        if not real_current:
            continue
            
        # Set previous task link
        if template["custom_previous_task"]:
            previous_subject = frappe.db.get_value("Task", template["custom_previous_task"], "subject")
            real_previous = subject_to_real_task.get(previous_subject)
            
            if real_previous:
                frappe.db.set_value("Task", real_current, "custom_previous_task", real_previous)

        # Copy checklist from template task to real task
        if template["checklist"]:
            real_task_doc = frappe.get_doc("Task", real_current)
            
            # Clear existing checklist (if any)
            real_task_doc.set("custom_check_list", [])
            
            # Add checklist items from template
            for checklist_item in template["checklist"]:
                real_task_doc.append("custom_check_list", {
                    "check_list": checklist_item.check_list,
                    "comment": checklist_item.get("comment", ""),
                    "done": 0  # Default to not done for new tasks
                })
            
            # Save the task with new checklist
            real_task_doc.save(ignore_permissions=True)

    # Step 5: Make first task(s) visible
    for task in real_tasks:
        prev = frappe.db.get_value("Task", task.name, "custom_previous_task")
        if not prev:
            frappe.db.set_value("Task", task.name, "custom_visible_to_user", 1)


def on_task_update(doc, method):
    """After a task is updated, check if it was completed. If yes, unhide the next task(s).
    Also, if all tasks in the project are completed, trigger sales invoice creation."""
    
    if doc.status == "Completed":
        # Unhide next tasks
        next_tasks = frappe.get_all("Task", filters={
            "custom_previous_task": doc.name,
            "project": doc.project
        })
        for task in next_tasks:
            frappe.db.set_value("Task", task.name, "custom_visible_to_user", 1)

        # Check if all project tasks are completed
        if doc.project:
            total = frappe.db.count("Task", {"project": doc.project})
            completed = frappe.db.count("Task", {"project": doc.project, "status": "Completed"})

            if total and total == completed:
                # Set project to Completed (if not already)
                project_doc = frappe.get_doc("Project", doc.name)
                if project_doc.status != "Completed":
                    project_doc.status = "Completed"
                    project_doc.save()

                # Now trigger invoice
                from naqd.project_hooks import create_sales_invoice_on_completion
                create_sales_invoice_on_completion(project_doc, method="triggered_by_task")


def create_auto_repeat_from_project(doc, method):
    frequency = doc.get("custom_repeat_frequency")
    # Set auto-repeat info in project
    created_date = getdate(doc.creation or today())
    month_name = calendar.month_name[created_date.month]
    info = f"{month_name} {created_date.year} ({frequency or 'One Time'})"
    frappe.db.set_value("Project", doc.name, "custom_auto_repeat_info", info)    

    if not frequency or frequency == "One Time":
        return  # Don't create Auto Repeat
    if frappe.db.exists("Auto Repeat", {"reference_name": doc.name, "reference_doctype": "Project"}):
        return

    # Create Auto Repeat
    auto_repeat = frappe.new_doc("Auto Repeat")
    auto_repeat.reference_doctype = "Project"
    auto_repeat.reference_document = doc.name
    auto_repeat.frequency = frequency
    auto_repeat.start_date = today()
    auto_repeat.submit()


def tag_project_created_by_auto_repeat(doc, method):
    """Set custom_auto_repeat_info if project was created via Auto Repeat."""
    auto_repeat = frappe.db.exists("Auto Repeat", {
        "reference_name": doc.name,
        "reference_doctype": "Project"
    })
    if auto_repeat:
        created_date = getdate(doc.creation or today())
        month_name = calendar.month_name[created_date.month]
        freq = frappe.db.get_value("Auto Repeat", auto_repeat, "frequency")
        info = f"{month_name} {created_date.year} ({freq})"
        frappe.db.set_value("Project", doc.name, "custom_auto_repeat_info", info)


# Optional: Wrapper for hooks (if needed)
def update_checklist_from_hooks(doc, method):
    """Wrapper to call update_existing_tasks_with_checklist from hooks."""
    if doc.project_template:
        update_existing_tasks_with_checklist(doc.name, doc.project_template)


# Optional: Helper function to bulk update checklist for existing tasks
def update_existing_tasks_with_checklist(project_name, template_name):
    """
    Helper function to update existing tasks with checklist from template.
    Call this if you need to update tasks that were already created.
    """
    # Get template tasks
    template_task_links = frappe.get_all("Project Template Task", filters={
        "parent": template_name
    }, fields=["task", "subject"])

    template_checklists = {}
    for row in template_task_links:
        task = frappe.get_doc("Task", row.task)
        if task.get("checklist"):
            template_checklists[task.subject] = task.get("checklist", [])

    # Get project tasks
    real_tasks = frappe.get_all("Task", filters={
        "project": project_name,
        "is_template": 0
    }, fields=["name", "subject"])

    # Update each task
    for task in real_tasks:
        if task.subject in template_checklists:
            task_doc = frappe.get_doc("Task", task.name)
            
            # Clear existing checklist
            task_doc.set("checklist", [])
            
            # Add checklist from template
            for item in template_checklists[task.subject]:
                task_doc.append("checklist", {
                    "check_list": item.check_list,
                    "comment": item.get("comment", ""),
                    "done": 0
                })
            
            task_doc.save(ignore_permissions=True)
            print(f"Updated checklist for task: {task.name}")
