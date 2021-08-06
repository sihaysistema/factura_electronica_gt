import frappe


def execute():
    try:
        # Cambios propiedades campo pincode
        frappe.make_property_setter({
            "doctype": "Address",
            "fieldname": "pincode",
            "property": "allow_in_quick_entry",
            "value": 1,
            "property_type": "Int"
        })

        frappe.make_property_setter({
            "doctype": "Address",
            "fieldname": "pincode",
            "default": "0",
            "property": "reqd",
            "value": 1,
            "property_type": "Int"
        })

        # Cambios propiedades campo email_id
        frappe.make_property_setter({
            "doctype": "Address",
            "fieldname": "email_id",
            "property": "allow_in_quick_entry",
            "value": 1,
            "property_type": "Int"
        })

        frappe.make_property_setter({
            "doctype": "Address",
            "fieldname": "email_id",
            "property": "reqd",
            "value": 0,
            "property_type": "Int"
        })

        # Cambios propiedades campo phone
        frappe.make_property_setter({
            "doctype": "Address",
            "fieldname": "phone",
            "property": "reqd",
            "value": 0,
            "property_type": "Int"
        })

        frappe.make_property_setter({
            "doctype": "Address",
            "fieldname": "phone",
            "property": "allow_in_quick_entry",
            "value": 1,
            "property_type": "Int"
        })

        # Campo tax id en Customer Dt
        frappe.make_property_setter({
            "doctype": "Customer",
            "fieldname": "tax_id",
            "property": "reqd",
            "value": 1,
            "property_type": "Int"
        })

        frappe.make_property_setter({
            "doctype": "Address",
            "fieldname": "tax_id",
            "default": "C/F",
            "property": "allow_in_quick_entry",
            "value": 1,
            "property_type": "Int"
        })

        frappe.make_property_setter({
            "doctype": "Customer",
            "fieldname": "county",
            "property": "reqd",
            "value": 0,
            "property_type": "Int"
        })

        frappe.make_property_setter({
            "doctype": "Address",
            "fieldname": "county",
            "default": "Guatemala",
            "property": "allow_in_quick_entry",
            "value": 1,
            "property_type": "Int"
        })

        for ffield in ["city", "state", "country"]:
            frappe.make_property_setter({
                "doctype": "Address",
                "fieldname": ffield,
                "default": "Guatemala",
                "property": "reqd",
                "value": 1,
                "property_type": "Int"
            })

            frappe.make_property_setter({
                "doctype": "Address",
                "fieldname": ffield,
                "property": "allow_in_quick_entry",
                "value": 1,
                "property_type": "Int"
            })

    except:
        with open("debug.txt", "w") as f:
            f.write(str(frappe.get_traceback()))
