""" transcriber """

import os
import asyncio

import torch
import numpy as np

import whisper
from whisper import Whisper


models = {}

_WHISPER_MODEL_NAMES = {
    "tiny", "tiny.en", "base", "base.en",
    "small", "small.en", "medium", "medium.en",
    "large", "large-v2", "large-v3", "turbo",
}

def _device():
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def get_model(file_name="tiny.en.pt") -> Whisper:
    """load model by name (downloads to ~/.cache/whisper) or from local models/ dir"""
    if file_name not in models:
        name = file_name.removesuffix(".pt")
        if name in _WHISPER_MODEL_NAMES:
            models[file_name] = whisper.load_model(name).to(_device())
        else:
            path = os.path.join(os.path.dirname(__file__), f"./models/{file_name}")
            models[file_name] = whisper.load_model(path).to(_device())
    return models[file_name]


def transcribe_pcm_chunks(
    model: Whisper, chunks: list, lang="en", temperature=0.1, log_prob=-0.5
) -> dict:
    """transcribes pcm chunks list"""
    arr = (
        np.frombuffer(b"".join(chunks), np.int16).flatten().astype(np.float32) / 32768.0
    )
    use_fp16 = torch.backends.mps.is_available() or torch.cuda.is_available()
    return model.transcribe(
        arr,
        fp16=use_fp16,
        language=lang,
        logprob_threshold=log_prob,
        temperature=temperature,
    )


async def transcribe_pcm_chunks_async(
    model: Whisper, chunks: list, lang="en", temperature=0.1, log_prob=-0.5
) -> dict:
    """transcribes pcm chunks async"""
    return await asyncio.get_running_loop().run_in_executor(
        None, transcribe_pcm_chunks, model, chunks, lang, temperature, log_prob
    )
