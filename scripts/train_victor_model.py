"""
VICTOR Custom Wake-Word Generator & Trainer
Synthesizes positive & negative acoustic training samples, extracts 16x96 embeddings
via OpenWakeWord's embedding ONNX model, trains an MLP classifier, and exports
data/models/victor.onnx ready for OpenWakeWord inference.
"""

import math
import os
import shutil
import tempfile
import time
import wave
from pathlib import Path
import numpy as np
import onnx
from onnx import helper, TensorProto
import onnxruntime as ort
from sklearn.neural_network import MLPClassifier
from scipy import signal

ROOT_DIR = Path(__file__).resolve().parents[1]
MODELS_DIR = ROOT_DIR / "data" / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)
VICTOR_MODEL_PATH = MODELS_DIR / "victor.onnx"

OWW_DIR = ROOT_DIR / ".venv" / "Lib" / "site-packages" / "openwakeword" / "resources" / "models"
MEL_PATH = OWW_DIR / "melspectrogram.onnx"
EMB_PATH = OWW_DIR / "embedding_model.onnx"


def generate_speech_wav(text: str, voice_id: str, rate: int, output_wav: Path):
    """Use pyttsx3 to generate WAV file on disk."""
    import pyttsx3
    engine = pyttsx3.init()
    engine.setProperty("voice", voice_id)
    engine.setProperty("rate", rate)
    engine.save_to_file(text, str(output_wav))
    engine.runAndWait()
    engine.stop()


def load_wav_16k(wav_path: Path) -> np.ndarray:
    """Load WAV file and resample/convert to 16kHz float32 mono."""
    with wave.open(str(wav_path), "rb") as wf:
        sr = wf.getframerate()
        n_ch = wf.getnchannels()
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)

    # 16-bit PCM
    audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    if n_ch > 1:
        audio = audio.reshape(-1, n_ch).mean(axis=1)

    if sr != 16000:
        num_target = int(len(audio) * 16000 / sr)
        audio = signal.resample(audio, num_target)

    return audio.astype(np.float32)


def get_audio_embeddings(audio: np.ndarray, oww_model) -> list:
    """
    Extract openwakeword 16x96 embeddings.
    Audio is fed in 1280-sample chunks (80ms).
    """
    audio_int16 = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
    
    embeddings = []
    step = 1280
    for i in range(0, len(audio_int16) - step, step):
        chunk = audio_int16[i:i + step]
        oww_model.predict(chunk)
        if hasattr(oww_model, "preprocessor") and hasattr(oww_model.preprocessor, "feature_buffer"):
            fb = oww_model.preprocessor.feature_buffer
            if len(fb) >= 16:
                emb = fb[-16:, :][None, :, :].copy().astype(np.float32)
                embeddings.append(emb)
    return embeddings


def export_mlp_to_onnx(weights_1, bias_1, weights_2, bias_2, output_path: Path):
    """
    Construct and save an ONNX model matching openWakeWord requirements:
    Input: 'x.1' [1, 16, 96]
    Output: '53' [1, 1]
    """
    # Create initializers (weights and biases)
    # W1: [1536, H], B1: [H]
    # W2: [H, 1], B2: [1]
    w1_init = helper.make_tensor("W1", TensorProto.FLOAT, weights_1.shape, weights_1.flatten().tolist())
    b1_init = helper.make_tensor("B1", TensorProto.FLOAT, bias_1.shape, bias_1.flatten().tolist())
    w2_init = helper.make_tensor("W2", TensorProto.FLOAT, weights_2.shape, weights_2.flatten().tolist())
    b2_init = helper.make_tensor("B2", TensorProto.FLOAT, bias_2.shape, bias_2.flatten().tolist())

    # Graph nodes:
    # 1. Flatten x.1 from [1, 16, 96] to [1, 1536]
    flat_node = helper.make_node("Flatten", ["x.1"], ["flat"], axis=1)
    # 2. Gemm: flat * W1 + B1
    gemm1_node = helper.make_node("Gemm", ["flat", "W1", "B1"], ["h1"], alpha=1.0, beta=1.0, transA=0, transB=0)
    # 3. Relu
    relu_node = helper.make_node("Relu", ["h1"], ["a1"])
    # 4. Gemm: a1 * W2 + B2
    gemm2_node = helper.make_node("Gemm", ["a1", "W2", "B2"], ["h2"], alpha=1.0, beta=1.0, transA=0, transB=0)
    # 5. Sigmoid
    sig_node = helper.make_node("Sigmoid", ["h2"], ["53"])

    input_tensor = helper.make_tensor_value_info("x.1", TensorProto.FLOAT, [1, 16, 96])
    output_tensor = helper.make_tensor_value_info("53", TensorProto.FLOAT, [1, 1])

    graph = helper.make_graph(
        [flat_node, gemm1_node, relu_node, gemm2_node, sig_node],
        "VictorWakeWordClassifier",
        [input_tensor],
        [output_tensor],
        [w1_init, b1_init, w2_init, b2_init]
    )

    model = helper.make_model(
        graph,
        producer_name="victor_ai",
        ir_version=7,
        opset_imports=[helper.make_opsetid("", 13)]
    )
    onnx.checker.check_model(model)
    onnx.save(model, str(output_path))
    print(f"[+] Exported custom Victor ONNX model to: {output_path}")


