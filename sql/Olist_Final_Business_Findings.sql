USE olist_project;

-- ==========================================
-- OLIST E-COMMERCE PROJECT
-- FINAL BUSINESS FINDINGS
-- ==========================================

-- Finding 1: Delivery Performance & Customer Satisfaction
-- Query 1: What percentage of delivered orders were late?

USE olist_project;

SELECT
    COUNT(DISTINCT order_id) AS total_delivered_orders,

    COUNT(DISTINCT CASE
        WHEN order_delivered_customer_date >
             order_estimated_delivery_date
        THEN order_id
    END) AS late_orders,

    ROUND(
        100.0 * COUNT(DISTINCT CASE
            WHEN order_delivered_customer_date >
                 order_estimated_delivery_date
            THEN order_id
        END) / COUNT(DISTINCT order_id),
        2
    ) AS late_delivery_percentage

FROM olist_orders_dataset

WHERE order_status = 'delivered'
  AND order_delivered_customer_date IS NOT NULL
  AND order_estimated_delivery_date IS NOT NULL;
  

-- Query 2: Analyse late delivery severity

SELECT
    COUNT(*) AS late_orders,

    ROUND(
        AVG(DATEDIFF(
            order_delivered_customer_date,
            order_estimated_delivery_date
        )),
        2
    ) AS average_days_late,

    MAX(DATEDIFF(
        order_delivered_customer_date,
        order_estimated_delivery_date
    )) AS maximum_days_late

FROM olist_orders_dataset

WHERE order_status = 'delivered'
  AND order_delivered_customer_date IS NOT NULL
  AND order_estimated_delivery_date IS NOT NULL
  AND order_delivered_customer_date > order_estimated_delivery_date;
  
  
  -- Query 3: Compare customer satisfaction for late vs on-time orders
-- Average review score per order avoids counting duplicate review rows

SELECT
    delivery_status,
    COUNT(*) AS orders_with_reviews,
    ROUND(AVG(order_average_review), 2) AS average_review_score,
    ROUND(
        100.0 * SUM(CASE WHEN order_average_review <= 2 THEN 1 ELSE 0 END)
        / COUNT(*),
        2
    ) AS low_review_percentage

FROM (
    SELECT
        o.order_id,
        CASE
            WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date
                THEN 'Late'
            ELSE 'On-time or Early'
        END AS delivery_status,
        AVG(r.review_score) AS order_average_review
    FROM olist_orders_dataset AS o
    JOIN olist_order_reviews_dataset AS r
        ON o.order_id = r.order_id
    WHERE o.order_status = 'delivered'
      AND o.order_delivered_customer_date IS NOT NULL
      AND o.order_estimated_delivery_date IS NOT NULL
    GROUP BY o.order_id, delivery_status
) AS order_review_data
GROUP BY delivery_status;

-- Finding 2: Customer Retention Analysis
-- Query 1: Calculate customer repeat purchase rate within 90 days

WITH delivered_customer_orders AS (
    SELECT
        c.customer_unique_id,
        o.order_id,
        o.order_purchase_timestamp
    FROM olist_orders_dataset AS o
    JOIN olist_customers_dataset AS c
        ON o.customer_id = c.customer_id
    WHERE o.order_status = 'delivered'
      AND o.order_purchase_timestamp IS NOT NULL
),

first_purchase AS (
    SELECT
        customer_unique_id,
        MIN(order_purchase_timestamp) AS first_order_date
    FROM delivered_customer_orders
    GROUP BY customer_unique_id
),

eligible_customers AS (
    SELECT
        customer_unique_id,
        first_order_date
    FROM first_purchase
    WHERE first_order_date <= '2018-05-31'
),

customer_90_day_orders AS (
    SELECT
        e.customer_unique_id,
        COUNT(DISTINCT d.order_id) AS total_orders_90_days
    FROM eligible_customers AS e
    JOIN delivered_customer_orders AS d
        ON e.customer_unique_id = d.customer_unique_id
       AND d.order_purchase_timestamp >= e.first_order_date
       AND d.order_purchase_timestamp <=
           DATE_ADD(e.first_order_date, INTERVAL 90 DAY)
    GROUP BY e.customer_unique_id
)

