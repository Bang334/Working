import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const [sourcePath, targetPath, outputDir] = process.argv.slice(2);
await fs.mkdir(outputDir, { recursive: true });

async function loadWorkbook(filePath) {
  const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(filePath));
  workbook.recalculate();
  return workbook;
}

async function scanErrors(workbook, label) {
  const errors = await workbook.inspect({
    kind: "match",
    searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!",
    options: { useRegex: true, maxResults: 300 },
    summary: `${label} formula error scan`,
  });
  console.log(errors.ndjson);
}

async function inspectRange(workbook, range) {
  const result = await workbook.inspect({
    kind: "table",
    range,
    include: "values,formulas",
    tableMaxRows: 40,
    tableMaxCols: 12,
    maxChars: 25000,
  });
  console.log(result.ndjson);
}

async function renderSheets(workbook, names, prefix) {
  for (const sheetName of names) {
    const preview = await workbook.render({
      sheetName,
      autoCrop: "all",
      scale: 1,
      format: "png",
    });
    const safeName = sheetName.replace(/[\\/:*?"<>|]/g, "_");
    const outputPath = path.join(outputDir, `${prefix}_${safeName}.png`);
    await fs.writeFile(outputPath, new Uint8Array(await preview.arrayBuffer()));
    console.log(JSON.stringify({ sheetName, outputPath }));
  }
}

const source = await loadWorkbook(sourcePath);
await inspectRange(source, "CX Technology (VN)!A10:I34");
await inspectRange(source, "Sheet1!A9:J33");
await scanErrors(source, "source");
await renderSheets(source, ["CX Technology (VN)", "Sheet1"], "source");

const target = await loadWorkbook(targetPath);
await inspectRange(target, "Nghiệm Thu!A19:G20");
for (const range of [
  "RFR900NA55RSVHBA036!A1:D8",
  "EF550R4ALAWBH109!A1:F9",
  "EF550R4ALAWBI661!A1:F8",
  "EF550R4ALAWBI677!A1:F8",
  "EF550RA4LAWBI666!A1:F8",
  "EF550RA4LAWBI678!A1:F8",
  "EF550R4ALAWBI670!A1:F8",
]) {
  await inspectRange(target, range);
}
await scanErrors(target, "target");
await renderSheets(
  target,
  [
    "Nghiệm Thu",
    "RFR900NA55RSVHBA036",
    "EF550R4ALAWBH109",
    "EF550R4ALAWBI661",
    "EF550R4ALAWBI677",
    "EF550RA4LAWBI666",
    "EF550RA4LAWBI678",
    "EF550R4ALAWBI670",
  ],
  "target",
);
