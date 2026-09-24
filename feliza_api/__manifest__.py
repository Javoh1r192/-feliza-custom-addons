{
    "name": "Feliza APIs",
    "version": "1.4",
    "author": "Shahzod",
    "summary": "Feliza APIs",
    "icon": "/feliza_api/static/description/feliza.jpg",
    "depends": [
        "base",
        "web",
        "fastapi",
        "product",
        "contacts",
        "sale",
        "sale_loyalty",
        "stock",
        "queue_job"
    ],
    "data": [
        "data/queue_job_data.xml",
        "views/product_product.xml",
        "views/product_template.xml",
        "views/res_partner.xml"
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
}