SELECT
    COUNT(*) AS eligible_customers,

    SUM(CASE
        WHEN total_orders_90_days > 1 THEN 1
        ELSE 0
    END) AS repeat_customers,

    SUM(CASE
        WHEN total_orders_90_days = 1 THEN 1
        ELSE 0
    END) AS one_time_customers,

    SUM(CASE
        WHEN total_orders_90_days > 1
        THEN total_orders_90_days - 1
        ELSE 0
    END) AS additional_repeat_orders,

    ROUND(
        100.0 * SUM(CASE
            WHEN total_orders_90_days > 1 THEN 1
            ELSE 0
        END) / COUNT(*),
        2
    ) AS repeat_customer_percentage

FROM customer_90_day_orders;


-- Query 2: Compare revenue from repeat and non-repeat customers
-- Use the same 90-day observation window for both groups

WITH order_payments AS (
    SELECT
        order_id,
        SUM(payment_value) AS order_payment_total
    FROM olist_order_payments_dataset
    GROUP BY order_id
),

customer_orders AS (
    SELECT
        c.customer_unique_id,
        o.order_id,
        o.order_purchase_timestamp,
        p.order_payment_total
    FROM olist_customers_dataset AS c
    JOIN olist_orders_dataset AS o
        ON c.customer_id = o.customer_id
    LEFT JOIN order_payments AS p
        ON o.order_id = p.order_id
    WHERE o.order_status = 'delivered'
),

customer_first_order AS (
    SELECT
        customer_unique_id,
        MIN(order_purchase_timestamp) AS first_order_date
    FROM customer_orders
    GROUP BY customer_unique_id
),

eligible_customers AS (
    SELECT
        customer_unique_id,
        first_order_date
    FROM customer_first_order
    WHERE first_order_date <= '2018-05-31'
),

customer_90_day_revenue AS (
    SELECT
        e.customer_unique_id,
        SUM(o.order_payment_total) AS revenue_90_days,
        COUNT(DISTINCT o.order_id) AS orders_90_days
    FROM eligible_customers AS e
    JOIN customer_orders AS o
        ON e.customer_unique_id = o.customer_unique_id
       AND o.order_purchase_timestamp >= e.first_order_date
       AND o.order_purchase_timestamp <= DATE_ADD(
            e.first_order_date,
            INTERVAL 90 DAY
       )
    GROUP BY e.customer_unique_id
),

repeat_customers AS (
    SELECT
        customer_unique_id
    FROM customer_90_day_revenue
    WHERE orders_90_days > 1
)

SELECT
    CASE
        WHEN r.customer_unique_id IS NOT NULL
            THEN 'Repeat within 90 days'
        ELSE 'No repeat within 90 days'
    END AS customer_group,

    COUNT(*) AS customers,

    ROUND(SUM(cr.revenue_90_days), 2) AS total_revenue_90_days,

    ROUND(AVG(cr.revenue_90_days), 2) AS average_revenue_per_customer,

    ROUND(AVG(cr.orders_90_days), 2) AS average_orders_per_customer

FROM customer_90_day_revenue AS cr
LEFT JOIN repeat_customers AS r
    ON cr.customer_unique_id = r.customer_unique_id

GROUP BY customer_group;


-- Finding 3: Dispatch Delay & Late Delivery
-- Query 1: Average time taken to hand over orders to the carrier
SELECT
    COUNT(*) AS total_orders,

    ROUND(
        AVG(TIMESTAMPDIFF(
            HOUR,
            order_approved_at,
            order_delivered_carrier_date
        )),
        2
    ) AS average_dispatch_hours,

    MAX(TIMESTAMPDIFF(
        HOUR,
        order_approved_at,
        order_delivered_carrier_date
    )) AS maximum_dispatch_hours

FROM olist_orders_dataset

WHERE order_status = 'delivered'
  AND order_approved_at IS NOT NULL
  AND order_delivered_carrier_date IS NOT NULL
  AND order_delivered_carrier_date >= order_approved_at;


-- Query 2: Compare late delivery rates based on dispatch time
WITH dispatch_analysis AS (
    SELECT
        order_id,

        TIMESTAMPDIFF(
            HOUR,
            order_approved_at,
            order_delivered_carrier_date
        ) AS dispatch_hours,

        CASE
            WHEN order_delivered_customer_date >
                 order_estimated_delivery_date
            THEN 1
            ELSE 0
        END AS is_late

    FROM olist_orders_dataset

    WHERE order_status = 'delivered'
      AND order_approved_at IS NOT NULL
      AND order_delivered_carrier_date IS NOT NULL
      AND order_delivered_customer_date IS NOT NULL
      AND order_estimated_delivery_date IS NOT NULL
      AND order_delivered_carrier_date >= order_approved_at
),

