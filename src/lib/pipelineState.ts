import type { PipelineResponse } from "@/services/pipelineApi";

const PIPELINE_KEY = "pipeline_result_v1";

export function savePipelineResult(result: PipelineResponse): void {
  sessionStorage.setItem(PIPELINE_KEY, JSON.stringify(result));
}

export function loadPipelineResult(): PipelineResponse | null {
  const raw = sessionStorage.getItem(PIPELINE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as PipelineResponse;
  } catch {
    return null;
  }
}
