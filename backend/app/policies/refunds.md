# Refund & Compensation Policy

## Processing Timeline (REF-TIME-01)
- **Inspection:** After the warehouse receives a return, allow **3–5 business days** for inspection.
- **Bank Posting:** After a refund is issued, allow **5–10 business days** for the bank to post the credit.

## Refund Methods (REF-METH-02)
### Original Payment Method (REF-METH-02A)
- Default refund method for non-gift orders.

### Store Credit (Gift Card) (REF-METH-02B)
- If a customer chooses store credit:
  - the **$8.00 return shipping fee is waived**
  - credit may be issued upon the first carrier scan of the return label (instant credit), subject to internal trust checks

## Deductions & Fees (REF-FEE-03)
### Return Shipping Fee (REF-FEE-03A)
- A flat **$8.00** is deducted from the refund total for **Customer Preference** returns (see `returns.md`, `RET-REASON-05A`).

### Outbound Shipping (REF-FEE-03B)
- Original outbound shipping charges (example: **$15 overnight shipping**) are **non-refundable** unless the return is classified as **Vendor Error** (see `returns.md`, `RET-REASON-05B`).

### Restocking Fee (REF-FEE-03C)
A **15% restocking fee** applies only when either condition is true:
- **High Value:** any item priced **over $500**, or
- **Bulk:** **5+ units of the same SKU** in the order

## Partial Refunds (REF-PART-04)
- Partial refunds (e.g., “keep the item for 20% off”) are not offered.
- Resolution is binary:
  - return the item for a full refund/store credit (subject to applicable fees), or
  - keep the item with no refund
- Exception:
  - if a replacement is approved under Warranty but the SKU is out of stock, a refund may be issued (see `warranty.md`, `WAR-RES-05`).

## Gift Returns (REF-GIFT-05)
- For orders marked as gifts, refunds must be issued as **store credit** linked to the **gift recipient email**.
- Do not issue refunds to the original payment method for gift orders.

## Refund Amount Calculation Rules (REF-AMT-06)
Refund amount is computed as:

1. **Start with item subtotal** for the returned items.
2. **Subtract** applicable fees:
   - subtract **$8.00** if classified as **Customer Preference** (`REF-FEE-03A`)
   - subtract **15% restocking fee** if High Value or Bulk (`REF-FEE-03C`)
3. **Outbound shipping**:
   - do **not** refund outbound shipping unless Vendor Error (`REF-FEE-03B`)
4. Never refund more than the amount paid for the returned items.