dispatch_groups AS (
    SELECT
        CASE
            WHEN dispatch_hours <= 24 THEN 'Within 1 day'
            WHEN dispatch_hours <= 48 THEN '1-2 days'
            WHEN dispatch_hours <= 72 THEN '2-3 days'
            WHEN dispatch_hours <= 168 THEN '3-7 days'
            ELSE 'More than 7 days'
        END AS dispatch_category,

        CASE
            WHEN dispatch_hours <= 24 THEN 1
            WHEN dispatch_hours <= 48 THEN 2
            WHEN dispatch_hours <= 72 THEN 3
            WHEN dispatch_hours <= 168 THEN 4
            ELSE 5
        END AS sort_order,

        is_late

    FROM dispatch_analysis
)

SELECT
    dispatch_category,

    COUNT(*) AS total_orders,

    SUM(is_late) AS late_orders,

    ROUND(
        100.0 * SUM(is_late) / COUNT(*),
        2
    ) AS late_delivery_percentage

FROM dispatch_groups

GROUP BY dispatch_category, sort_order
ORDER BY sort_order;


-- Finding 4: Seller Customer Satisfaction
-- Query 1: Seller-wise low customer ratings

WITH single_seller_orders AS (
    SELECT
        oi.order_id,
        MIN(oi.seller_id) AS seller_id
    FROM olist_order_items_dataset AS oi
    JOIN olist_orders_dataset AS o
        ON oi.order_id = o.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY oi.order_id
    HAVING COUNT(DISTINCT oi.seller_id) = 1
),

order_reviews AS (
    SELECT
        order_id,
        AVG(review_score) AS avg_review_score
    FROM olist_order_reviews_dataset
    WHERE review_score IS NOT NULL
    GROUP BY order_id
),

seller_performance AS (
    SELECT
        s.seller_id,
        COUNT(*) AS reviewed_orders,

        SUM(
            CASE WHEN r.avg_review_score <= 2
            THEN 1 ELSE 0 END
        ) AS low_rating_orders,

        ROUND(
            100.0 * SUM(
                CASE WHEN r.avg_review_score <= 2
                THEN 1 ELSE 0 END
            ) / COUNT(*),
            2
        ) AS low_rating_percentage

    FROM single_seller_orders AS s
    JOIN order_reviews AS r
        ON s.order_id = r.order_id
    GROUP BY s.seller_id
    HAVING COUNT(*) >= 50
),

overall_benchmark AS (
    SELECT
        ROUND(
            100.0 * SUM(
                CASE WHEN r.avg_review_score <= 2
                THEN 1 ELSE 0 END
            ) / COUNT(*),
            2
        ) AS overall_low_rating_percentage

    FROM single_seller_orders AS s
    JOIN order_reviews AS r
        ON s.order_id = r.order_id
)

SELECT
    sp.seller_id,
    sp.reviewed_orders,
    sp.low_rating_orders,
    sp.low_rating_percentage,
    ob.overall_low_rating_percentage

FROM seller_performance AS sp
CROSS JOIN overall_benchmark AS ob

ORDER BY sp.low_rating_percentage DESC;

-- Query 2 : Count sellers above and below the overall
-- low-rating benchmark

WITH single_seller_orders AS (
    SELECT
        oi.order_id,
        MIN(oi.seller_id) AS seller_id
    FROM olist_order_items_dataset AS oi
    JOIN olist_orders_dataset AS o
        ON oi.order_id = o.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY oi.order_id
    HAVING COUNT(DISTINCT oi.seller_id) = 1
),

order_reviews AS (
    SELECT
        order_id,
        AVG(review_score) AS avg_review_score
    FROM olist_order_reviews_dataset
    WHERE review_score IS NOT NULL
    GROUP BY order_id
),

seller_performance AS (
    SELECT
        s.seller_id,
        COUNT(*) AS reviewed_orders,
        SUM(CASE WHEN r.avg_review_score <= 2
            THEN 1 ELSE 0 END) AS low_rating_orders
    FROM single_seller_orders AS s
    JOIN order_reviews AS r
        ON s.order_id = r.order_id
    GROUP BY s.seller_id
    HAVING COUNT(*) >= 50
),

