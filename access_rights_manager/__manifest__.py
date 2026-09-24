# -*- coding: utf-8 -*-
{
    'name': 'Access Rights Manager',
    'version': '19.0.1.0.0',
    'category': 'Extra Tools',
    'summary': 'Odoo Access Manager, access management App,User wise access rules,Access rules setup,access rights setup, Hide Any Menu, Any Field, Any Report, Any Button,Odoo user rights,User security roles,Advanced Users Access Rights,Advanced Users Access Rights Manager,Hide Fields, Hide Buttons, Hide Tabs, Hide Views, Hide Contacts, Hide Menus, Hide Submenus, Hide Reports, Hide Actions, Hide Server Actions,Hide Delete, Hide Tree view, Hide Apps, Hide Object Buttons, Hide Action Buttons, Hide Smart Buttons, Readonly Any Field, Readonly User, Readonly User, Hide Create, Hide Duplicate, Readonly Field, Invisible Field,Allow to Disable Developer Mode or Disable Debug Mode For Users,Single step access rights management for the system users rights, report access permissions , Message access rights, Chatter userwise visiblity, Chatter model wise access set, fields level access right, model level access right, Chatter hide, Hide Chatter, Invisible Chatter, Hide Group By, Hide Filter, Hide Filters, Chatter Hide, Control Every Fields, Control Every Views, Control Every Buttons, Control Every Actions, Restrict/Read-OnlyAll in One Access Rights Manager, Access Manager, Sales Access, Sale Access, Invoicing Access, Invoice Access, CRM Access, Inventory Access, Accounting Access, Purchase Access, Project Access, Manufacturing Access, Email Marketing Access, Timesheets Access, Expenses Access, Documents Access, Time Off Access, Recruitment Access, Employees Access, Knowledge Access, Maintenance Access, Helpdesk Access, Subscriptions Access, Quality Access, Quality Control Access, Contacts Access, Rental Access, Calendar Access, Field Service Access, Social Marketing Access, Appraisals Access, Fleet Access, Approvals Access, Consolidation Access, Appointments Access, Surveys Access, Repairs Access, Referral Access, Attendances Access, Management Access, Shipping Access, VOIP Access, Payroll Access, Jobs Access, Lunch AccessAccess Management System Customized Menu Access Field access control Navbar button management Chatter Access Management Report action Management Multiaction views access Role-based access control Customizable user permissions User Role Management Access Control Security User Provisioning Access Monitoring Access Management System module User Access Control software Access Management solution Access Control System tool Manage Access Management of user access manage access All in one access control all in one access management User wise access rules user wise access control user wise access management hide menu hide any menu hide sub menu disable menu disable submenu disable any menu invisible menu hide menus usewise hide menu user wise menu hide submenus hide menus Hide field hide fields hide any field disable fields user wise fields invisible field Read only fields hide archive disable action disable delete Hide buttons hide any buttons disable button user wise buttons invisible button Hide delete hide import hide export hide actions Hide tabs hide any tabs invisible tab Hide views hide any view hide tree view hide list view hide kanban view hide graph view hide activity view hide apps invisible views hide reports disable reports user wise reports Hide chatter disable chatter invisible chatter Access rights user access roles user security access user wise accesses access rights setup Odoo Hide Menu, Submenu,Actions,Reports,Fields,Create, Edit Button Visible/Invisible in Tree/Form View Delete, Duplicate Action Visible/Invisible in Tree/Form View,Hide Conversation,Hide Developer Mode,hide Chatter, Hide Button/Tab Single step access rights management for the system users rights, report access permissions , Message access rights, Chatter userwise visiblity, Chatter model wise access set, fields level access right, model level access right, Chatter hide',
    'description': "Access Rights Manager",
    'license': 'OPL-1',
    'images': ['static/description/main_screenshot.png'],
    'data': [
        'security/ir.model.access.csv',
        'security/access_right_control.xml',
        'views/access_rights_management_view.xml',
        'views/res_users_view.xml',
        'views/model_nodes_view.xml',
    ],
    'assets':{
        'web.assets_backend': [
            # 'access_rights_manager/static/src/js/debug.js',
            'access_rights_manager/static/src/js/form_controller.js',
            'access_rights_manager/static/src/js/idle_timer.js',
            'access_rights_manager/static/src/xml/debug.xml',
        ],
    },
    'depends': ['web'],
    'post_init_hook': 'post_install_action_dup_hook',
    'application': True,
    'installable': True,
    'auto_install': False,
    'author': "Khaled Hassan",
    'website': "https://apps.odoo.com/apps/modules/browse?search=Khaled+hassan",
    "price": "120",
    "currency": "EUR",
}
