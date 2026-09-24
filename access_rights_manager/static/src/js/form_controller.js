/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";
import { FormController } from "@web/views/form/form_controller";
import { ExportAll } from "@web/views/list/export_all/export_all";
import { user } from "@web/core/user";
import { onWillStart } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import { Component, useEnv, useRef } from "@odoo/owl";

// Common restriction check function
async function checkRestrictions(resModel) {
    if (!resModel || !user.userId) return {};
    return rpc('/access_rights/check_restrictions', {
        user_id: user.userId,
        model_name: resModel
    });
}

patch(ListController.prototype, {
    setup() {
        super.setup();
        this.restrictions = {};

        onWillStart(async () => {
            if (this.props.resModel) {
                this.restrictions = await checkRestrictions(this.props.resModel);
            }
        });
    },

    get actionMenuItems() {
        const items = super.actionMenuItems;
        if (items?.action) {
            if (this.restrictions.disable_archive) {
                items.action = items.action.filter(
                    item => !["archive", "unarchive"].includes(item.key)
                );
            }
            if (this.restrictions.disable_export) {
                items.action = items.action.filter(
                    item => item.key !== "export"
                );
            }
        }
        return items;
    }
});

patch(FormController.prototype, {
    setup() {
        super.setup();
        this.restrictions = {};

        onWillStart(async () => {
            if (this.props.resModel) {
                this.restrictions = await checkRestrictions(this.props.resModel);
            }
        });
    },

    get actionMenuItems() {
        const items = super.actionMenuItems;
        if (items?.action) {
            if (this.restrictions.disable_archive) {
                items.action = items.action.filter(
                    item => !["archive", "unarchive"].includes(item.key)
                );
            }
            if (this.restrictions.disable_export) {
                items.action = items.action.filter(
                    item => item.key !== "export"
                );
            }
        }
        return items;
    }
});

patch(ExportAll.prototype, {
    setup() {
        super.setup();
        this.restricted = false;
        this.actionService = useService("action");
        this.env = useEnv();

        onWillStart(async () => {
            if (user.userId) {
                try {
                     const modelName = this.env.searchModel && this.env.searchModel.resModel;

                    if (modelName) {
                        const restrictions = await rpc('/access_rights/check_restrictions', {
                            user_id: user.userId,
                            model_name: modelName
                        });
                        this.restricted = restrictions.disable_export;
                    }
                } catch (error) {
                    console.error("Failed to check export restriction:", error);
                    this.restricted = false;
                }
            }
        });
    },

    get canExport() {
        return !this.restricted && super.canExport;
    }
});