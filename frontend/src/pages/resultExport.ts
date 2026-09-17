const DEFAULT_API_BASE_URL = "http://localhost:8000";

export class AssessmentExportError extends Error {
  status: number | null;

  constructor(message: string, status: number | null = null) {
    super(message);
    this.name = "AssessmentExportError";
    this.status = status;
  }
}

function getApiBaseUrl(): string {
  const configured = import.meta.env.VITE_API_BASE_URL?.trim();
  return configured || DEFAULT_API_BASE_URL;
}

function buildExportUrl(assessmentId: string): string {
  return new URL(`/api/assessments/${assessmentId}/export.pdf`, getApiBaseUrl()).toString();
}

function parseFilenameFromDisposition(header: string | null): string | null {
  if (!header) return null;

  const utf8Match = header.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match?.[1]) {
    return decodeURIComponent(utf8Match[1]);
  }

  const quotedMatch = header.match(/filename="([^"]+)"/i);
  if (quotedMatch?.[1]) {
    return quotedMatch[1];
  }

  const plainMatch = header.match(/filename=([^;]+)/i);
  if (plainMatch?.[1]) {
    return plainMatch[1].trim();
  }

  return null;
}

async function readErrorMessage(response: Response): Promise<string> {
  const contentType = response.headers.get("content-type") || "";

  if (contentType.includes("application/json")) {
    const payload = (await response.json()) as Record<string, unknown>;
    const detail = payload.detail;
    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }
    const message = payload.message;
    if (typeof message === "string" && message.trim()) {
      return message;
    }
  }

  const text = (await response.text()).trim();
  if (text) {
    return text;
  }

  if (response.status === 409) {
    return "结果尚未完成，暂时不能导出 PDF";
  }
  if (response.status === 404) {
    return "当前结果不存在，无法导出 PDF。";
  }
  return "导出 PDF 失败，请稍后重试。";
}

export async function exportAssessmentToPdf(assessmentId: string): Promise<string> {
  let response: Response;

  try {
    response = await fetch(buildExportUrl(assessmentId), {
      method: "GET",
      credentials: "include"
    });
  } catch (error) {
    if (typeof navigator !== "undefined" && navigator.onLine === false) {
      throw new AssessmentExportError("网络连接已断开，请恢复网络后重试。");
    }
    throw new AssessmentExportError(
      error instanceof Error ? error.message : "网络连接不可用，请稍后重试。"
    );
  }

  if (!response.ok) {
    throw new AssessmentExportError(await readErrorMessage(response), response.status);
  }

  const blob = await response.blob();
  const filename =
    parseFilenameFromDisposition(response.headers.get("content-disposition")) ||
    `yasi-assessment-${assessmentId}.pdf`;

  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filename;
  anchor.rel = "noopener";
  anchor.style.display = "none";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 0);
  return filename;
}
