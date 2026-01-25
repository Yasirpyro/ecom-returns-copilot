# Return Policy Guidelines

## Definitions (RET-DEF-01)
- **Delivery Date:** The timestamp when the carrier tracking status first changes to **Delivered**.
- **Initiate Return:** The timestamp when a return request is successfully submitted in the return portal (not when the label is scanned).
- **Vendor Error:** A return reason where the fault lies with the company. Vendor Error is strictly limited to:
  1. **Wrong item sent** (incorrect SKU/size received vs. ordered).
  2. **Item arrived damaged** (visible damage on arrival: crushed packaging, torn product, broken hardware on arrival).
  3. **Manufacturing defect** (eligible under the Warranty Policy; see `warranty.md`).

## Return Window Eligibility (RET-ELIG-02)
- **Standard Window:** Returns may be initiated within **30 days** of the Delivery Date.
- **Holiday Extension:** Orders placed between **November 15** and **December 25** may be initiated until **January 31** of the following year.
- **Outside Window:** Requests outside the eligible window require **manual review**.

## Item Condition Requirements (RET-COND-03)
To be eligible for a standard return, items must meet the **Resalable Standard**:
1. **Tags attached:** Original hangtags are intact.
2. **Unworn & unwashed:** Free of odors, fragrances, pet hair, and deodorant marks.
3. **Original packaging:** Footwear must be returned in the original shoebox (no shipping labels placed directly on the shoebox).

## Non-Returnable Items / Final Sale (RET-EXCL-04)
The following items are not eligible for return:
- **Intimates & Swimwear:** bottoms/bodysuits/swimwear with a missing or tampered hygiene liner.
- **Clearance / Final Sale:** any item marked **Final Sale** at checkout or priced ending in **.97**.
- **Gift Cards:** non-refundable and non-returnable.
- **Custom/Personalized Items:** monogrammed or altered items.

## Return Reasons & Classification (RET-REASON-05)
Return requests must include a reason. Reason classification determines fees and handling:

### Customer Preference (RET-REASON-05A)
Examples:
- “Doesn’t fit”
- “Changed mind”
- “Ordered wrong size”
- “Color looked different online”

Rules:
- Subject to the **Return Shipping Fee** (see `refunds.md`, `REF-FEE-03`).

### Vendor Error (RET-REASON-05B)
Examples:
- “Wrong item sent”
- “Arrived damaged”

Rules:
- **Return Shipping Fee is waived** (see `refunds.md`, `REF-FEE-03`).
- If damage is reported, see photo requirements in `warranty.md`, `WAR-CLAIM-04`.

## Late Return Handling (RET-LATE-06)
- Late returns are not approved automatically.
- A late request must be routed for manual review with:
  - order_id
  - delivery date
  - requested reason
  - any provided evidence (photos)