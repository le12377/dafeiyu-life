@echo off
cd /d "<BREEZE_ROOT>\bin"
"<BREEZE_ROOT>\bin\breeze-server.exe" "<BREEZE_ROOT>\models\breeze-tts-2-q8_0.gguf" --host 127.0.0.1 --port 8137 --voices-dir "<BREEZE_ROOT>\voices" --ws-port -1 --webui
pause
