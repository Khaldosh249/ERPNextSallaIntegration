# Events module for Salla Integration
# ERPNext document event handlers

from salla_integration.events.item_events import (
    on_item_update,
    on_item_insert,
    before_item_delete,
)
from salla_integration.events.stock_events import (
    on_stock_entry_submit,
    on_stock_entry_cancel,
)
from salla_integration.events.order_events import (
    on_delivery_note_submit,
)
from salla_integration.events.salla_category_events import (
    on_salla_category_update,
    on_salla_category_insert,
    before_salla_category_delete,
)

__all__ = [
    "on_item_update",
    "on_item_insert",
    "before_item_delete",
    "on_stock_entry_submit",
    "on_stock_entry_cancel",
    "on_delivery_note_submit",
    "on_salla_category_update",
    "on_salla_category_insert",
    "before_salla_category_delete",
]
