# -*- coding: utf-8 -*-
{
    'name'     : 'InfoSaône - Module Odoo 16 pour France Filets (anti-chute-pro)',
    'version'  : '0.1',
    'author'   : 'InfoSaône',
    'category' : 'InfoSaône',
    'description': """
InfoSaône - Module Odoo 16 pour France Filets (anti-chute-pro)
===================================================
""",
    'maintainer' : 'InfoSaône',
    'website'    : 'http://www.infosaone.com',
    'depends'    : [
        'base',
        'stock',
        'sale_management',
        'sales_team',
        'mail',
        'account',
        'purchase',
        'attachment_indexation',
        # "base_rest",                    # Pour API Rest Akyos
        # "base_rest_datamodel",          # Pour API Rest Akyos
        # "base_rest_auth_user_service",  # Pour API Rest Akyos
        # "component",                    # Pour API Rest Akyos
],
    'data' : [
        'security/res.groups.xml',
        'security/ir.model.access.csv',
        'security/ir.model.access.xml',
        'views/res_company_view.xml',
        'views/partner_view.xml',
        'views/sale_view.xml',
        'views/account_move_view.xml',
        'views/is_export_compta_view.xml',
        'views/is_sale_order_line.xml',
        'views/is_filet_view.xml',
        'views/is_suivi_budget_view.xml',
        'views/report_templates.xml',
        'views/menu.xml',
        'report/sale_report_templates.xml',
        'report/report_invoice.xml',
        'report/planning_report_templates.xml',
        'report/fiche_travail_report_templates.xml',
        'report/pv_reception_report_templates.xml',
        'report/is_suivi_budget_report_templates.xml',
        'report/is_suivi_budget_journal_vente_report_templates.xml',
        'report/report.xml',
    ],
    'installable': True,
    'application': True,
    'qweb': [
    ],
    'license': 'LGPL-3',
}

