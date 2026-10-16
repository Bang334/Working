/**
 * API Client for Hong Ming Global PM Portal
 */

const ApiClient = {
  /**
   * Send raw prompt, table text or attached files (image, Excel, Word) to Gemini AI for parsing
   */
  async parseWithAI(rawText, modelName, fileData = null) {
    const payload = {
      raw_text: rawText || "",
      model_name: modelName || null
    };

    if (fileData && fileData.base64) {
      payload.file_base64 = fileData.base64;
      payload.file_name = fileData.name || "upload_file";
      payload.file_mime = fileData.mime || "application/octet-stream";
    }

    const response = await fetch("/api/v1/ai/parse-contract", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!response.ok) {
      throw new Error(`Lỗi máy chủ (${response.status}): ${response.statusText}`);
    }
    return await response.json();
  },

  /**
   * Generate official Word (.docx) file
   */
  async generateDocx(contractData) {
    const response = await fetch("/api/v1/contracts/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(contractData)
    });
    if (!response.ok) {
      throw new Error(`Lỗi máy chủ (${response.status}): ${response.statusText}`);
    }
    return await response.json();
  },

  /**
   * Request updated live preview HTML from backend
   */
  async getLivePreview(contractData) {
    const response = await fetch("/api/v1/contracts/preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(contractData)
    });
    if (!response.ok) {
      throw new Error(`Lỗi cập nhật xem trước (${response.status})`);
    }
    return await response.json();
  }
};