benchmark AS (
    SELECT
        ROUND(
            100.0 * SUM(CASE WHEN r.avg_review_score <= 2
                THEN 1 ELSE 0 END) / COUNT(*),
            2
        ) AS overall_low_rating_percentage
    FROM single_seller_orders AS s
    JOIN order_reviews AS r
        ON s.order_id = r.order_id
)

SELECT
    CASE
        WHEN 100.0 * sp.low_rating_orders / sp.reviewed_orders
             > b.overall_low_rating_percentage
        THEN 'Above benchmark'
        ELSE 'At or below benchmark'
    END AS seller_group,

    COUNT(*) AS total_sellers

FROM seller_performance AS sp
CROSS JOIN benchmark AS b

GROUP BY seller_group;

-- Finding 5: Installment Payment Behaviour
-- Query 1: Average credit-card payment by installment group

WITH order_payments AS (
    SELECT
        order_id,
        MAX(payment_installments) AS installments,
        SUM(payment_value) AS order_payment
    FROM olist_order_payments_dataset
    WHERE payment_type = 'credit_card'
    GROUP BY order_id
),

installment_groups AS (
    SELECT
        order_id,
        order_payment,
        CASE
            WHEN installments = 1 THEN '1 installment'
            WHEN installments BETWEEN 2 AND 3 THEN '2-3 installments'
            WHEN installments BETWEEN 4 AND 6 THEN '4-6 installments'
            WHEN installments BETWEEN 7 AND 10 THEN '7-10 installments'
            ELSE 'More than 10 installments'
        END AS installment_group
    FROM order_payments
)

SELECT
    installment_group,
    COUNT(*) AS total_orders,
    ROUND(AVG(order_payment), 2) AS average_payment,
    ROUND(SUM(order_payment), 2) AS total_payment

FROM installment_groups

GROUP BY installment_group

ORDER BY
    CASE installment_group
        WHEN '1 installment' THEN 1
        WHEN '2-3 installments' THEN 2
        WHEN '4-6 installments' THEN 3
        WHEN '7-10 installments' THEN 4
        ELSE 5
    END;
    

-- Query 2: Check credit-card orders using multiple payment methods
SELECT
    COUNT(*) AS total_credit_card_orders,

    SUM(
        CASE
            WHEN payment_method_count = 1
            THEN 1 ELSE 0
        END
    ) AS credit_card_only_orders,

    SUM(
        CASE
            WHEN payment_method_count > 1
            THEN 1 ELSE 0
        END
    ) AS mixed_payment_orders,

    ROUND(
        100.0 * SUM(
            CASE
                WHEN payment_method_count > 1
                THEN 1 ELSE 0
            END
        ) / COUNT(*),
        2
    ) AS mixed_payment_percentage

FROM (
    SELECT
        order_id,
        COUNT(DISTINCT payment_type) AS payment_method_count
    FROM olist_order_payments_dataset
    GROUP BY order_id
    HAVING SUM(
        CASE
            WHEN payment_type = 'credit_card'
            THEN 1 ELSE 0
        END
    ) > 0
) AS order_methods;

-- Query 3: Validate payment amount against order value
WITH order_payments AS (
    SELECT
        order_id,
        SUM(payment_value) AS total_payment
    FROM olist_order_payments_dataset
    GROUP BY order_id
    HAVING MAX(
        CASE
            WHEN payment_type = 'credit_card'
            THEN 1 ELSE 0
        END
    ) = 1
),

order_items AS (
    SELECT
        order_id,
        SUM(price + freight_value) AS expected_order_value
    FROM olist_order_items_dataset
    GROUP BY order_id
)

SELECT
    COUNT(*) AS total_orders_checked,

    SUM(
        CASE
            WHEN ABS(p.total_payment - i.expected_order_value) <= 0.01
            THEN 1 ELSE 0
        END
    ) AS matching_orders,

    SUM(
        CASE
            WHEN ABS(p.total_payment - i.expected_order_value) > 0.01
            THEN 1 ELSE 0
        END
    ) AS mismatched_orders,

    ROUND(
        AVG(p.total_payment - i.expected_order_value), 2
    ) AS average_payment_difference,

    ROUND(SUM(p.total_payment), 2) AS total_recorded_payment,

    ROUND(SUM(i.expected_order_value), 2) AS total_expected_order_value

FROM order_payments AS p
JOIN order_items AS i
    ON p.order_id = i.order_id;
    
