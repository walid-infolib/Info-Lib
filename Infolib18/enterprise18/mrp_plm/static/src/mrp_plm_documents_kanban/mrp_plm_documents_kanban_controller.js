/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ProductDocumentKanbanController } from "@product/js/product_document_kanban/product_document_kanban_controller";

patch(ProductDocumentKanbanController.prototype, {
    setup() {
        super.setup(...arguments);
        if (this.props.context.eco_bom) {
            this.formData.eco_bom = true;
        }
    },
});