{
    "name": "Invoice Journal Select",
    "version": "19.0.1.0.0",
    "author": "Bobur",
    "category": "Accounting",
    "summary": "Foydalanuvchiga to'lov ro'yxatga olish oynasida ko'rinadigan jurnallarni cheklash",
    "depends": [
        "account",  # account.payment.register modeli uchun shart
    ],
    "data": [
        "views/res_users_view.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
