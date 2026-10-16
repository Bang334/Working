import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const [inputPath, outputDir] = process.argv.slice(2);
await fs.mkdir(outputDir, { recursive: true });

const input = await FileBlob.load(inputPath);
const workbook = await SpreadsheetFile.importXlsx(input);
const sheetInfo = await workbook.inspect({
  kind: "sheet",
  include: "id,name",
  maxChars: 10000,
});
console.log(sheetInfo.ndjson);

for (let index = 0; index < workbook.worksheets.items.length; index += 1) {
  const sheet = workbook.worksheets.getItemAt(index);
  const safeName = sheet.name.replace(/[\\/:*?"<>|]/g, "_");
  const preview = await workbook.render({
    sheetName: sheet.name,
    autoCrop: "all",
    scale: 1,
    format: "png",
  });
  const bytes = new Uint8Array(await preview.arrayBuffer());
  const outputPath = path.join(outputDir, `${String(index + 1).padStart(2, "0")}_${safeName}.png`);
  await fs.writeFile(outputPath, bytes);
  console.log(JSON.stringify({ index: index + 1, sheet: sheet.name, outputPath, bytes: bytes.length }));
}