-- Query 4: Median full-order payment by installment group
WITH order_payments AS (
    SELECT
        order_id,
        SUM(payment_value) AS total_order_payment,
        MAX(
            CASE
                WHEN payment_type = 'credit_card'
                THEN payment_installments
            END
        ) AS installments
    FROM olist_order_payments_dataset
    GROUP BY order_id
    HAVING MAX(
        CASE
            WHEN payment_type = 'credit_card'
            THEN 1 ELSE 0
        END
    ) = 1
),

installment_groups AS (
    SELECT
        order_id,
        total_order_payment,
        CASE
            WHEN installments = 1 THEN '1 installment'
            WHEN installments BETWEEN 2 AND 3 THEN '2-3 installments'
            WHEN installments BETWEEN 4 AND 6 THEN '4-6 installments'
            WHEN installments BETWEEN 7 AND 10 THEN '7-10 installments'
            ELSE 'More than 10 installments'
        END AS installment_group
    FROM order_payments
),

ranked_orders AS (
    SELECT
        installment_group,
        total_order_payment,
        ROW_NUMBER() OVER (
            PARTITION BY installment_group
            ORDER BY total_order_payment
        ) AS row_num,
        COUNT(*) OVER (
            PARTITION BY installment_group
        ) AS total_orders
    FROM installment_groups
)

SELECT
    installment_group,
    MAX(total_orders) AS total_orders,
    ROUND(
        AVG(
            CASE
                WHEN row_num IN (
                    FLOOR((total_orders + 1) / 2),
                    FLOOR((total_orders + 2) / 2)
                )
                THEN total_order_payment
            END
        ), 2
    ) AS median_full_order_payment

FROM ranked_orders

GROUP BY installment_group

ORDER BY MIN(
    CASE installment_group
        WHEN '1 installment' THEN 1
        WHEN '2-3 installments' THEN 2
        WHEN '4-6 installments' THEN 3
        WHEN '7-10 installments' THEN 4
        ELSE 5
    END
);
-- Finding 6: Seller Revenue Concentration
-- Query 1: Top 10 sellers' contribution to total revenue
WITH seller_revenue AS (
    SELECT
        oi.seller_id,
        SUM(oi.price) AS seller_revenue
    FROM olist_order_items_dataset AS oi
    JOIN olist_orders_dataset AS o
        ON oi.order_id = o.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY oi.seller_id
),

top_10 AS (
    SELECT seller_revenue
    FROM seller_revenue
    ORDER BY seller_revenue DESC
    LIMIT 10
)

SELECT
    (SELECT COUNT(*) FROM seller_revenue) AS total_sellers,

    ROUND(
        (SELECT SUM(seller_revenue) FROM seller_revenue), 2
    ) AS total_revenue,

    ROUND(
        (SELECT SUM(seller_revenue) FROM top_10), 2
    ) AS top_10_revenue,

    ROUND(
        100.0 * (SELECT SUM(seller_revenue) FROM top_10) /
        (SELECT SUM(seller_revenue) FROM seller_revenue),
        2
    ) AS top_10_revenue_percentage;
    
-- Query 2: Revenue Contribution of Top 20% Sellers
WITH seller_revenue AS (
    SELECT
        oi.seller_id,
        SUM(oi.price) AS seller_revenue
    FROM olist_order_items_dataset AS oi
    JOIN olist_orders_dataset AS o
        ON oi.order_id = o.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY oi.seller_id
),
ranked_sellers AS (
    SELECT
        seller_id,
        seller_revenue,
        ROW_NUMBER() OVER (
            ORDER BY seller_revenue DESC
        ) AS seller_rank
    FROM seller_revenue
),
seller_count AS (
    SELECT COUNT(*) AS total_sellers
    FROM seller_revenue
)
SELECT
    sc.total_sellers,
    CEIL(sc.total_sellers * 0.20) AS top_20_percent_sellers,
    ROUND(SUM(rs.seller_revenue), 2) AS top_20_percent_revenue,
    ROUND(
        SUM(rs.seller_revenue) * 100.0 /
        (SELECT SUM(seller_revenue) FROM seller_revenue),
        2
    ) AS top_20_percent_revenue_percentage
FROM ranked_sellers AS rs
CROSS JOIN seller_count AS sc
WHERE rs.seller_rank <= CEIL(sc.total_sellers * 0.20)
GROUP BY sc.total_sellers;
