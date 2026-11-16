-- C1. 
SELECT *
FROM parts
WHERE category = 'Mechanical';


-- C2. 
SELECT part_id, part_name, category, unit_price
FROM parts
WHERE unit_price > 1000
ORDER BY unit_price DESC;


-- C3. 
SELECT category,
       ROUND(AVG(unit_price), 2) AS avg_unit_price
FROM parts
GROUP BY category
ORDER BY category;


-- C4. 
SELECT category,
       SUM(stock_qty) AS total_stock_qty
FROM parts
GROUP BY category
ORDER BY category;


-- C5. 
SELECT po.po_id,
       s.supplier_name,
       po.order_date,
       po.status
FROM purchase_orders po
JOIN suppliers s ON s.supplier_id = po.supplier_id
ORDER BY po.po_id;


-- C6.
SELECT po.po_id,
       p.part_name,
       poi.quantity,
       p.unit_price
FROM purchase_orders po
JOIN purchase_order_items poi ON poi.po_id = po.po_id
JOIN parts p ON p.part_id = poi.part_id
ORDER BY po.po_id, p.part_name;


-- C7. 
SELECT po.po_id,
       p.part_name,
       poi.quantity,
       p.unit_price,
       poi.quantity * p.unit_price AS line_total
FROM purchase_orders po
JOIN purchase_order_items poi ON poi.po_id = po.po_id
JOIN parts p ON p.part_id = poi.part_id
ORDER BY po.po_id, p.part_name;


-- C8. 
SELECT s.supplier_id,
       s.supplier_name,
       s.city,
       po.po_id,
       po.order_date,
       po.status
FROM suppliers s
LEFT JOIN purchase_orders po ON po.supplier_id = s.supplier_id
ORDER BY s.supplier_id, po.po_id;


-- C9. 
SELECT s.supplier_id,
       s.supplier_name,
       s.city
FROM suppliers s
LEFT JOIN purchase_orders po ON po.supplier_id = s.supplier_id
WHERE po.po_id IS NULL
ORDER BY s.supplier_id;


-- C10. 
CREATE OR REPLACE VIEW purchase_order_summary AS
SELECT po.po_id,
       s.supplier_name,
       p.part_name,
       poi.quantity,
       p.unit_price,
       poi.quantity * p.unit_price AS line_total,
       po.status
FROM purchase_orders po
JOIN suppliers s ON s.supplier_id = po.supplier_id
JOIN purchase_order_items poi ON poi.po_id = po.po_id
JOIN parts p ON p.part_id = poi.part_id;

SELECT *
FROM purchase_order_summary
WHERE status = 'Pending'
ORDER BY po_id;


-- C11.
-- Returns 10 percent of amount when amount >= 2000, otherwise 0.
CREATE OR REPLACE FUNCTION calculate_part_discount(amount NUMERIC)
RETURNS NUMERIC
LANGUAGE plpgsql
AS $$
BEGIN
    IF amount >= 2000 THEN
        RETURN amount * 0.10;
    ELSE
        RETURN 0;
    END IF;
END;
$$;

SELECT part_id,
       part_name,
       unit_price,
       calculate_part_discount(unit_price) AS discount
FROM parts
ORDER BY part_id;


-- C12. 
CREATE OR REPLACE FUNCTION final_part_price(amount NUMERIC)
RETURNS NUMERIC
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN amount - calculate_part_discount(amount);
END;
$$;

-- Use it in a SELECT query
SELECT part_id,
       part_name,
       unit_price,
       calculate_part_discount(unit_price) AS discount,
       final_part_price(unit_price)        AS final_price
FROM parts
ORDER BY part_id;


-- C13. 
CREATE OR REPLACE PROCEDURE update_po_status(p_po_id INT, p_new_status VARCHAR)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE purchase_orders
    SET status = p_new_status
    WHERE po_id = p_po_id;
END;
$$;

-- Before the call
SELECT po_id, status FROM purchase_orders WHERE po_id = 1004;

-- Call it once: change PO 1004 from Pending to Received
CALL update_po_status(1004, 'Received');

-- Verify the result
SELECT po_id, status FROM purchase_orders WHERE po_id = 1004;


-- C14. 
-- Changes Pending orders dated before 2026-10-04 to Received.
CREATE OR REPLACE PROCEDURE mark_old_pending_orders()
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE purchase_orders
    SET status = 'Received'
    WHERE status = 'Pending'
      AND order_date < DATE '2026-10-04';
END;
$$;

-- Before the call
SELECT po_id, order_date, status FROM purchase_orders ORDER BY po_id;

-- Run it
CALL mark_old_pending_orders();

-- Verify the results
SELECT po_id, order_date, status FROM purchase_orders ORDER BY po_id;


-- C15. Normalization
-- Imagine one large table with these columns repeated on every row:
--   supplier_name, supplier_city, part_name, part_category, po_id, quantity
--
-- Repeated facts:
--   1. Supplier facts. supplier_name and supplier_city are repeated for
--      every order line of that supplier. Axis Components, Rajkot would be
--      stored again for each item on each of its orders.
--   2. Part facts. part_name and part_category are repeated every time
--      the same part is ordered. Hydraulic Seal, Mechanical would appear
--      on every order that contains it.
--   3. Order facts. po_id is repeated for each item on the same order.
--
-- Problems this causes:
--   Update anomaly: if a supplier moves city, many rows must be changed.
--   Insert anomaly: a new supplier or part cannot be stored until it has
--   been ordered at least once.
--   Delete anomaly: deleting the last order of a part also deletes the
--   only record that the part exists.
--
-- How to separate the data (this is the structure already used in the
-- setup script, and it satisfies third normal form):
--   suppliers (supplier_id PK, supplier_name, city)
--   parts (part_id PK, part_name, category, unit_price, stock_qty)
--   purchase_orders (po_id PK, supplier_id FK, order_date, status)
--   purchase_order_items (po_item_id PK, po_id FK, part_id FK, quantity)
--
-- Each fact is stored once. The foreign keys connect the tables, and a
-- JOIN rebuilds the original wide view whenever it is needed.
