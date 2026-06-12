#!/usr/bin/env bash
set -euo pipefail

ROOT="${HOME}/mozilla-hackathon"
ENCODER_REPO="${ROOT}/encoderfile"
VENV="${ROOT}/venv"
MODEL_DIR="${ROOT}/models/sentiment-model"
BUILD_DIR="${ENCODER_REPO}/build"
CONFIG="${ENCODER_REPO}/configs/sentiment-config.yml"
BINARY="${BUILD_DIR}/sentiment-analyzer.encoderfile"
CLI_DIR="${ROOT}/bin"
CLI="${CLI_DIR}/encoderfile"
PORT="${ENCODERFILE_PORT:-8081}"
HF_MODEL="optimum/distilbert-base-uncased-finetuned-sst-2-english"

log() { printf '==> %s\n' "$1"; }
warn() { printf 'WARNING: %s\n' "$1"; }

mkdir -p "${ROOT}" "${CLI_DIR}" "${MODEL_DIR}" "${BUILD_DIR}"

if [[ ! -d "${VENV}" ]]; then
  log "Creating shared Python venv"
  python3 -m venv "${VENV}"
fi

# shellcheck disable=SC1091
source "${VENV}/bin/activate"
python -m pip install -U pip
python -m pip install huggingface_hub encoderfile pyyaml

if [[ -d "${ENCODER_REPO}" && ! -d "${ENCODER_REPO}/.git" ]]; then
  log "Removing incomplete encoderfile directory"
  rm -rf "${ENCODER_REPO}"
fi

if [[ ! -d "${ENCODER_REPO}/.git" ]]; then
  log "Cloning encoderfile repo (docs/config reference)"
  git clone --depth 1 https://github.com/mozilla-ai/encoderfile.git "${ENCODER_REPO}"
else
  log "encoderfile repo already present"
fi

mkdir -p "${ENCODER_REPO}/configs"

if [[ ! -x "${CLI}" ]]; then
  log "Downloading encoderfile CLI binary"
  tmp="$(mktemp -d)"
  curl -fsSL \
    "https://github.com/mozilla-ai/encoderfile/releases/download/v0.6.2/encoderfile-x86_64-unknown-linux-gnu.tar.gz" \
    -o "${tmp}/encoderfile.tgz"
  tar -xzf "${tmp}/encoderfile.tgz" -C "${tmp}"
  install -m 755 "${tmp}/encoderfile" "${CLI}"
  rm -rf "${tmp}"
fi

if [[ ! -f "${MODEL_DIR}/model.onnx" ]]; then
  log "Downloading pre-exported ONNX model (no torch required)"
  MODEL_DIR="${MODEL_DIR}" HF_MODEL="${HF_MODEL}" python <<'PY'
from huggingface_hub import snapshot_download
import os

model_dir = os.environ["MODEL_DIR"]
repo = os.environ["HF_MODEL"]
snapshot_download(
    repo_id=repo,
    local_dir=model_dir,
    allow_patterns=[
        "model.onnx",
        "config.json",
        "tokenizer.json",
        "tokenizer_config.json",
        "vocab.txt",
        "special_tokens_map.json",
    ],
)
print("Downloaded ONNX model to", model_dir)
PY
else
  log "ONNX model already downloaded"
fi

log "Patching model config for encoderfile"
MODEL_DIR="${MODEL_DIR}" python <<'PY'
import json
import os
from pathlib import Path

config_path = Path(os.environ["MODEL_DIR"]) / "config.json"
config = json.loads(config_path.read_text(encoding="utf-8"))
config.setdefault("model_type", "distilbert")
if "num_labels" not in config and config.get("id2label"):
    config["num_labels"] = len(config["id2label"])
config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
print("Patched", config_path)
PY

cat > "${CONFIG}" <<EOF
encoderfile:
  name: sentiment-analyzer
  path: ${MODEL_DIR}
  model_type: sequence_classification
  output_path: ${BINARY}
EOF

if [[ ! -x "${BINARY}" ]]; then
  log "Building encoderfile binary"
  "${CLI}" build -f "${CONFIG}"
fi

chmod +x "${BINARY}"

log "Setup complete"
log "Binary: ${BINARY}"
log "Start with: ${BINARY} serve --http-port ${PORT} --disable-grpc"
