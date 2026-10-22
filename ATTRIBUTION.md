# Audio/model attribution notes

- The background music is generated procedurally by `app/make_audio.py`; no third-party song is included.
- The workflow downloads the `en_US-lessac-medium` Piper voice model from the `rhasspy/piper-voices` Hugging Face repository at run time. Verify the voice model's current licence and preserve its attribution requirements before commercial use. Model/voice terms can differ from the Python package's licence.
- The Blender visuals are generated procedurally by this project; no reference-video assets are included.

- Story generation uses `Qwen2.5-1.5B-Instruct` in GGUF Q4_K_M quantization from `bartowski/Qwen2.5-1.5B-Instruct-GGUF` on Hugging Face (Apache-2.0 model card at time of packaging). The workflow downloads it to the temporary runner; model weights are not committed into this repository.
