#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${BREV_LLM_API_KEY:-}" && -f "$HOME/.brev_llm_key" ]]; then
  BREV_LLM_API_KEY="$(<"$HOME/.brev_llm_key")"
fi
: "${BREV_LLM_API_KEY:?Set BREV_LLM_API_KEY on the Brev instance before starting vLLM}"

model="${BREV_MODEL_ID:-nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-FP8}"
served_name="${BREV_LLM_MODEL:-nemotron-3-nano}"
max_len="${BREV_MAX_MODEL_LEN:-16384}"

docker run -d --name challenge-hub-nemotron --gpus all --ipc=host \
  -p 127.0.0.1:8000:8000 \
  -v "$HOME/.cache/huggingface:/root/.cache/huggingface" \
  vllm/vllm-openai:latest \
  --model "$model" \
  --served-model-name "$served_name" \
  --max-model-len "$max_len" \
  --max-num-seqs 2 \
  --trust-remote-code \
  --api-key "$BREV_LLM_API_KEY"
