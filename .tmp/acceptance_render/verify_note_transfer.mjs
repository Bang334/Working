import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const [inputPath, outputDir] = process.argv.slice(2);
await fs.mkdir(outputDir, { recursive: true });

const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(inputPath));
workbook.recalculate();

for (const range of [
  "Nghiệm Thu!A19:G20",
  "RFR900NA55RSVHBA036!A1:D8",
  "EF550RA4LAWBI666!A1:F8",
  "EF550RA4LAWBI678!A1:F8",
  "EF550R4ALAWBI670!A1:F8",
]) {
  const inspected = await workbook.inspect({
    kind: "table",
    range,
    include: "values,formulas",
    tableMaxRows: 10,
    tableMaxCols: 8,
    maxChars: 7000,
  });
  console.log(inspected.ndjson);
}

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!",
  options: { useRegex: true, maxResults: 300 },
  summary: "final formula error scan",
});
console.log(errors.ndjson);

for (const sheetName of [
  "Nghiệm Thu",
  "RFR900NA55RSVHBA036",
  "EF550RA4LAWBI666",
  "EF550RA4LAWBI678",
  "EF550R4ALAWBI670",
]) {
  const preview = await workbook.render({
    sheetName,
    autoCrop: "all",
    scale: 1,
    format: "png",
  });
  const safeName = sheetName.replace(/[\\/:*?"<>|]/g, "_");
  const outputPath = path.join(outputDir, `${safeName}.png`);
  await fs.writeFile(outputPath, new Uint8Array(await preview.arrayBuffer()));
  console.log(JSON.stringify({ sheetName, outputPath }));
}
