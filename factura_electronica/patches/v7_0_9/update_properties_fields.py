import frappe

# This patch deletes all the duplicate indexes created for same column
# The patch only checks for indexes with UNIQUE constraints

def execute():
    try:
        for ffield in ["city", "county", "state", "country"]:
            frappe.make_property_setter({
                "doctype": "Address",
                "fieldname": ffield,
                "default": "Guatemala",
                "property": "reqd",
                "value": 1,
                "property_type": "Int"
            },
            {
                "doctype": 'Address',
                "fieldname": ffield,
                "property": "allow_in_quick_entry",
                "value": 1,
                "property_type": "Int"
            })

        frappe.make_property_setter({
            "doctype": 'Address',
            "fieldname": 'is_primary_address',
            "property": "allow_in_quick_entry",
            "value": 1,
            "property_type": "Int"
        },
        {
            "doctype": 'Address',
            "fieldname": 'pincode',
            "default": "0",
            "property": "reqd",
            "value": 1,
            "property_type": "Int"
        },
        {
            "doctype": 'Address',
            "fieldname": 'pincode',
            "property": "allow_in_quick_entry",
            "value": 0,
            "property_type": "Int"
        },
        {
            "doctype": 'Address',
            "fieldname": 'email_id',
            "property": "reqd",
            "value": 1,
            "property_type": "Int"
        },
        {
            "doctype": 'Address',
            "fieldname": 'email_id',
            "property": "allow_in_quick_entry",
            "value": 1,
            "property_type": "Int"
        },
        {
            "doctype": 'Address',
            "fieldname": 'phone',
            "property": "reqd",
            "value": 0,
            "property_type": "Int"
        },
        {
            "doctype": 'Address',
            "fieldname": 'phone',
            "property": "allow_in_quick_entry",
            "value": 1,
            "property_type": "Int"
        })

    except:
        pass