def train_victor_model():
    print("=" * 60, flush=True)
    print("   [+] VICTOR Custom Wake-Word Generator & Trainer", flush=True)
    print("=" * 60, flush=True)

    import pyttsx3
    engine = pyttsx3.init()
    voices = [v.id for v in engine.getProperty("voices")]

    print(f"[*] Available system voices: {len(voices)}", flush=True)

    temp_dir = Path(tempfile.mkdtemp(prefix="victor_train_"))
    try:
        positive_phrases = [
            "Victor",
            "Hey Victor",
            "Victor please",
            "Okay Victor",
            "Victor",
            "Hey Victor"
        ]

        negative_phrases = [
            "Jarvis",
            "Hey Jarvis",
            "Alexa",
            "Computer",
            "Hello",
            "Vishnu",
            "Testing",
            "Diagnostics"
        ]

        rates = [140, 175, 205]

        print("[*] Synthesizing audio files via SAPI5...", flush=True)
        tasks = []
        count = 0
        for phrase in positive_phrases:
            for v_id in voices:
                for r in rates:
                    wav_file = temp_dir / f"pos_{count}.wav"
                    engine.setProperty("voice", v_id)
                    engine.setProperty("rate", r)
                    engine.save_to_file(phrase, str(wav_file))
                    tasks.append((True, wav_file))
                    count += 1

        count = 0
        for phrase in negative_phrases:
            for v_id in voices:
                for r in rates:
                    wav_file = temp_dir / f"neg_{count}.wav"
                    engine.setProperty("voice", v_id)
                    engine.setProperty("rate", r)
                    engine.save_to_file(phrase, str(wav_file))
                    tasks.append((False, wav_file))
                    count += 1

        engine.runAndWait()
        engine.stop()
        print(f"[+] Synthesized {len(tasks)} audio files successfully.", flush=True)

        print("[*] Extracting openWakeWord 16x96 embeddings...", flush=True)
        from openwakeword.model import Model
        oww_model = Model(wakeword_models=["hey_jarvis"], inference_framework="onnx")

        X_pos = []
        X_neg = []

        for is_pos, wav_file in tasks:
            if not wav_file.exists():
                continue
            audio = load_wav_16k(wav_file)
            embs = get_audio_embeddings(audio, oww_model)
            if is_pos:
                X_pos.extend(embs)
                # Augment with slight noise
                noisy = audio + np.random.normal(0, 0.005, size=len(audio)).astype(np.float32)
                embs_noise = get_audio_embeddings(noisy, oww_model)
                X_pos.extend(embs_noise)
            else:
                X_neg.extend(embs)

        # Add background silence and ambient noise negatives
        for _ in range(15):
            noise_audio = np.random.normal(0, 0.01, size=24000).astype(np.float32)
            embs_noise = get_audio_embeddings(noise_audio, oww_model)
            X_neg.extend(embs_noise)

        print(f"[+] Total positive frames: {len(X_pos)}, negative frames: {len(X_neg)}", flush=True)

        # Prepare dataset for Scikit-Learn
        X = []
        y = []

        for e in X_pos:
            X.append(e.reshape(-1))
            y.append(1)

        for e in X_neg:
            X.append(e.reshape(-1))
            y.append(0)

        X = np.array(X, dtype=np.float32)
        y = np.array(y, dtype=np.int32)

        print(f"[*] Training MLP classifier (X={X.shape}, y={y.shape})...", flush=True)
        clf = MLPClassifier(
            hidden_layer_sizes=(64,),
            activation="relu",
            max_iter=300,
            random_state=42,
            learning_rate_init=0.003
        )
        clf.fit(X, y)
        train_acc = clf.score(X, y)
        print(f"[+] Model training complete. Accuracy: {train_acc * 100:.2f}%", flush=True)

        # Extract weights
        W1 = clf.coefs_[0].astype(np.float32)      # [1536, 64]
        B1 = clf.intercepts_[0].astype(np.float32)  # [64]
        W2 = clf.coefs_[1].astype(np.float32)      # [64, 1]
        B2 = clf.intercepts_[1].astype(np.float32)  # [1]

        # Export ONNX
        export_mlp_to_onnx(W1, B1, W2, B2, VICTOR_MODEL_PATH)

        # Verification with OpenWakeWord
        print("[*] Verifying custom model loading with openWakeWord...", flush=True)
        test_model = Model(wakeword_models=[str(VICTOR_MODEL_PATH)], inference_framework="onnx")
        print(f"[+] Model loaded successfully: {list(test_model.models.keys())}", flush=True)

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    train_victor_model()
