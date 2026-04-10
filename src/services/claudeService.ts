import Anthropic from "@anthropic-ai/sdk";

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

/**
 * Model selection:
 *  - HAIKU is cheap + fast, used for routine ambiguous-band escalations.
 *  - SONNET is reserved for the hardest calls (HAIKU returns low confidence
 *    or the operator explicitly asks for a second opinion).
 */
export const CLAUDE_MODELS = {
  HAIKU: "claude-haiku-4-5",
  SONNET: "claude-sonnet-4-6",
} as const;

export type ClaudeModel = (typeof CLAUDE_MODELS)[keyof typeof CLAUDE_MODELS];

export interface MarkClassification {
  status: "marked" | "blank" | "ambiguous";
  confidence: number;
  reason: string;
}

const SYSTEM_PROMPT = `You are an OMR (Optical Mark Recognition) expert reviewing scanned answer-sheet boxes from GL/Kent/Bucks-style 11+ exams.

Pupils mark answers by drawing a thin HORIZONTAL LINE across a small rectangular box — they do NOT shade bubbles. Your job is to classify what is in the box.

Classify each box as:
- "marked":    a clear horizontal line (or near-horizontal stroke) crosses the box.
- "blank":     the box is empty, or contains only negligible noise / paper grain.
- "ambiguous": there is a mark but it is unclear — e.g. erasure residue, faint stroke, smudge, dot, or multiple competing marks.

Be conservative: if you would want a human to double-check, return "ambiguous".

Always respond with ONLY a JSON object (no prose, no markdown fences) in this exact shape:
{"status": "marked" | "blank" | "ambiguous", "confidence": <number 0-1>, "reason": "<short explanation>"}`;

const BATCH_SYSTEM_PROMPT = `You are an OMR (Optical Mark Recognition) expert reviewing scanned answer-sheet boxes from GL/Kent/Bucks-style 11+ exams.

Pupils mark answers by drawing a thin HORIZONTAL LINE across a small rectangular box — they do NOT shade bubbles.

For EACH image provided, in order, classify it as:
- "marked":    a clear horizontal line (or near-horizontal stroke) crosses the box.
- "blank":     the box is empty, or contains only negligible noise.
- "ambiguous": there is a mark but it is unclear (erasure, faint, smudge, double mark).

Be conservative: if a human should double-check, use "ambiguous".

Always respond with ONLY a JSON array (no prose, no markdown fences) in this exact shape:
[{"status": "...", "confidence": <0-1>, "reason": "..."}, ...]
The array length MUST equal the number of images provided, and the order MUST match.`;

function extractJson(text: string): string {
  // Strip markdown fences if Claude returns them despite instructions.
  const fenced = text.match(/```(?:json)?\s*([\s\S]*?)```/);
  if (fenced) return fenced[1].trim();
  return text.trim();
}

function fallback(reason: string): MarkClassification {
  return { status: "ambiguous", confidence: 0, reason };
}

/**
 * Classify a single OMR box image. Used by the ambiguous-band escalation path
 * after the OpenCV pre-filter has already triaged the easy cases.
 */
export async function classifyMark(
  base64Image: string,
  model: ClaudeModel = CLAUDE_MODELS.HAIKU
): Promise<MarkClassification> {
  try {
    const response = await client.messages.create({
      model,
      max_tokens: 256,
      system: SYSTEM_PROMPT,
      messages: [
        {
          role: "user",
          content: [
            {
              type: "image",
              source: {
                type: "base64",
                media_type: "image/png",
                data: base64Image,
              },
            },
            { type: "text", text: "Classify this box." },
          ],
        },
      ],
    });

    const textBlock = response.content.find((b) => b.type === "text");
    if (!textBlock || textBlock.type !== "text") {
      return fallback("No text response from Claude");
    }

    const parsed = JSON.parse(extractJson(textBlock.text));
    return {
      status: parsed.status ?? "ambiguous",
      confidence: typeof parsed.confidence === "number" ? parsed.confidence : 0,
      reason: parsed.reason ?? "No reason provided",
    };
  } catch (error) {
    console.error("Claude classification error:", error);
    return fallback("AI processing failed");
  }
}

/**
 * Batch classify multiple OMR box images in a single Claude call.
 * Cuts latency and per-request overhead when many boxes land in the
 * ambiguous band on the same sheet.
 */
export async function batchClassifyMarks(
  base64Images: string[],
  model: ClaudeModel = CLAUDE_MODELS.HAIKU
): Promise<MarkClassification[]> {
  if (base64Images.length === 0) return [];

  try {
    const response = await client.messages.create({
      model,
      max_tokens: 1024,
      system: BATCH_SYSTEM_PROMPT,
      messages: [
        {
          role: "user",
          content: [
            ...base64Images.map((img) => ({
              type: "image" as const,
              source: {
                type: "base64" as const,
                media_type: "image/png" as const,
                data: img,
              },
            })),
            {
              type: "text" as const,
              text: `Classify these ${base64Images.length} boxes in order.`,
            },
          ],
        },
      ],
    });

    const textBlock = response.content.find((b) => b.type === "text");
    if (!textBlock || textBlock.type !== "text") {
      return base64Images.map(() => fallback("No text response from Claude"));
    }

    const parsed = JSON.parse(extractJson(textBlock.text));
    if (!Array.isArray(parsed)) {
      return base64Images.map(() => fallback("Batch response was not an array"));
    }

    // Pad / truncate to match input length so callers can index safely.
    return base64Images.map((_, i) => {
      const item = parsed[i];
      if (!item) return fallback("Missing classification for this image");
      return {
        status: item.status ?? "ambiguous",
        confidence: typeof item.confidence === "number" ? item.confidence : 0,
        reason: item.reason ?? "No reason provided",
      };
    });
  } catch (error) {
    console.error("Claude batch classification error:", error);
    return base64Images.map(() => fallback("Batch processing failed"));
  }
}
