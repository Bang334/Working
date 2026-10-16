# Payment Request Word Template Contract

## Reference

- Path: `E:\Working\Bieu Mau\đơn yêu cầu NCC thanh toán-Gốc.docx`
- SHA-256: `6615b9c3e98d3d68ca8fe29d24eff81480570615bfb7a5a0499f88846b6cd1c8`
- Pages: 1
- Sections: 1
- Reference render: `template-render/page-1.png`
- Style evidence: `template-style-evidence.json`

## Page system

- A4 portrait, 8.27 x 11.69 inches.
- Margins: left 0.30, right 0.30, top 0.33, bottom 0.33 inches.
- One section, normal first page, linked default header and footer, no visible header or footer content.
- The generated payment request must remain exactly one page.

## Typography and color

- Retain every existing paragraph and run property.
- The title is 17 pt black and bold.
- Section labels are 9.5 pt dark blue `1F4E79` and bold.
- Table content uses the source's Microsoft JhengHei and Arial run formatting.
- Each payment-term row has two paragraphs. The numeric prefix is Arial 9.5 pt, blue `2E75B6`, bold; the Chinese body is Microsoft JhengHei 8 pt, black; the Vietnamese body is 8 pt, black.

## Tables and components

- Preserve five tables with row/column grids: 1x2 header, 4x6 metadata, 3x9 payment detail, 4x1 payment terms, 4x4 bank/signature block.
- Preserve all table grids, merged cells, widths, fills, borders, cell margins, paragraph properties, and row settings.
- Preserve all five body paragraphs and their order: title, payment-content heading, payment-terms heading, VAT note, bank-information heading, plus the trailing spacer paragraph.
- No drawings, fields, or content controls are present.

## Editable slot map

- Header table: form number only.
- Metadata table: customer name, application date, contract/project text, due date. Payment method remains fixed.
- Payment-detail table: item number, payment item, currency, contract values, quantity, tax values, requested amount, and total.
- Payment-terms table: update text inside the existing four rows. Keep row count unchanged; blank unused rows without deleting them.
- Bank and signature table: preserve unchanged.

## Package preservation

- Preserve package relationships, theme, settings, custom XML, numbering, styles, web settings, font table, and document properties.
- Only text nodes in the documented editable slots may change. All section geometry and table grids must match the reference.
- Source package contains 16 parts. Key preserve-only hashes include styles `c5a378d66de36f4fbdb1e9a1f4b30b2deae2c9b968333cf98e857d7d7db81b0f`, numbering `6d1a57f0a131a4f1902615aae57d3fd27ac15a93805fe495cdf0756206cb3920`, theme `b2295d3198893d2c03f5e584c749a15751b798aefdcd9bee2889f13903d68cb2`, and document relationships `14e2469320c6c093096066505e35f3c94b2eb61b47eecb47ef2585ae3dc64222`.

## Fidelity gates

- The reference remains byte-for-byte unchanged at the recorded hash.
- The final document renders as one clean page with no clipping, overlap, hidden text, broken table, or missing signature label.
- Section geometry, table count, table dimensions, and table grids match the reference.
- The payment-term run styles remain separated as specified above.
